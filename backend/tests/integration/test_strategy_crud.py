"""Integration tests for strategy CRUD and lifecycle."""

from uuid import uuid4

import pytest
import pytest_asyncio
from sqlalchemy import select

from app.strategies.models import Strategy, StrategyConfigVersion


class TestStrategyCreate:
    @pytest.mark.asyncio
    async def test_create_strategy_starts_as_draft(self, db, admin_user):
        strategy = Strategy(
            user_id=admin_user.id,
            key=f"test_create_{uuid4().hex[:8]}",
            name="New Strategy",
            market="equities",
        )
        db.add(strategy)
        await db.flush()
        assert strategy.status == "draft"
        assert strategy.id is not None

    @pytest.mark.asyncio
    async def test_create_strategy_with_config_version(self, db, admin_user):
        from tests.integration.conftest import _minimal_strategy_config

        strategy = Strategy(
            user_id=admin_user.id,
            key=f"test_ver_{uuid4().hex[:8]}",
            name="Versioned Strategy",
            market="equities",
        )
        db.add(strategy)
        await db.flush()

        config = StrategyConfigVersion(
            strategy_id=strategy.id,
            version="1.0.0",
            config_json=_minimal_strategy_config(),
            is_active=True,
        )
        db.add(config)
        await db.flush()

        result = await db.execute(
            select(StrategyConfigVersion).where(
                StrategyConfigVersion.strategy_id == strategy.id
            )
        )
        versions = result.scalars().all()
        assert len(versions) == 1
        assert versions[0].version == "1.0.0"

    @pytest.mark.asyncio
    async def test_duplicate_key_fails(self, db, admin_user):
        key = f"test_dup_{uuid4().hex[:8]}"
        s1 = Strategy(user_id=admin_user.id, key=key, name="First", market="equities")
        db.add(s1)
        await db.flush()

        s2 = Strategy(user_id=admin_user.id, key=key, name="Second", market="equities")
        db.add(s2)
        with pytest.raises(Exception):  # IntegrityError
            await db.flush()


class TestStrategyLifecycle:
    @pytest.mark.asyncio
    async def test_enable_draft(self, db, draft_strategy):
        draft_strategy.status = "enabled"
        await db.flush()
        assert draft_strategy.status == "enabled"

    @pytest.mark.asyncio
    async def test_pause_enabled(self, db, sample_strategy):
        sample_strategy.status = "paused"
        await db.flush()
        assert sample_strategy.status == "paused"

    @pytest.mark.asyncio
    async def test_resume_paused(self, db, sample_strategy):
        sample_strategy.status = "paused"
        await db.flush()
        sample_strategy.status = "enabled"
        await db.flush()
        assert sample_strategy.status == "enabled"

    @pytest.mark.asyncio
    async def test_disable_enabled(self, db, sample_strategy):
        sample_strategy.status = "disabled"
        await db.flush()
        assert sample_strategy.status == "disabled"


class TestStrategyUpdate:
    @pytest.mark.asyncio
    async def test_update_creates_new_config_version(self, db, sample_strategy):
        from tests.integration.conftest import _minimal_strategy_config

        new_config = _minimal_strategy_config()
        new_config["timeframe"] = "5m"

        # Deactivate old version
        result = await db.execute(
            select(StrategyConfigVersion).where(
                StrategyConfigVersion.strategy_id == sample_strategy.id,
                StrategyConfigVersion.is_active == True,
            )
        )
        old_version = result.scalar_one()
        old_version.is_active = False

        # Create new version
        new_ver = StrategyConfigVersion(
            strategy_id=sample_strategy.id,
            version="2.0.0",
            config_json=new_config,
            is_active=True,
        )
        db.add(new_ver)
        await db.flush()

        # Verify two versions exist, only new one active
        result = await db.execute(
            select(StrategyConfigVersion).where(
                StrategyConfigVersion.strategy_id == sample_strategy.id
            )
        )
        versions = result.scalars().all()
        assert len(versions) == 2
        active = [v for v in versions if v.is_active]
        assert len(active) == 1
        assert active[0].version == "2.0.0"


class TestStrategyQuery:
    @pytest.mark.asyncio
    async def test_query_by_user(self, db, admin_user, regular_user):
        s1 = Strategy(
            user_id=admin_user.id,
            key=f"admin_strat_{uuid4().hex[:8]}",
            name="Admin Strategy",
            market="equities",
        )
        s2 = Strategy(
            user_id=regular_user.id,
            key=f"user_strat_{uuid4().hex[:8]}",
            name="User Strategy",
            market="equities",
        )
        db.add_all([s1, s2])
        await db.flush()

        result = await db.execute(
            select(Strategy).where(Strategy.user_id == regular_user.id)
        )
        user_strategies = result.scalars().all()
        assert all(s.user_id == regular_user.id for s in user_strategies)

    @pytest.mark.asyncio
    async def test_query_by_key(self, db, sample_strategy):
        result = await db.execute(
            select(Strategy).where(Strategy.key == sample_strategy.key)
        )
        found = result.scalar_one()
        assert found.id == sample_strategy.id
