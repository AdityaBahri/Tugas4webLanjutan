"""
tests/test_main.py — Test Suite untuk FastAPI Microservice
===========================================================
Author  :  Ahmad Hidayat

Mencakup 3 skenario wajib:
  1. Pengujian Alur Autentikasi  (register & login → JWT token)
  2. Pengujian CRUD Operasional  (create, read, update, delete — sebagai admin)
  3. Pengujian RBAC              (user biasa → 403 Forbidden pada POST/PUT/DELETE)

Cara menjalankan
----------------
  # Pastikan dependensi sudah terinstall
  pip install -r requirements.txt

  # Jalankan seluruh test suite dari root project
  pytest tests/test_main.py -v

  # Atau jalankan dengan laporan singkat
  pytest tests/test_main.py -v --tb=short
"""

import pytest
from fastapi.testclient import TestClient

# Impor aplikasi dari main.py di root project
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import main as app_module
from main import app, fake_users_db, fake_tasks_db


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------
@pytest.fixture(autouse=True)
def reset_db():
    """
    Bersihkan in-memory database sebelum setiap test agar setiap test
    berjalan dengan state yang bersih (test isolation).
    """
    fake_users_db.clear()
    fake_tasks_db.clear()
    app_module.task_id_counter = 1
    yield
    fake_users_db.clear()
    fake_tasks_db.clear()
    app_module.task_id_counter = 1


@pytest.fixture
def client():
    """Buat TestClient sekali per test."""
    return TestClient(app)


@pytest.fixture
def admin_token(client):
    """Registrasi dan login sebagai admin, kembalikan token."""
    client.post("/register", json={"username": "admin1", "password": "adminpass", "role": "admin"})
    res = client.post("/login", data={"username": "admin1", "password": "adminpass"})
    return res.json()["access_token"]


@pytest.fixture
def user_token(client):
    """Registrasi dan login sebagai user biasa, kembalikan token."""
    client.post("/register", json={"username": "user1", "password": "userpass", "role": "user"})
    res = client.post("/login", data={"username": "user1", "password": "userpass"})
    return res.json()["access_token"]


def auth_header(token: str) -> dict:
    """Helper: buat header Authorization dari token."""
    return {"Authorization": f"Bearer {token}"}


# ===========================================================================
# SKENARIO 1 — Pengujian Alur Autentikasi
# ===========================================================================
class TestAuthFlow:
    """Test case untuk registrasi dan login (JWT Auth Flow)."""

    def test_register_success(self, client):
        """Register pengguna baru → response 201 & data user dikembalikan."""
        response = client.post(
            "/register",
            json={"username": "testuser", "password": "secret123", "role": "user"},
        )
        assert response.status_code == 201
        data = response.json()
        assert data["username"] == "testuser"
        assert data["role"] == "user"
        assert "message" in data

    def test_register_duplicate_username(self, client):
        """Registrasi username yang sudah ada → 400 Bad Request."""
        payload = {"username": "dupuser", "password": "pass", "role": "user"}
        client.post("/register", json=payload)
        response = client.post("/register", json=payload)
        assert response.status_code == 400
        assert "already registered" in response.json()["detail"]

    def test_register_invalid_role(self, client):
        """Registrasi dengan role tidak valid → 422 Unprocessable Entity."""
        response = client.post(
            "/register",
            json={"username": "baduser", "password": "pass", "role": "superuser"},
        )
        assert response.status_code == 422

    def test_login_returns_valid_token(self, client):
        """Login dengan kredensial benar → 200 OK & access_token dikembalikan."""
        client.post("/register", json={"username": "loginuser", "password": "mypassword", "role": "user"})
        response = client.post("/login", data={"username": "loginuser", "password": "mypassword"})
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"
        assert len(data["access_token"]) > 0

    def test_login_wrong_password(self, client):
        """Login dengan password salah → 401 Unauthorized."""
        client.post("/register", json={"username": "user2", "password": "correct", "role": "user"})
        response = client.post("/login", data={"username": "user2", "password": "wrong"})
        assert response.status_code == 401

    def test_login_unknown_user(self, client):
        """Login dengan username tidak terdaftar → 401 Unauthorized."""
        response = client.post("/login", data={"username": "ghost", "password": "nopass"})
        assert response.status_code == 401


# ===========================================================================
# SKENARIO 2 — Pengujian CRUD Operasional (sebagai Admin)
# ===========================================================================
class TestCRUDAdmin:
    """
    Test case untuk semua operasi CRUD menggunakan token milik Admin.
    Membuktikan bahwa admin dapat Create, Read, Update, dan Delete tasks.
    """

    def test_create_task(self, client, admin_token):
        """POST /tasks sebagai admin → 201 Created & task dikembalikan."""
        response = client.post(
            "/tasks",
            json={"title": "Task Pertama", "description": "Deskripsi task"},
            headers=auth_header(admin_token),
        )
        assert response.status_code == 201
        data = response.json()
        assert data["title"] == "Task Pertama"
        assert data["description"] == "Deskripsi task"
        assert data["id"] == 1
        assert data["owner"] == "admin1"

    def test_read_all_tasks(self, client, admin_token):
        """GET /tasks → 200 OK & mengembalikan list tasks."""
        client.post("/tasks", json={"title": "T1"}, headers=auth_header(admin_token))
        client.post("/tasks", json={"title": "T2"}, headers=auth_header(admin_token))
        response = client.get("/tasks", headers=auth_header(admin_token))
        assert response.status_code == 200
        assert len(response.json()) == 2

    def test_read_single_task(self, client, admin_token):
        """GET /tasks/{id} → 200 OK & mengembalikan task yang tepat."""
        create_res = client.post(
            "/tasks",
            json={"title": "Single Task", "description": "desc"},
            headers=auth_header(admin_token),
        )
        task_id = create_res.json()["id"]
        response = client.get(f"/tasks/{task_id}", headers=auth_header(admin_token))
        assert response.status_code == 200
        assert response.json()["title"] == "Single Task"

    def test_read_task_not_found(self, client, admin_token):
        """GET /tasks/9999 → 404 Not Found."""
        response = client.get("/tasks/9999", headers=auth_header(admin_token))
        assert response.status_code == 404

    def test_update_task(self, client, admin_token):
        """PUT /tasks/{id} sebagai admin → 200 OK & data task terupdate."""
        create_res = client.post(
            "/tasks", json={"title": "Old Title"}, headers=auth_header(admin_token)
        )
        task_id = create_res.json()["id"]
        response = client.put(
            f"/tasks/{task_id}",
            json={"title": "New Title", "description": "Updated desc"},
            headers=auth_header(admin_token),
        )
        assert response.status_code == 200
        data = response.json()
        assert data["title"] == "New Title"
        assert data["description"] == "Updated desc"

    def test_update_task_partial(self, client, admin_token):
        """PUT /tasks/{id} dengan hanya title → description tidak berubah."""
        create_res = client.post(
            "/tasks",
            json={"title": "Original", "description": "Keep this"},
            headers=auth_header(admin_token),
        )
        task_id = create_res.json()["id"]
        response = client.put(
            f"/tasks/{task_id}",
            json={"title": "Changed"},
            headers=auth_header(admin_token),
        )
        assert response.status_code == 200
        data = response.json()
        assert data["title"] == "Changed"
        assert data["description"] == "Keep this"

    def test_delete_task(self, client, admin_token):
        """DELETE /tasks/{id} sebagai admin → 200 OK & task terhapus."""
        create_res = client.post(
            "/tasks", json={"title": "To Delete"}, headers=auth_header(admin_token)
        )
        task_id = create_res.json()["id"]
        response = client.delete(f"/tasks/{task_id}", headers=auth_header(admin_token))
        assert response.status_code == 200
        assert "dihapus" in response.json()["message"]

        # Pastikan task sudah tidak ada
        get_res = client.get(f"/tasks/{task_id}", headers=auth_header(admin_token))
        assert get_res.status_code == 404

    def test_delete_task_not_found(self, client, admin_token):
        """DELETE /tasks/9999 → 404 Not Found."""
        response = client.delete("/tasks/9999", headers=auth_header(admin_token))
        assert response.status_code == 404


# ===========================================================================
# SKENARIO 3 — Pengujian RBAC (Access Denied untuk Role 'user')
# ===========================================================================
class TestRBACAccessDenied:
    """
    Test case untuk memastikan user dengan role biasa ('user')
    mendapatkan response 403 Forbidden pada endpoint POST, PUT, DELETE.
    """

    def test_user_cannot_create_task(self, client, admin_token, user_token):
        """POST /tasks sebagai 'user' → 403 Forbidden."""
        response = client.post(
            "/tasks",
            json={"title": "Unauthorized Task"},
            headers=auth_header(user_token),
        )
        assert response.status_code == 403
        assert response.json()["detail"] == "Access Denied"

    def test_user_cannot_update_task(self, client, admin_token, user_token):
        """PUT /tasks/{id} sebagai 'user' → 403 Forbidden."""
        # Admin buat task dulu
        create_res = client.post(
            "/tasks", json={"title": "Admin Task"}, headers=auth_header(admin_token)
        )
        task_id = create_res.json()["id"]

        # User coba update
        response = client.put(
            f"/tasks/{task_id}",
            json={"title": "Hacked"},
            headers=auth_header(user_token),
        )
        assert response.status_code == 403
        assert response.json()["detail"] == "Access Denied"

    def test_user_cannot_delete_task(self, client, admin_token, user_token):
        """DELETE /tasks/{id} sebagai 'user' → 403 Forbidden."""
        create_res = client.post(
            "/tasks", json={"title": "Protected Task"}, headers=auth_header(admin_token)
        )
        task_id = create_res.json()["id"]

        response = client.delete(f"/tasks/{task_id}", headers=auth_header(user_token))
        assert response.status_code == 403
        assert response.json()["detail"] == "Access Denied"

    def test_user_can_read_tasks(self, client, admin_token, user_token):
        """GET /tasks sebagai 'user' → 200 OK (read diperbolehkan)."""
        client.post(
            "/tasks", json={"title": "Visible Task"}, headers=auth_header(admin_token)
        )
        response = client.get("/tasks", headers=auth_header(user_token))
        assert response.status_code == 200
        assert len(response.json()) == 1

    def test_unauthenticated_cannot_access_tasks(self, client):
        """Tanpa token → 401 Unauthorized."""
        response = client.get("/tasks")
        assert response.status_code == 401
