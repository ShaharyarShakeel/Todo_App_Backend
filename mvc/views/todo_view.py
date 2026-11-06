from typing import Optional, List, Dict, Any
from pydantic import BaseModel, ConfigDict, Field

class TodoCreateView(BaseModel):
    title: str = Field(..., min_length=1, max_length=200, description="Title of the todo")
    description: Optional[str] = Field(default=None, description="Optional description")

class TodoUpdateView(BaseModel):
    title: str = Field(..., min_length=1, max_length=200, description="Title of the todo")
    description: Optional[str] = Field(default=None, description="Optional description")
    completed: bool = Field(..., description="Completion status")

class TodoPatchView(BaseModel):
    title: Optional[str] = Field(default=None, min_length=1, max_length=200)
    description: Optional[str] = None
    completed: Optional[bool] = None

class TodoResponseView(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    title: str
    description: Optional[str] = None
    completed: bool

class TodoView:
    @staticmethod
    def render_todo(todo) -> Dict[str, Any]:
        return {
            "id": todo.id,
            "title": todo.title,
            "description": todo.description,
            "completed": todo.completed,
        }

    @staticmethod
    def render_todos(todos) -> List[Dict[str, Any]]:
        return [TodoView.render_todo(t) for t in todos]

    @staticmethod
    def render_message(message: str) -> Dict[str, str]:
        return {"message": message}
