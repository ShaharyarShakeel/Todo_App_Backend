import hmac

from fastapi import APIRouter, Depends, Header, HTTPException, Request, status

from presentation.controllers.todo_reminder_controller import TodoReminderController


def create_cron_routes(controller: TodoReminderController) -> APIRouter:
    router = APIRouter(prefix="/api/cron", tags=["Cron jobs"])

    async def authorize_cron_request(
        request: Request,
        cron_secret: str | None = Header(default=None, alias="X-Cron-Secret"),
    ) -> None:
        expected_secret = request.app.state.cron_secret
        if not expected_secret:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Cron endpoint is not configured.",
            )
        if cron_secret is None or not hmac.compare_digest(
            cron_secret, expected_secret
        ):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid cron authentication.",
            )

    @router.post(
        "/send-todo-reminders",
        status_code=status.HTTP_200_OK,
        summary="Send due Todo reminders",
        dependencies=[Depends(authorize_cron_request)],
    )
    def send_todo_reminders():
        return controller.send_due_reminders()

    return router
