import unittest
from unittest.mock import Mock, patch

from bson import ObjectId

from mvc.models.todo_model import TodoModel


class TestMVCTodoOwnershipQueries(unittest.TestCase):
    def test_create_and_crud_queries_include_the_owner_id(self):
        collection = Mock()
        todo_id = ObjectId()
        collection.insert_one.return_value.inserted_id = todo_id
        collection.find.return_value = []
        collection.find_one.return_value = None
        collection.update_one.return_value.matched_count = 0
        collection.delete_one.return_value.deleted_count = 0
        owner_id = "mvc-owner-123"

        with patch(
            "mvc.models.todo_model.Database.get_collection",
            return_value=collection,
        ):
            created = TodoModel.create(
                title="Owned todo",
                description=None,
                owner_id=owner_id,
            )
            self.assertEqual(created.owner_id, owner_id)
            collection.insert_one.assert_called_once_with(
                {
                    "title": "Owned todo",
                    "description": None,
                    "completed": False,
                    "owner_id": owner_id,
                }
            )

            TodoModel.find_all(owner_id)
            collection.find.assert_called_once_with({"owner_id": owner_id})

            TodoModel.find_by_id(str(todo_id), owner_id)
            collection.find_one.assert_called_once_with(
                {"_id": todo_id, "owner_id": owner_id}
            )

            TodoModel.update(
                todo_id=str(todo_id),
                title="Updated",
                owner_id=owner_id,
            )
            self.assertEqual(
                collection.update_one.call_args.args[0],
                {"_id": todo_id, "owner_id": owner_id},
            )

            TodoModel.patch(
                todo_id=str(todo_id),
                title="Patched",
                owner_id=owner_id,
            )
            self.assertEqual(
                collection.update_one.call_args.args[0],
                {"_id": todo_id, "owner_id": owner_id},
            )

            TodoModel.delete(str(todo_id), owner_id)
            collection.delete_one.assert_called_once_with(
                {"_id": todo_id, "owner_id": owner_id}
            )


if __name__ == "__main__":
    unittest.main()
