"""Optional DB-backed lock helpers for scheduled jobs.

Starter template keeps these stubs so you can wire cron jobs later without Redis.
"""

from sqlalchemy.ext.asyncio import AsyncSession

from app.utils.logger.log import logs


async def try_acquire_db_cron_lock(db: AsyncSession, job_name: str) -> bool:
    """Stub: always acquire. Replace with a real lock table when you add cron jobs."""
    logs.debug(f"Cron lock acquire stub for '{job_name}'")
    return True


async def release_db_cron_lock(db: AsyncSession, job_name: str) -> None:
    logs.debug(f"Cron lock release stub for '{job_name}'")


async def already_sent_digest_today(db: AsyncSession, digest_key: str) -> bool:
    return False


async def mark_digest_sent_today(db: AsyncSession, digest_key: str) -> None:
    logs.debug(f"Digest mark stub for '{digest_key}'")
