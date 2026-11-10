"""Provides a command-line tool to send database switching requests to the FastAPI backend through a Windows Named Pipe."""
import argparse
import ctypes
import os
import sys
from multiprocessing.connection import AuthenticationError, Client
from pathlib import Path
from queue import Queue
from threading import Thread


PROJECT_ROOT = Path(__file__).resolve().parent
DEFAULT_PIPE_NAME = r"\\.\pipe\TodoApiDatabaseSwitch"


def _read_project_env() -> dict:
    values = {}
    env_path = PROJECT_ROOT / ".env"
    if not env_path.is_file():
        return values
    for raw_line in env_path.read_text(encoding="utf-8-sig").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
            value = value[1:-1]
        values[key.strip()] = value
    return values


def _wait_for_pipe(address: str, timeout_seconds: float) -> None:
    if os.name != "nt":
        raise RuntimeError("Database switching is supported on Windows only.")
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    wait_named_pipe = kernel32.WaitNamedPipeW
    wait_named_pipe.argtypes = (ctypes.c_wchar_p, ctypes.c_uint32)
    wait_named_pipe.restype = ctypes.c_int
    timeout_ms = max(1, int(timeout_seconds * 1000))
    if not wait_named_pipe(address, timeout_ms):
        error_code = ctypes.get_last_error()
        if error_code == 2:
            raise ConnectionError("FastAPI is not running or its switch pipe is unavailable.")
        if error_code == 121:
            raise TimeoutError("Timed out waiting for the FastAPI switch pipe.")
        raise OSError(error_code, "Could not connect to the FastAPI switch pipe.")


def send_switch_request(provider: str, address: str, authkey: str, timeout: float = 5.0) -> dict:
    if not authkey:
        raise RuntimeError(
            "DATABASE_SWITCH_PIPE_AUTHKEY is missing. Configure it in the project .env file."
        )
    if len(authkey) < 32:
        raise RuntimeError("DATABASE_SWITCH_PIPE_AUTHKEY must contain at least 32 characters.")

    result_queue = Queue(maxsize=1)

    def communicate() -> None:
        try:
            _wait_for_pipe(address, timeout)
            with Client(address, family="AF_PIPE", authkey=authkey.encode("utf-8")) as connection:
                connection.send({"action": "switch_database", "provider": provider})
                result_queue.put(connection.recv())
        except Exception as error:
            result_queue.put(error)

    worker = Thread(target=communicate, daemon=True)
    worker.start()
    worker.join(timeout)
    if worker.is_alive():
        raise TimeoutError("Timed out waiting for the FastAPI database switch response.")
    result = result_queue.get_nowait()
    if isinstance(result, Exception):
        raise result
    if not isinstance(result, dict) or "ok" not in result or "message" not in result:
        raise RuntimeError("FastAPI returned an invalid switch response.")
    return result


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Change the running Todo API's default registration database."
    )
    parser.add_argument("provider", help="mongodb, firebase, or postgresql")
    parser.add_argument("--timeout", type=float, default=5.0)
    args = parser.parse_args()

    env_values = _read_project_env()
    authkey = os.environ.get(
        "DATABASE_SWITCH_PIPE_AUTHKEY",
        env_values.get("DATABASE_SWITCH_PIPE_AUTHKEY", ""),
    )
    address = os.environ.get(
        "DATABASE_SWITCH_PIPE_NAME",
        env_values.get("DATABASE_SWITCH_PIPE_NAME", DEFAULT_PIPE_NAME),
    )
    try:
        response = send_switch_request(args.provider, address, authkey, args.timeout)
    except (OSError, RuntimeError, TimeoutError, AuthenticationError) as error:
        print(f"Database switch failed: {error}", file=sys.stderr)
        return 1

    if not response["ok"]:
        print(f"Database switch failed: {response['message']}", file=sys.stderr)
        return 1
    print(response["message"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
