import logging
from datetime import datetime, timedelta, timezone
from uuid import uuid4

from application.ports.email_sender import EmailSender
from application.ports.reminder_repository_provider import ReminderRepositoryProvider
from application.services.todo_reminder_scheduler import calculate_reminder_due_at

logger = logging.getLogger(__name__)


class SendTodoReminders:
    """Backfills and sends due Todo reminders across initialized providers."""

    SCHEDULE_BATCH_SIZE = 500
    CLAIM_BATCH_SIZE = 100
    CLAIM_LEASE = timedelta(minutes=30)

    def __init__(
        self,
        repository_provider: ReminderRepositoryProvider,
        email_sender: EmailSender,
    ):
        self.repository_provider = repository_provider
        self.email_sender = email_sender

    def execute(self, now: datetime | None = None) -> dict:
        current = now or datetime.now(timezone.utc)
        if current.tzinfo is None:
            current = current.replace(tzinfo=timezone.utc)
        current = current.astimezone(timezone.utc)
        lease_until = current + self.CLAIM_LEASE

        result = {
            "providers_checked": 0,
            "reminders_scheduled": 0,
            "reminders_claimed": 0,
            "reminders_sent": 0,
            "reminders_failed": 0,
        }

        for repositories in self.repository_provider.active_reminder_repositories():
            result["providers_checked"] += 1
            todos = repositories.todos
            users = repositories.users
            try:
                unscheduled = todos.get_unscheduled_reminders(self.SCHEDULE_BATCH_SIZE)
                for todo in unscheduled:
                    if todo.due_date is None:
                        continue
                    scheduled_at = calculate_reminder_due_at(todo.due_date, current)
                    if todos.schedule_reminder(todo.id, todo.due_date, scheduled_at):
                        result["reminders_scheduled"] += 1

                claim_id = str(uuid4())
                claimed = todos.claim_due_reminders(
                    now=current,
                    lease_until=lease_until,
                    claim_id=claim_id,
                    limit=self.CLAIM_BATCH_SIZE,
                )
                result["reminders_claimed"] += len(claimed)
            except Exception:
                result["reminders_failed"] += 1
                logger.exception("Could not prepare due reminders for an active database.")
                continue

            for todo in claimed:
                reminder_due_at = todo.reminder_due_at
                if not todo.owner_id or not todo.due_date or reminder_due_at is None:
                    self._release_claim(todos, todo, claim_id)
                    result["reminders_failed"] += 1
                    logger.error("A claimed Todo reminder is missing owner or date data.")
                    continue

                try:
                    latest = todos.get_by_id(todo.id, todo.owner_id)
                    if (
                        latest is None
                        or latest.completed
                        or latest.due_date is None
                        or latest.due_date != todo.due_date
                        or latest.reminder_due_at != reminder_due_at
                        or latest.reminder_claim_id != claim_id
                    ):
                        self._release_claim(todos, todo, claim_id)
                        continue

                    user = users.get_by_id(todo.owner_id)
                    if user is None or not user.email:
                        raise ValueError("The Todo owner has no email address.")
                    self.email_sender.send_todo_reminder_email(
                        user.email, latest.title, latest.due_date
                    )
                except Exception:
                    result["reminders_failed"] += 1
                    logger.exception("Failed to deliver a Todo due-date reminder.")
                    self._release_claim(todos, todo, claim_id)
                    continue

                try:
                    marked_sent = todos.mark_reminder_sent(
                        todo.id,
                        reminder_due_at,
                        claim_id,
                        datetime.now(timezone.utc),
                    )
                except Exception:
                    # Keep the lease after delivery. Retrying immediately could send
                    # a duplicate if SMTP succeeded but persistence failed.
                    result["reminders_failed"] += 1
                    logger.exception(
                        "Email was accepted, but reminder delivery could not be recorded."
                    )
                    continue

                if marked_sent:
                    result["reminders_sent"] += 1
                else:
                    result["reminders_failed"] += 1
                    logger.warning(
                        "A delivered reminder no longer owns its database claim."
                    )

        return result

    @staticmethod
    def _release_claim(repository, todo, claim_id: str) -> None:
        if todo.reminder_due_at is None:
            return
        try:
            repository.release_reminder_claim(
                todo.id, todo.reminder_due_at, claim_id
            )
        except Exception:
            logger.exception("Could not release a failed Todo reminder claim.")
