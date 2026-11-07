from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

from application.use_cases.create_todo import CreateTodo
from application.use_cases.get_todo import GetTodo
from application.use_cases.get_all_todos import GetAllTodos
from application.use_cases.update_todo import UpdateTodo
from application.use_cases.patch_todo import PatchTodo
from application.use_cases.delete_todo import DeleteTodo
from presentation.controllers.todo_controller import TodoController
from presentation.routes.todo_routes import create_todo_routes
from infrastructure.security.auth import PasswordHasher, TokenService
from application.use_cases.sign_up import SignUp
from application.use_cases.log_in import LogIn
from presentation.controllers.auth_controller import AuthController
from presentation.routes.auth_routes import create_auth_routes
from infrastructure.config.settings import settings


if settings.DATABASE_PROVIDER == "mongodb":
    from infrastructure.database.mongodb.client import (
        connect_to_mongodb as connect_database,
        close_mongodb_connection as close_database,
        get_todo_collection,
        get_user_collection,
    )
    from infrastructure.repositories.mongodb.todo_repository import MongoTodoRepository
    from infrastructure.repositories.mongodb.user_repository import MongoUserRepository

    todo_repository = MongoTodoRepository(collection=get_todo_collection())
    user_repository = MongoUserRepository(collection=get_user_collection())
elif settings.DATABASE_PROVIDER == "firebase":
    from infrastructure.database.firebase.client import (
        connect_to_firebase as connect_database,
        close_firebase as close_database,
    )
    from infrastructure.repositories.firebase.todo_repository import FirebaseTodoRepository
    from infrastructure.repositories.firebase.user_repository import FirebaseUserRepository

    todo_repository = FirebaseTodoRepository()
    user_repository = FirebaseUserRepository()
elif settings.DATABASE_PROVIDER == "postgresql":
    from infrastructure.database.postgres.client import (
        connect_to_postgres as connect_database,
        close_postgres as close_database,
    )
    from infrastructure.repositories.postgres.todo_repository import PostgresTodoRepository
    from infrastructure.repositories.postgres.user_repository import PostgresUserRepository

    todo_repository = PostgresTodoRepository()
    user_repository = PostgresUserRepository()
else:
    raise ValueError("DATABASE_PROVIDER must be 'mongodb', 'firebase', or 'postgresql'.")


# ----------------------------------------------------
# Application Lifespan (Startup & Shutdown)
# ----------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):
    connect_database()
    user_repository.ensure_indexes()
    yield
    close_database()


# ----------------------------------------------------
# FastAPI Application (Delivery Framework)
# ----------------------------------------------------

app = FastAPI(
    title="Todo API",
    description="Todo CRUD API implementing Domain-Driven Design & Onion Architecture",
    version="1.0.0",
    lifespan=lifespan,
)
app.state.user_repository = user_repository

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.FRONTEND_URL],
    allow_credentials=True,                   # Required for cookies
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(Exception)
async def handle_unexpected_error(request: Request, error: Exception) -> JSONResponse:
    return JSONResponse(
        status_code=500,
        content={"detail": "An unexpected error occurred."},
    )


# ----------------------------------------------------
# Composition Root
# ----------------------------------------------------

# 1. Infrastructure Layer: Database collection & Repository adapter
password_hasher = PasswordHasher()
token_service = TokenService()

# 2. Application Layer: Use cases with injected Domain Repository
create_todo = CreateTodo(repository=todo_repository)
get_todo = GetTodo(repository=todo_repository)
get_all_todos = GetAllTodos(repository=todo_repository)
update_todo = UpdateTodo(repository=todo_repository)
patch_todo = PatchTodo(repository=todo_repository)
delete_todo = DeleteTodo(repository=todo_repository)
sign_up = SignUp(user_repository, password_hasher, token_service)
log_in = LogIn(user_repository, password_hasher, token_service)

# 3. Presentation Layer: Controller with injected Use Cases
todo_controller = TodoController(
    create_todo=create_todo,
    get_todo=get_todo,
    get_all_todos=get_all_todos,
    update_todo=update_todo,
    patch_todo=patch_todo,
    delete_todo=delete_todo,
)

# 4. Presentation Layer: Register API Routes
app.include_router(create_todo_routes(controller=todo_controller))
auth_controller = AuthController(sign_up=sign_up, log_in=log_in)
app.include_router(create_auth_routes(controller=auth_controller))


# ----------------------------------------------------
# Root / Health Check
# ----------------------------------------------------

@app.get("/", tags=["Health"])
def root():
    return {
        "status": "healthy",
        "message": "Todo API is running with Onion Architecture",
    }
