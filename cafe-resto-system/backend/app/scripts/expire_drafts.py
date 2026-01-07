"""
Background job to expire stale drafts

This script should be run periodically (e.g., via cron or Celery beat)
to expire drafts that have exceeded their TTL.
"""

import asyncio
import sys
import os
from datetime import datetime

# Add backend to path
backend_path = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, backend_path)

from sqlmodel import Session, select
from app.core.database import engine
from app.models.draft_order import DraftOrder, DraftStatus
import structlog

logger = structlog.get_logger(__name__)


def expire_stale_drafts(session: Session) -> dict:
    """Find and expire all stale drafts"""
    try:
        # Find pending drafts that have expired
        expired_drafts = session.exec(
            select(DraftOrder).where(
                DraftOrder.status == DraftStatus.PENDING,
                DraftOrder.expires_at < datetime.utcnow()
            )
        ).all()

        if not expired_drafts:
            logger.info("No stale drafts found")
            return {"processed": 0, "expired": 0}

        # Expire each draft
        for draft in expired_drafts:
            try:
                draft.transition_to_expired()
                logger.info(f"Expired draft {draft.id} (session: {draft.table_session_id})")
            except Exception as e:
                logger.error(f"Failed to expire draft {draft.id}: {e}")
                continue

        session.commit()

        # Also release locks on expired drafts (should already be done by transition)
        # But double-check for drafts locked > 30 minutes
        from datetime import timedelta
        stale_locked_drafts = session.exec(
            select(DraftOrder).where(
                DraftOrder.status == DraftStatus.PENDING,
                DraftOrder.locked_by != None,
                DraftOrder.locked_at < datetime.utcnow() - timedelta(minutes=30)
            )
        ).all()

        for draft in stale_locked_drafts:
            draft.locked_by = None
            draft.locked_at = None
            draft.version += 1
            logger.info(f"Released stale lock on draft {draft.id}")

        session.commit()

        return {
            "processed": len(expired_drafts) + len(stale_locked_drafts),
            "expired": len(expired_drafts),
            "locks_released": len(stale_locked_drafts)
        }

    except Exception as e:
        session.rollback()
        logger.error(f"Error expiring stale drafts: {e}")
        raise


def main():
    """Main entry point for cleanup job"""
    logger.info("="*80)
    logger.info("Starting Draft TTL Cleanup Job")
    logger.info("="*80)

    try:
        with Session(engine) as session:
            results = expire_stale_drafts(session)

            logger.info("="*80)
            logger.info("Draft TTL Cleanup Complete")
            logger.info(f"Results: {results}")
            logger.info("="*80)

    except Exception as e:
        logger.error(f"Fatal error in cleanup job: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
