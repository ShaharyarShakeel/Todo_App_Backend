# Todo API

FastAPI backend with separate onion architecture and MVC implementations. Firebase is wired only to the onion architecture; the `mvc/` implementation remains MongoDB-only.

## Onion architecture databases

The onion API keeps MongoDB, Firebase Firestore, and PostgreSQL initialized while it is running. MongoDB also stores the metadata-only `account_registry`, which maps each global account ID and normalized email to its original provider-specific user ID. The registry does not store passwords or todos.

On startup, the API connects to all three databases and backfills existing users. If any provider is unavailable, startup fails rather than routing its accounts elsewhere. If backfill finds duplicate normalized emails or ambiguous provider IDs, startup stops and reports the conflict rather than choosing an assignment. Existing Todo records are not moved or rewritten.

Copy `.env.example` to `.env` and set credentials for all three databases. `DATABASE_PROVIDER` sets the initial default for new registrations. Existing users always log in and use Todos through their saved provider assignment. Switching the default only changes the current process and does not invalidate tokens; restarting restores the initial value from `.env`.

Keep `.env`, the Firebase service account file, and all database credentials private. `DATABASE_SWITCH_PIPE_AUTHKEY` must be a long random local key; a key is already generated in this machine's ignored `.env`. The switch command uses the Python standard library and requires no additional package.

### Start the backend (Terminal 1)

```powershell
cd D:\Sherry\Cloudpacer\Internship\todo-api
.\venv\Scripts\Activate.ps1
uvicorn main:app
```

### Change the registration default (Terminal 2)

Run this from any working directory. The CLI uses only Python's standard library:

```powershell
python D:\Sherry\Cloudpacer\Internship\todo-api\switch_database.py firebase
python D:\Sherry\Cloudpacer\Internship\todo-api\switch_database.py postgresql
python D:\Sherry\Cloudpacer\Internship\todo-api\switch_database.py mongodb
```

If `python` is not the project's interpreter, use `D:\Sherry\Cloudpacer\Internship\todo-api\venv\Scripts\python.exe` in its place. Switching uses an authenticated Windows Named Pipe, not an HTTP route. The CLI reports success or a connection/provider error. Run a single local Uvicorn process: multiple workers or backend instances would each hold a separate in-memory default. The separate MVC app remains MongoDB-only and is not changed by this routing.

Provider adapters live under `infrastructure/repositories/{mongodb,firebase,postgres}/`; account registry and runtime provider lifecycle code live under `infrastructure/`.
