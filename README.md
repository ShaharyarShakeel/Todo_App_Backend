# Todo API

FastAPI backend with separate onion architecture and MVC implementations. Firebase is wired only to the onion architecture; the `mvc/` implementation remains MongoDB-only.

## Onion architecture database

The onion API selects its persistence adapter with `DATABASE_PROVIDER` (`firebase`, `mongodb`, or `postgresql`). The local, Git-ignored `.env` selects PostgreSQL; without that variable, the code defaults to Firebase. Firebase uses Cloud Firestore through the Firebase Admin SDK. PostgreSQL uses the `POSTGRES_URL` connection string.

The root `.env` file stores the local database choice and connection settings, JWT signing values, and allowed frontend origin. It is Git-ignored. Start the API with:

```powershell
uvicorn main:app --reload
```

The Firebase credential JSON must remain outside the repository. Override `FIREBASE_CREDENTIALS_PATH` via the process environment when running elsewhere. For hosted environments, set it to an empty string and configure Google Application Default Credentials. `JWT_SECRET_KEY` must be set; use a unique, high entropy secret per deployment. Set `FRONTEND_URL` to the frontend's exact origin (scheme and host, plus port if needed).

To use PostgreSQL, set `DATABASE_PROVIDER=postgresql` and configure `POSTGRES_URL`. The app creates the `todos` and `users` tables and the todo owner index on startup if they do not exist. To use MongoDB for the onion API, set `DATABASE_PROVIDER=mongodb` and configure `MONGO_URL` plus the optional Mongo database and collection variables. The independent MVC app continues to use its own MongoDB configuration and is not affected by the provider setting.

Firebase and PostgreSQL adapters live in provider-specific folders under `infrastructure/database/` and `infrastructure/repositories/`. MongoDB adapters remain in their existing files under those infrastructure folders.
