import unittest
from dataclasses import FrozenInstanceError

from domain.entities.todo import Todo
from domain.exceptions.todo_exceptions import (
    TodoTitleRequiredError,
    TodoTitleTooLongError,
)
from domain.value_objects import TodoDescription, TodoTitle


class TestTodoDomainEntity(unittest.TestCase):
    """Unit tests for the Todo Domain Entity (Core Ring)."""

    def test_create_valid_todo(self):
        todo = Todo(title="Buy milk", description="Low fat milk", completed=False)
        self.assertEqual(todo.title, "Buy milk")
        self.assertEqual(todo.description, "Low fat milk")
        self.assertFalse(todo.completed)
        self.assertIsNone(todo.id)

    def test_create_todo_empty_title_raises_domain_exception(self):
        with self.assertRaises(TodoTitleRequiredError):
            Todo(title="")

        with self.assertRaises(TodoTitleRequiredError):
            Todo(title="   ")

    def test_create_todo_title_too_long_raises_domain_exception(self):
        long_title = "a" * (Todo.MAX_TITLE_LENGTH + 1)
        with self.assertRaises(TodoTitleTooLongError):
            Todo(title=long_title)

    def test_mark_completed_and_incomplete(self):
        todo = Todo(title="Task 1", completed=False)
        self.assertFalse(todo.completed)

        todo.mark_completed()
        self.assertTrue(todo.completed)

        todo.mark_incomplete()
        self.assertFalse(todo.completed)

    def test_update_details(self):
        todo = Todo(title="Initial", description="Initial desc", completed=False)
        todo.update(title="Updated Title", description="Updated desc", completed=True)

        self.assertEqual(todo.title, "Updated Title")
        self.assertEqual(todo.description, "Updated desc")
        self.assertTrue(todo.completed)

    def test_update_title_invalid_raises_error(self):
        todo = Todo(title="Valid Title")
        with self.assertRaises(TodoTitleRequiredError):
            todo.update_title("")

    def test_value_objects_are_immutable_and_normalize_values(self):
        title = TodoTitle("  Buy milk  ")
        description = TodoDescription("  Low fat milk  ")

        self.assertEqual(title.value, "Buy milk")
        self.assertEqual(description.value, "Low fat milk")
        with self.assertRaises(FrozenInstanceError):
            title.value = "Changed"
        with self.assertRaises(FrozenInstanceError):
            description.value = "Changed"

    def test_todo_uses_value_objects_for_title_and_description(self):
        todo = Todo(title="  Buy milk  ", description="  Low fat milk  ")

        self.assertIsInstance(todo._title, TodoTitle)
        self.assertIsInstance(todo._description, TodoDescription)
        self.assertEqual(todo.title, "Buy milk")
        self.assertEqual(todo.description, "Low fat milk")


if __name__ == "__main__":
    unittest.main()
