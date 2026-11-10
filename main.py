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
from infrastructure.database.account_registry_initializer import AccountRegistryInitializer
from infrastructure.database.provider_catalog import (
    DatabaseCatalog,
    DynamicTodoRepository,
    DynamicUserRepository,
    ProviderRequestScopeMiddleware,
)
from infrastructure.repositories.mongodb.account_registry_repository import (
    MongoAccountRegistryRepository,
)
from infrastructure.database.switch_pipe import DatabaseSwitchPipeServer


database_catalog = DatabaseCatalog(settings.DATABASE_PROVIDER)
account_registry = MongoAccountRegistryRepository()
account_registry_initializer = AccountRegistryInitializer(account_registry, database_catalog)
todo_repository = DynamicTodoRepository(database_catalog)
user_repository = DynamicUserRepository(database_catalog)
password_hasher = PasswordHasher()
token_service = TokenService()
sign_up = SignUp(
    user_repository,
    password_hasher,
    token_service,
    account_registry=account_registry,
    provider_catalog=database_catalog,
)
log_in = LogIn(
    user_repository,
    password_hasher,
    token_service,
    account_registry=account_registry,
    provider_catalog=database_catalog,
)
database_switch_pipe = DatabaseSwitchPipeServer(database_catalog)


# ----------------------------------------------------
# Application Lifespan (Startup & Shutdown)
# ----------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):
    database_catalog.initialize_all()
    try:
        account_registry_initializer.initialize()
        database_switch_pipe.start()
        print(f"Default registration database: {database_catalog.default_provider}")
        yield
    finally:
        database_switch_pipe.stop()
        database_catalog.close_all()


# ----------------------------------------------------
# FastAPI Application (Delivery Framework)
# ----------------------------------------------------

app = FastAPI(
    title="Todo API",
    description="Todo CRUD API implementing Domain-Driven Design & Onion Architecture",
    version="1.0.0",
    lifespan=lifespan,
)
app.state.provider_catalog = database_catalog
app.state.account_registry = account_registry
app.state.token_service = token_service
app.add_middleware(ProviderRequestScopeMiddleware, catalog=database_catalog)
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

# 2. Application Layer: Use cases with injected Domain Repository
create_todo = CreateTodo(repository=todo_repository)
get_todo = GetTodo(repository=todo_repository)
get_all_todos = GetAllTodos(repository=todo_repository)
update_todo = UpdateTodo(repository=todo_repository)
patch_todo = PatchTodo(repository=todo_repository)
delete_todo = DeleteTodo(repository=todo_repository)

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
