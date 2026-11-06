from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

from infrastructure.persistence.mongodb.database import (
    connect_to_mongodb,
    close_mongodb_connection,
    get_todo_collection,
    get_user_collection,
)
from infrastructure.firebase.admin import initialize_firebase, close_firebase
from infrastructure.persistence.mongodb.repositories.todo_repository import (
    MongoTodoRepository,
)
from application.use_cases.create_todo import CreateTodo
from application.use_cases.get_todo import GetTodo
from application.use_cases.get_all_todos import GetAllTodos
from application.use_cases.update_todo import UpdateTodo
from application.use_cases.patch_todo import PatchTodo
from application.use_cases.delete_todo import DeleteTodo
from presentation.controllers.todo_controller import TodoController
from presentation.routes.todo_routes import create_todo_routes
from infrastructure.persistence.mongodb.repositories.user_repository import MongoUserRepository
from infrastructure.security.auth import PasswordHasher, TokenService
from application.use_cases.sign_up import SignUp
from application.use_cases.log_in import LogIn
from presentation.controllers.auth_controller import AuthController
from presentation.routes.auth_routes import create_auth_routes


# ----------------------------------------------------
# Application Lifespan (Startup & Shutdown)
# ----------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: initialize external infrastructure
    connect_to_mongodb()
    try:
        initialize_firebase()
        user_repository.ensure_indexes()
        yield
    finally:
        # Shutdown: Close external infrastructure cleanly.
        close_mongodb_connection()
        close_firebase()


# ----------------------------------------------------
# FastAPI Application (Delivery Framework)
# ----------------------------------------------------

app = FastAPI(
    title="Todo API",
    description="Todo CRUD API implementing Domain-Driven Design & Onion Architecture",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],  # React Vite dev server
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
todo_collection = get_todo_collection() # this gave mongodb todos collection object
todo_repository = MongoTodoRepository(collection=todo_collection) #we pass todos collection to the mongotodorepository
user_repository = MongoUserRepository(collection=get_user_collection()) 
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
