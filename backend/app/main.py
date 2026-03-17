"""Ratatoskr Trading Platform — API Entrypoint"""

import logging
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.router import router as auth_router, users_router
from app.common.config import get_settings
from app.common.database import get_db, get_engine
from app.common.errors import DomainError, domain_error_handler, unhandled_error_handler
from app.market_data.router import router as market_data_router
from app.observability.router import router as observability_router
from app.paper_trading.router import router as paper_trading_router
from app.portfolio.router import router as portfolio_router
from app.risk.router import router as risk_router
from app.signals.router import router as signals_router
from app.strategies.router import router as strategies_router
from app.backtesting.router import router as backtesting_router, strategy_backtest_router
from app.strategy_sdk.router import router as python_strategy_router

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: validate settings load successfully (fail fast)
    settings = get_settings()
    logger.info("Settings loaded successfully (log_level=%s)", settings.log_level)

    # JWT secret production guard
    if settings.auth_jwt_secret_key == "dev-only-change-me-in-production-abc123":
        if settings.environment == "production":
            raise RuntimeError("AUTH_JWT_SECRET_KEY must be changed from default in production")
        else:
            logger.warning("Using default JWT secret — change this before production use")

    # Start observability FIRST — other modules need the event emitter
    try:
        from app.observability.startup import start_observability
        await start_observability()
    except Exception as e:
        logger.error("Observability startup failed (non-fatal): %s", e)

    # Start market data module (non-fatal — other modules still work if this fails)
    try:
        from app.common.database import get_session_factory
        from app.market_data.startup import start_market_data

        factory = get_session_factory()
        async with factory() as db:
            await start_market_data(db)
            await db.commit()
    except Exception as e:
        logger.error("Market data startup failed (non-fatal): %s", e)

    # Start strategy module (non-fatal)
    try:
        from app.strategies.startup import start_strategies
        await start_strategies()
    except Exception as e:
        logger.error("Strategy module startup failed (non-fatal): %s", e)

    # Start signal module (non-fatal — must start after strategies)
    try:
        from app.signals.startup import start_signals
        await start_signals()
    except Exception as e:
        logger.error("Signal module startup failed (non-fatal): %s", e)

    # Start risk module (non-fatal — must start after signals)
    try:
        from app.risk.startup import start_risk
        await start_risk()
    except Exception as e:
        logger.error("Risk module startup failed (non-fatal): %s", e)

    # Start paper trading module (non-fatal — must start after risk)
    try:
        from app.paper_trading.startup import start_paper_trading
        await start_paper_trading()
    except Exception as e:
        logger.error("Paper trading module startup failed (non-fatal): %s", e)

    # Discover Python strategies (non-fatal)
    try:
        from app.strategy_sdk.registry import discover_strategies
        strategies_found = discover_strategies()
        logger.info("Found %d Python strategies", len(strategies_found))
    except Exception as e:
        logger.error("Python strategy discovery failed (non-fatal): %s", e)

    # Start portfolio module (non-fatal — must start after paper trading)
    try:
        from app.portfolio.startup import start_portfolio
        from app.auth.models import User as AuthUser
        from sqlalchemy import select as sa_select

        async with factory() as portfolio_db:
            result = await portfolio_db.execute(
                sa_select(AuthUser).where(AuthUser.role == "admin").limit(1)
            )
            admin_user = result.scalar_one_or_none()
            if admin_user:
                await start_portfolio(portfolio_db, admin_user.id)
                await portfolio_db.commit()
            else:
                logger.warning("Portfolio startup skipped: no admin user found")
    except Exception as e:
        logger.error("Portfolio module startup failed (non-fatal): %s", e)

    yield

    # Shutdown: stop portfolio module (before paper trading)
    try:
        from app.portfolio.startup import stop_portfolio
        await stop_portfolio()
    except Exception as e:
        logger.error("Portfolio module shutdown error: %s", e)

    # Shutdown: stop paper trading module (before risk)
    try:
        from app.paper_trading.startup import stop_paper_trading
        await stop_paper_trading()
    except Exception as e:
        logger.error("Paper trading module shutdown error: %s", e)

    # Shutdown: stop risk module (before signals)
    try:
        from app.risk.startup import stop_risk
        await stop_risk()
    except Exception as e:
        logger.error("Risk module shutdown error: %s", e)

    # Shutdown: stop signal module (before strategies)
    try:
        from app.signals.startup import stop_signals
        await stop_signals()
    except Exception as e:
        logger.error("Signal module shutdown error: %s", e)

    # Shutdown: stop strategy module
    try:
        from app.strategies.startup import stop_strategies
        await stop_strategies()
    except Exception as e:
        logger.error("Strategy module shutdown error: %s", e)

    # Shutdown: stop market data module
    try:
        from app.market_data.startup import stop_market_data
        await stop_market_data()
    except Exception as e:
        logger.error("Market data shutdown error: %s", e)

    # Shutdown: stop observability LAST — capture shutdown events
    try:
        from app.observability.startup import stop_observability
        await stop_observability()
    except Exception as e:
        logger.error("Observability module shutdown error: %s", e)

    # Dispose database engine
    await get_engine().dispose()
    logger.info("Database engine disposed")


app = FastAPI(
    title="Ratatoskr Trading Platform",
    description="Professional quant/algo trading platform",
    version="0.1.0",
    lifespan=lifespan,
)

# Configure logging based on environment
_boot_settings = get_settings()
if _boot_settings.log_format == "json":
    import json as _json

    class _JSONFormatter(logging.Formatter):
        def format(self, record):
            log_data = {
                "timestamp": self.formatTime(record),
                "level": record.levelname,
                "logger": record.name,
                "message": record.getMessage(),
            }
            if record.exc_info:
                log_data["exception"] = self.formatException(record.exc_info)
            return _json.dumps(log_data)

    _handler = logging.StreamHandler()
    _handler.setFormatter(_JSONFormatter())
    logging.root.handlers.clear()
    logging.root.addHandler(_handler)

logging.root.setLevel(getattr(logging, _boot_settings.log_level.upper(), logging.INFO))

# Request body size limit middleware
from app.common.middleware import RequestSizeLimitMiddleware

app.add_middleware(RequestSizeLimitMiddleware, max_body_size=_boot_settings.max_request_body_size)

# CORS middleware
_settings = get_settings()
_cors_origins = (
    _settings.cors_allowed_origins.split(",")
    if _settings.cors_allowed_origins
    else ["http://localhost:3000", "http://localhost:5173"]
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Exception handlers
app.add_exception_handler(DomainError, domain_error_handler)
app.add_exception_handler(Exception, unhandled_error_handler)

# Module routers
app.include_router(auth_router, prefix="/api/v1")
app.include_router(users_router, prefix="/api/v1")
app.include_router(market_data_router, prefix="/api/v1")
app.include_router(strategies_router, prefix="/api/v1")
app.include_router(signals_router, prefix="/api/v1")
app.include_router(risk_router, prefix="/api/v1")
app.include_router(paper_trading_router, prefix="/api/v1")
app.include_router(portfolio_router, prefix="/api/v1")
app.include_router(observability_router, prefix="/api/v1")
app.include_router(backtesting_router, prefix="/api/v1")
app.include_router(strategy_backtest_router, prefix="/api/v1")
app.include_router(python_strategy_router, prefix="/api/v1")


@app.get("/api/v1/health")
async def health_check(db: AsyncSession = Depends(get_db)):
    try:
        await db.execute(text("SELECT 1"))
        db_status = "connected"
    except Exception:
        db_status = "disconnected"

    # Broker status
    brokers = {}
    try:
        from app.market_data.startup import get_ws_manager
        ws_mgr = get_ws_manager()
        if ws_mgr:
            health = ws_mgr.get_health()
            for broker_key in ("alpaca", "oanda"):
                if broker_key in health:
                    h = health[broker_key]
                    brokers[broker_key] = {
                        "status": h.get("status", "unknown"),
                        "subscribedSymbols": h.get("subscribedSymbols", 0),
                    }
                else:
                    s = get_settings()
                    key = s.alpaca_api_key if broker_key == "alpaca" else s.oanda_access_token
                    brokers[broker_key] = {
                        "status": "unconfigured" if not key else "not_started"
                    }
        else:
            s = get_settings()
            brokers["alpaca"] = {
                "status": "unconfigured" if not s.alpaca_api_key else "disconnected"
            }
            brokers["oanda"] = {
                "status": "unconfigured" if not s.oanda_access_token else "disconnected"
            }
    except Exception:
        brokers["alpaca"] = {"status": "unknown"}
        brokers["oanda"] = {"status": "unknown"}

    return {
        "status": "healthy" if db_status == "connected" else "degraded",
        "version": "0.1.0",
        "database": db_status,
        "brokers": brokers,
    }
