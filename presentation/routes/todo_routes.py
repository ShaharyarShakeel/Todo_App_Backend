from typing import List
from fastapi import APIRouter, Depends, status

from presentation.controllers.todo_controller import TodoController
from presentation.dependencies.auth import get_current_user
from presentation.schemas.todo_schema import (
    TodoCreateSchema,
    TodoUpdateSchema,
    TodoPatchSchema,
    TodoResponseSchema,
)


def create_todo_routes(controller: TodoController) -> APIRouter:
    """Creates and configures the FastAPI router for Todo endpoints."""

    router = APIRouter(
        prefix="/todos",
        tags=["Todos"],
    )

    @router.post(
        "/",
        response_model=TodoResponseSchema,
        status_code=status.HTTP_201_CREATED,
        summary="Create a new todo",
    )
    def create_todo(
        data: TodoCreateSchema,
        owner_id: str = Depends(get_current_user),
    ):
        return controller.create(data, owner_id)

    @router.get(
        "/",
        response_model=List[TodoResponseSchema],
        status_code=status.HTTP_200_OK,
        summary="List all todos",
    )
    def get_all_todos(owner_id: str = Depends(get_current_user)):
        return controller.get_all(owner_id)

    @router.get(
        "/{todo_id}",
        response_model=TodoResponseSchema,
        status_code=status.HTTP_200_OK,
        summary="Get a todo by ID",
    )
    def get_todo(todo_id: str, owner_id: str = Depends(get_current_user)):
        return controller.get_by_id(todo_id, owner_id)

    @router.put(
        "/{todo_id}",
        response_model=TodoResponseSchema,
        status_code=status.HTTP_200_OK,
        summary="Update a todo completely",
    )
    def update_todo(
        todo_id: str,
        data: TodoUpdateSchema,
        owner_id: str = Depends(get_current_user),
    ):
        return controller.update(todo_id, data, owner_id)

    @router.patch(
        "/{todo_id}",
        response_model=TodoResponseSchema,
        status_code=status.HTTP_200_OK,
        summary="Partially update a todo",
    )
    def patch_todo(
        todo_id: str,
        data: TodoPatchSchema,
        owner_id: str = Depends(get_current_user),
    ):
        return controller.patch(todo_id, data, owner_id)

    @router.delete(
        "/{todo_id}",
        status_code=status.HTTP_200_OK,
        summary="Delete a todo",
    )
    def delete_todo(todo_id: str, owner_id: str = Depends(get_current_user)):
        return controller.delete(todo_id, owner_id)

    return router