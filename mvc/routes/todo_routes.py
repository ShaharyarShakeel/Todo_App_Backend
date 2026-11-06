from typing import List
from fastapi import APIRouter, Depends, status
from mvc.controllers.todo_controller import TodoController
from presentation.dependencies.auth import get_current_user
from mvc.views.todo_view import (
    TodoCreateView,
    TodoUpdateView,
    TodoPatchView,
    TodoResponseView,
)

router = APIRouter(prefix="/todos", tags=["MVC Todos"])

@router.post(
    "/",
    response_model=TodoResponseView,
    status_code=status.HTTP_201_CREATED,
    summary="[MVC] Create a new todo",
)
def create_todo(
    payload: TodoCreateView,
    owner_id: str = Depends(get_current_user),
):
    return TodoController.create_todo(payload, owner_id)

@router.get(
    "/",
    response_model=List[TodoResponseView],
    status_code=status.HTTP_200_OK,
    summary="[MVC] List all todos",
)
def get_all_todos(owner_id: str = Depends(get_current_user)):
    return TodoController.get_all_todos(owner_id)

@router.get(
    "/{todo_id}",
    response_model=TodoResponseView,
    status_code=status.HTTP_200_OK,
    summary="[MVC] Get todo by ID",
)
def get_todo(todo_id: str, owner_id: str = Depends(get_current_user)):
    return TodoController.get_todo_by_id(todo_id, owner_id)

@router.put(
    "/{todo_id}",
    response_model=TodoResponseView,
    status_code=status.HTTP_200_OK,
    summary="[MVC] Update a todo completely",
)
def update_todo(
    todo_id: str,
    payload: TodoUpdateView,
    owner_id: str = Depends(get_current_user),
):
    return TodoController.update_todo(todo_id, payload, owner_id)

@router.patch(
    "/{todo_id}",
    response_model=TodoResponseView,
    status_code=status.HTTP_200_OK,
    summary="[MVC] Partially update a todo",
)
def patch_todo(
    todo_id: str,
    payload: TodoPatchView,
    owner_id: str = Depends(get_current_user),
):
    return TodoController.patch_todo(todo_id, payload, owner_id)

@router.delete(
    "/{todo_id}",
    status_code=status.HTTP_200_OK,
    summary="[MVC] Delete a todo",
)
def delete_todo(todo_id: str, owner_id: str = Depends(get_current_user)):
    return TodoController.delete_todo(todo_id, owner_id)
