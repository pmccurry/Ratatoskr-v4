"""Trade reconciliation — compare internal state against broker state."""

import logging
from datetime import datetime, timezone
from decimal import Decimal

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.config import get_settings
from app.portfolio.models import Position

logger = logging.getLogger(__name__)


async def reconcile(db: AsyncSession) -> dict:
    """Compare internal positions against broker state.

    Returns a reconciliation report for each broker.
    """
    now = datetime.now(timezone.utc)
    result = {
        "timestamp": now.isoformat(),
        "alpaca": await _reconcile_alpaca(db),
        "oanda": await _reconcile_oanda(db),
    }
    return result


async def _reconcile_alpaca(db: AsyncSession) -> dict:
    """Reconcile internal equity positions against Alpaca API."""
    settings = get_settings()

    if not settings.alpaca_api_key or not settings.alpaca_api_secret:
        return {"status": "unconfigured"}

    # Get internal open equity positions
    internal_result = await db.execute(
        select(Position).where(
            Position.market == "equities",
            Position.status == "open",
        )
    )
    internal_positions = list(internal_result.scalars().all())

    # Fetch Alpaca positions
    try:
        async with httpx.AsyncClient(
            base_url=settings.alpaca_base_url,
            headers={
                "APCA-API-KEY-ID": settings.alpaca_api_key,
                "APCA-API-SECRET-KEY": settings.alpaca_api_secret,
            },
            timeout=15.0,
        ) as client:
            resp = await client.get("/v2/positions")
            if resp.status_code != 200:
                return {
                    "status": "error",
                    "error": f"Alpaca API returned {resp.status_code}",
                }
            broker_positions = resp.json()
    except Exception as e:
        return {"status": "error", "error": str(e)}

    # Build lookup maps (all qtys as Decimal)
    internal_map = {}
    for p in internal_positions:
        internal_map[p.symbol] = {
            "qty": str(p.qty),
            "side": p.side,
        }

    broker_map = {}
    for bp in broker_positions:
        qty = Decimal(str(bp.get("qty", "0")))
        side = "long" if qty > 0 else "short"
        broker_map[bp["symbol"]] = {
            "qty": str(abs(qty)),
            "side": side,
        }

    # Compare
    mismatches = []
    all_symbols = set(internal_map.keys()) | set(broker_map.keys())
    for symbol in sorted(all_symbols):
        internal = internal_map.get(symbol)
        broker = broker_map.get(symbol)

        if internal and not broker:
            mismatches.append({
                "symbol": symbol,
                "internal": internal,
                "broker": None,
                "issue": "Position exists internally but not at broker",
            })
        elif broker and not internal:
            mismatches.append({
                "symbol": symbol,
                "internal": None,
                "broker": broker,
                "issue": "Position exists at broker but not internally",
            })
        elif internal and broker:
            if abs(Decimal(internal["qty"]) - Decimal(broker["qty"])) > Decimal("0.001") or internal["side"] != broker["side"]:
                mismatches.append({
                    "symbol": symbol,
                    "internal": internal,
                    "broker": broker,
                    "issue": "Quantity or side mismatch",
                })

    status = "matched" if not mismatches else "mismatch"
    return {
        "status": status,
        "internalPositions": len(internal_positions),
        "brokerPositions": len(broker_positions),
        "mismatches": mismatches,
    }


async def _reconcile_oanda(db: AsyncSession) -> dict:
    """Reconcile internal forex positions against OANDA API."""
    settings = get_settings()

    if not settings.oanda_access_token or not settings.oanda_account_id:
        return {"status": "unconfigured"}

    # Get internal open forex positions
    internal_result = await db.execute(
        select(Position).where(
            Position.market == "forex",
            Position.status == "open",
        )
    )
    internal_positions = list(internal_result.scalars().all())

    # For each pool account that has a real OANDA mapping, fetch positions
    from app.paper_trading.models import BrokerAccount

    accounts_result = await db.execute(
        select(BrokerAccount).where(
            BrokerAccount.broker == "oanda",
            BrokerAccount.is_active == True,
            BrokerAccount.account_type == "paper_live",
        )
    )
    real_accounts = list(accounts_result.scalars().all())

    if not real_accounts:
        # No real OANDA accounts mapped — skip broker comparison
        return {
            "status": "virtual_only",
            "internalPositions": len(internal_positions),
            "brokerPositions": 0,
            "mismatches": [],
            "note": "All forex pool accounts are virtual (no OANDA mapping)",
        }

    broker_positions = []
    try:
        async with httpx.AsyncClient(
            base_url=settings.oanda_base_url,
            headers={
                "Authorization": f"Bearer {settings.oanda_access_token}",
                "Content-Type": "application/json",
            },
            timeout=15.0,
        ) as client:
            for acct in real_accounts:
                resp = await client.get(
                    f"/v3/accounts/{acct.account_id}/openPositions"
                )
                if resp.status_code == 200:
                    data = resp.json()
                    for pos in data.get("positions", []):
                        long_units = int(pos.get("long", {}).get("units", "0"))
                        short_units = int(pos.get("short", {}).get("units", "0"))
                        if long_units != 0:
                            broker_positions.append({
                                "symbol": pos["instrument"],
                                "qty": abs(long_units),
                                "side": "long",
                                "poolAccount": acct.account_id,
                            })
                        if short_units != 0:
                            broker_positions.append({
                                "symbol": pos["instrument"],
                                "qty": abs(short_units),
                                "side": "short",
                                "poolAccount": acct.account_id,
                            })
    except Exception as e:
        return {"status": "error", "error": str(e)}

    # Build internal map (Decimal quantities)
    internal_map = {}
    for p in internal_positions:
        key = f"{p.symbol}:{p.broker_account_id or 'virtual'}"
        internal_map[key] = {
            "symbol": p.symbol,
            "qty": str(p.qty),
            "side": p.side,
            "poolAccount": p.broker_account_id,
        }

    broker_map = {}
    for bp in broker_positions:
        key = f"{bp['symbol']}:{bp['poolAccount']}"
        broker_map[key] = {
            "symbol": bp["symbol"],
            "qty": str(bp["qty"]),
            "side": bp["side"],
            "poolAccount": bp["poolAccount"],
        }

    mismatches = []
    all_keys = set(internal_map.keys()) | set(broker_map.keys())
    for key in sorted(all_keys):
        internal = internal_map.get(key)
        broker = broker_map.get(key)

        if internal and not broker:
            mismatches.append({
                "symbol": internal["symbol"],
                "poolAccount": internal["poolAccount"],
                "internal": {"qty": internal["qty"], "side": internal["side"]},
                "broker": None,
                "issue": "Position exists internally but not at broker",
            })
        elif broker and not internal:
            mismatches.append({
                "symbol": broker["symbol"],
                "poolAccount": broker["poolAccount"],
                "internal": None,
                "broker": {"qty": broker["qty"], "side": broker["side"]},
                "issue": "Position exists at broker but not internally",
            })
        elif internal and broker:
            if abs(Decimal(internal["qty"]) - Decimal(broker["qty"])) > Decimal("0.001") or internal["side"] != broker["side"]:
                mismatches.append({
                    "symbol": internal["symbol"],
                    "poolAccount": internal["poolAccount"],
                    "internal": {"qty": internal["qty"], "side": internal["side"]},
                    "broker": {"qty": broker["qty"], "side": broker["side"]},
                    "issue": "Quantity or side mismatch",
                })

    status = "matched" if not mismatches else "mismatch"
    return {
        "status": status,
        "internalPositions": len(internal_positions),
        "brokerPositions": len(broker_positions),
        "mismatches": mismatches,
    }
