import unittest
from fastapi.testclient import TestClient
from mvc.main import app
from mvc.config.database import Database
from infrastructure.security.auth import TokenService

class TestMVCApp(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)
        token = TokenService().create_access_token("mvc-test@example.com")
        cls.client.headers["Authorization"] = f"Bearer {token}"
        try:
            Database.get_collection().delete_many({})
        except Exception:
            pass

    @classmethod
    def tearDownClass(cls):
        try:
            Database.get_collection().delete_many({})
            Database.close()
        except Exception:
            pass

    def test_01_health_check(self):
        resp = self.client.get("/")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["architecture"], "MVC (Model-View-Controller)")

    def test_02_create_todo(self):
        resp = self.client.post("/todos/", json={"title": "MVC Test Todo", "description": "Testing CRUD"})
        self.assertEqual(resp.status_code, 201)
        data = resp.json()
        self.assertEqual(data["title"], "MVC Test Todo")
        self.assertIn("id", data)

    def test_03_get_all_todos(self):
        resp = self.client.get("/todos/")
        self.assertEqual(resp.status_code, 200)
        self.assertGreaterEqual(len(resp.json()), 1)

    def test_04_get_by_id(self):
        create_resp = self.client.post("/todos/", json={"title": "Find Me"})
        todo_id = create_resp.json()["id"]
        get_resp = self.client.get(f"/todos/{todo_id}")
        self.assertEqual(get_resp.status_code, 200)
        self.assertEqual(get_resp.json()["id"], todo_id)

    def test_05_update_todo(self):
        create_resp = self.client.post("/todos/", json={"title": "To Update"})
        todo_id = create_resp.json()["id"]
        put_resp = self.client.put(f"/todos/{todo_id}", json={"title": "Updated", "completed": True})
        self.assertEqual(put_resp.status_code, 200)
        self.assertTrue(put_resp.json()["completed"])

    def test_06_delete_todo(self):
        create_resp = self.client.post("/todos/", json={"title": "To Delete"})
        todo_id = create_resp.json()["id"]
        del_resp = self.client.delete(f"/todos/{todo_id}")
        self.assertEqual(del_resp.status_code, 200)
        self.assertEqual(self.client.get(f"/todos/{todo_id}").status_code, 404)

if __name__ == "__main__":
    unittest.main()
