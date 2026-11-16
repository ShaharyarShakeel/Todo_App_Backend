from datetime import date, datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo


PAKISTAN_TIME = ZoneInfo("Asia/Karachi")
UTC = timezone.utc


def calculate_reminder_due_at(due_date: date, now: datetime | None = None) -> datetime:
    """Schedule for 9 AM Pakistan time the day before, or immediately if late."""
    current = now or datetime.now(UTC)
    if current.tzinfo is None:
        current = current.replace(tzinfo=UTC)
    current_utc = current.astimezone(UTC)

    scheduled_local = datetime.combine(
        due_date - timedelta(days=1), time(hour=9), tzinfo=PAKISTAN_TIME
    )
    scheduled_utc = scheduled_local.astimezone(UTC)
    return max(scheduled_utc, current_utc)
