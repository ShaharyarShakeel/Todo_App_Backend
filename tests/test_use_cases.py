import unittest

from application.use_cases.create_todo import CreateTodo
from application.use_cases.get_todo import GetTodo
from application.use_cases.get_all_todos import GetAllTodos
from application.use_cases.update_todo import UpdateTodo
from application.use_cases.patch_todo import PatchTodo
from application.use_cases.delete_todo import DeleteTodo
from application.dtos.todo_dto import (
    TodoCreateDTO,
    TodoUpdateDTO,
    TodoPatchDTO,
)
from domain.exceptions.todo_exceptions import (
    TodoNotFoundError,
    TodoTitleRequiredError,
)
from infrastructure.repositories.in_memory_todo_repository import (
    InMemoryTodoRepository,
)


class TestTodoUseCases(unittest.TestCase):
    """Unit tests for Application Use Cases (Application Ring) using InMemoryTodoRepository."""

    def setUp(self):
        self.repository = InMemoryTodoRepository()
        self.owner_id = "user-1"
        self.create_todo = CreateTodo(self.repository)
        self.get_todo = GetTodo(self.repository)
        self.get_all_todos = GetAllTodos(self.repository)
        self.update_todo = UpdateTodo(self.repository)
        self.patch_todo = PatchTodo(self.repository)
        self.delete_todo = DeleteTodo(self.repository)

    def test_create_todo_use_case(self):
        todo = self.create_todo.execute(
            TodoCreateDTO(
                title="Learn DDD",
                description="Onion architecture in Python",
            ),
            self.owner_id,
        )
        self.assertIsNotNone(todo.id)
        self.assertEqual(todo.title, "Learn DDD")
        self.assertEqual(todo.description, "Onion architecture in Python")
        self.assertFalse(todo.completed)

    def test_get_todo_by_id(self):
        created = self.create_todo.execute(
            TodoCreateDTO(title="Test Get"), self.owner_id
        )
        found = self.get_todo.execute(created.id, self.owner_id)
        self.assertEqual(found.id, created.id)
        self.assertEqual(found.title, "Test Get")

    def test_get_nonexistent_todo_raises_not_found(self):
        with self.assertRaises(TodoNotFoundError):
            self.get_todo.execute("non-existent-id", self.owner_id)

    def test_get_all_todos(self):
        self.create_todo.execute(TodoCreateDTO(title="Task 1"), self.owner_id)
        self.create_todo.execute(TodoCreateDTO(title="Task 2"), self.owner_id)
        todos = self.get_all_todos.execute(self.owner_id)
        self.assertEqual(len(todos), 2)

    def test_update_todo(self):
        created = self.create_todo.execute(
            TodoCreateDTO(title="Old Title", description="Old Desc"),
            self.owner_id,
        )
        updated = self.update_todo.execute(
            TodoUpdateDTO(
                todo_id=created.id,
                title="New Title",
                description="New Desc",
                completed=True,
            ),
            self.owner_id,
        )
        self.assertEqual(updated.title, "New Title")
        self.assertEqual(updated.description, "New Desc")
        self.assertTrue(updated.completed)

    def test_patch_todo(self):
        created = self.create_todo.execute(
            TodoCreateDTO(title="Base Title", description="Base Desc"),
            self.owner_id,
        )
        patched = self.patch_todo.execute(
            TodoPatchDTO(todo_id=created.id, completed=True), self.owner_id
        )
        self.assertEqual(patched.title, "Base Title")
        self.assertEqual(patched.description, "Base Desc")
        self.assertTrue(patched.completed)

    def test_patch_todo_title_validation(self):
        created = self.create_todo.execute(
            TodoCreateDTO(title="Base Title"), self.owner_id
        )
        with self.assertRaises(TodoTitleRequiredError):
            self.patch_todo.execute(
                TodoPatchDTO(todo_id=created.id, title=""), self.owner_id
            )

    def test_delete_todo(self):
        created = self.create_todo.execute(
            TodoCreateDTO(title="To Delete"), self.owner_id
        )
        success = self.delete_todo.execute(created.id, self.owner_id)
        self.assertTrue(success)

        with self.assertRaises(TodoNotFoundError):
            self.get_todo.execute(created.id, self.owner_id)


if __name__ == "__main__":
    unittest.main()
