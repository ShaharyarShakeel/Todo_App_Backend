from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from infrastructure.persistence.mongodb.mvc_database import Database
from mvc.routes.todo_routes import router as mvc_todo_router
from mvc.routes.auth_routes import router as mvc_auth_router
from mvc.models.user_model import UserModel

@asynccontextmanager
async def lifespan(app: FastAPI):
    client = Database.get_client()
    client.admin.command("ping")
    UserModel.ensure_indexes()
    print("MVC App: MongoDB connected successfully")
    yield
    Database.close()
    print("MVC App: MongoDB connection closed")

app = FastAPI(
    title="Todo API - MVC Architecture",
    description="Todo CRUD API implementing traditional Model-View-Controller (MVC) architecture",
    version="1.0.0",
    lifespan=lifespan,
)


@app.exception_handler(Exception)
async def handle_unexpected_error(request: Request, error: Exception) -> JSONResponse:
    return JSONResponse(
        status_code=500,
        content={"detail": "An unexpected error occurred."},
    )


app.include_router(mvc_todo_router)
app.include_router(mvc_auth_router)

@app.get("/", tags=["Health"])
def root():
    return {
        "status": "healthy",
        "architecture": "MVC (Model-View-Controller)",
        "message": "Todo API is running with MVC Architecture",
    }
