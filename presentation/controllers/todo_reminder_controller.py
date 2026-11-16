from application.use_cases.send_todo_reminders import SendTodoReminders


class TodoReminderController:
    """Dispatches the protected cron request to the reminder use case."""

    def __init__(self, send_todo_reminders: SendTodoReminders):
        self.send_todo_reminders = send_todo_reminders

    def send_due_reminders(self) -> dict:
        return self.send_todo_reminders.execute()
