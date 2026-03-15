"""Daily portfolio maintenance jobs."""

import logging
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.portfolio.dividends import DividendProcessor
from app.portfolio.options_lifecycle import OptionsLifecycle
from app.portfolio.splits import SplitProcessor

logger = logging.getLogger(__name__)


class DailyPortfolioJobs:
    """Runs daily portfolio maintenance tasks.

    Should be triggered once per day (at market close or via schedule).
    """

    def __init__(self):
        self._dividend_processor = DividendProcessor()
        self._split_processor = SplitProcessor()
        self._options_lifecycle = OptionsLifecycle()

    async def run_daily(self, db: AsyncSession, user_id: UUID) -> dict:
        """Run all daily jobs."""
        summary = {
            "dividends_pending": 0,
            "dividends_paid": 0,
            "splits_processed": 0,
            "options_expired": 0,
            "snapshot_taken": False,
        }

        # 1. Process ex-date dividends
        try:
            pending = await self._dividend_processor.process_ex_date(db, user_id)
            summary["dividends_pending"] = len(pending)
        except Exception as e:
            logger.error("Ex-date dividend processing error: %s", e)

        # 2. Process payable-date dividends
        try:
            paid = await self._dividend_processor.process_payable_date(db, user_id)
            summary["dividends_paid"] = len(paid)
        except Exception as e:
            logger.error("Payable-date dividend processing error: %s", e)

        # 3. Process stock splits
        try:
            splits = await self._split_processor.process_splits(db, user_id)
            summary["splits_processed"] = len(splits)
        except Exception as e:
            logger.error("Split processing error: %s", e)

        # 4. Check options expirations
        try:
            expired = await self._options_lifecycle.check_expirations(db, user_id)
            summary["options_expired"] = len(expired)
        except Exception as e:
            logger.error("Options expiration error: %s", e)

        # 5. Take daily close snapshot
        try:
            from app.portfolio.startup import get_snapshot_manager
            snapshot_mgr = get_snapshot_manager()
            if snapshot_mgr:
                await snapshot_mgr.take_daily_close_snapshot(db, user_id)
                summary["snapshot_taken"] = True
        except Exception as e:
            logger.error("Daily close snapshot error: %s", e)

        logger.info("Daily portfolio jobs completed: %s", summary)
        return summary
