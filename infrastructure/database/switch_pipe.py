"""Runs a secure local server to receive and process database switching requests."""
"""Implements secure communication between separate processes using Python's multiprocessing.connection Listener and Windows Named Pipes (AF_PIPE), with threading for background listening, Event for stopping the server, and an authentication key for secure communication."""
import os
from multiprocessing.connection import AuthenticationError, Listener
from threading import Event, Thread

from infrastructure.config.settings import settings


class DatabaseSwitchPipeServer:
    """Authenticated local IPC listener for changing the registration default."""

    def __init__(self, catalog, address=None, authkey=None):
        self.catalog = catalog
        self.address = address or settings.DATABASE_SWITCH_PIPE_NAME
        self.authkey = (authkey or settings.DATABASE_SWITCH_PIPE_AUTHKEY).encode("utf-8")
        self._listener = None
        self._thread = None
        self._stop_event = Event()

    def start(self) -> None:
        if os.name != "nt":
            raise RuntimeError("The database switch pipe is supported on Windows only.")
        if not self.authkey:
            raise RuntimeError(
                "DATABASE_SWITCH_PIPE_AUTHKEY must be configured in .env before startup."
            )
        if len(self.authkey) < 32:
            raise RuntimeError(
                "DATABASE_SWITCH_PIPE_AUTHKEY must contain at least 32 characters."
            )
        if self._thread is not None and self._thread.is_alive():
            return
        self._stop_event.clear()
        # Binding synchronously makes pipe name conflicts visible during app startup.
        self._listener = Listener(
            address=self.address,
            family="AF_PIPE",
            authkey=self.authkey,
        )
        self._thread = Thread(
            target=self._serve,
            name="database-switch-pipe",
            daemon=True,
        )
        self._thread.start()
        print("Database switch named pipe is ready")

    def stop(self) -> None:
        self._stop_event.set()
        listener, self._listener = self._listener, None
        if listener is not None:
            listener.close()
        thread, self._thread = self._thread, None
        if thread is not None:
            thread.join(timeout=2)

    def _serve(self) -> None:
        listener = self._listener
        if listener is None:
            return
        while not self._stop_event.is_set():
            try:
                connection = listener.accept()
            except (OSError, EOFError, AuthenticationError):
                if self._stop_event.is_set():
                    return
                continue
            try:
                request = connection.recv()
                response = self._handle(request)
                connection.send(response)
            except (EOFError, OSError):
                pass
            finally:
                connection.close()

    def _handle(self, request) -> dict:
        if not isinstance(request, dict) or set(request) != {"action", "provider"}:
            return {"ok": False, "message": "Invalid switch command."}
        if request.get("action") != "switch_database":
            return {"ok": False, "message": "Unsupported switch action."}
        provider = request.get("provider")
        try:
            previous, active, changed = self.catalog.switch_default(provider)
        except (TypeError, ValueError, RuntimeError) as error:
            return {"ok": False, "message": str(error)}
        if not changed:
            return {
                "ok": True,
                "provider": active,
                "message": f"'{active}' is already the default registration database.",
            }
        return {
            "ok": True,
            "provider": active,
            "previous_provider": previous,
            "message": f"Default registration database changed from '{previous}' to '{active}'.",
        }
