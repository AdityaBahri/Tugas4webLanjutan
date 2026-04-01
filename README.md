# T4 — FastAPI Microservice: JWT Auth + RBAC + Task CRUD

> **Author:** Aditya Hisbul Bahri  
> **Mata Kuliah:** Pemrograman Web Lanjutan 
> **Tugas:** T4 — Pengujian API dengan Pytest

---

## 📋 Deskripsi Proyek

Proyek ini merupakan implementasi **FastAPI Microservice** sederhana dengan fitur:

- 🔐 **Autentikasi JWT** — Register & Login menghasilkan Bearer Token
- 🛡️ **RBAC (Role-Based Access Control)** — Role `admin` dan `user` dengan hak akses berbeda
- 📝 **Task CRUD** — Create, Read, Update, Delete task melalui REST API
- ✅ **Pengujian Pytest** — 3 skenario test lengkap menggunakan `TestClient`

---

## 🗂️ Struktur Proyek

```
T4_pytest/
├── main.py               # Aplikasi FastAPI utama
├── requirements.txt      # Dependensi Python
├── pytest.ini            # Konfigurasi Pytest
├── README.md             # Dokumentasi proyek (ini)
└── tests/
    ├── __init__.py
    └── test_main.py      # Suite pengujian (3 skenario)
```

---

## ⚙️ Instalasi & Menjalankan

### 1. Clone / Salin Proyek

```bash
git clone <url-repo>
cd T4_pytest
```

### 2. Buat Virtual Environment (opsional tapi disarankan)

```bash
python -m venv venv
source venv/bin/activate      # macOS/Linux
venv\Scripts\activate         # Windows
```

### 3. Install Dependensi

```bash
pip install -r requirements.txt
```

### 4. Jalankan Server (opsional, untuk uji manual via Swagger)

```bash
uvicorn main:app --reload
```

Buka browser ke: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)

---

## 🧪 Menjalankan Pengujian

```bash
# Jalankan semua test dengan output verbose
pytest tests/test_main.py -v

# Dengan laporan singkat jika ada error
pytest tests/test_main.py -v --tb=short
```

---

## 📌 Endpoint API

| Method   | Endpoint           | Role       | Keterangan                      |
|----------|--------------------|------------|---------------------------------|
| `POST`   | `/register`        | Public     | Registrasi pengguna baru        |
| `POST`   | `/login`           | Public     | Login & dapatkan JWT token      |
| `GET`    | `/tasks`           | admin/user | Ambil semua task                |
| `GET`    | `/tasks/{id}`      | admin/user | Ambil task berdasarkan ID       |
| `POST`   | `/tasks`           | admin only | Buat task baru                  |
| `PUT`    | `/tasks/{id}`      | admin only | Perbarui task                   |
| `DELETE` | `/tasks/{id}`      | admin only | Hapus task                      |

---

## 🏗️ Skenario Pengujian

### Skenario 1 — Alur Autentikasi (`TestAuthFlow`)
- ✅ Register pengguna baru → 201 Created
- ✅ Register username duplikat → 400 Bad Request
- ✅ Register role tidak valid → 422 Unprocessable Entity
- ✅ Login dengan kredensial benar → 200 OK + JWT token
- ✅ Login password salah → 401 Unauthorized
- ✅ Login username tidak terdaftar → 401 Unauthorized

### Skenario 2 — CRUD Operasional Admin (`TestCRUDAdmin`)
- ✅ Create task sebagai admin → 201 Created
- ✅ Read all tasks → 200 OK + list
- ✅ Read task by ID → 200 OK
- ✅ Read task ID tidak ada → 404 Not Found
- ✅ Update task (full) → 200 OK + data terbaru
- ✅ Update task (partial) → field lain tidak berubah
- ✅ Delete task → 200 OK + task hilang dari list
- ✅ Delete task tidak ada → 404 Not Found

### Skenario 3 — RBAC Access Denied (`TestRBACAccessDenied`)
- ✅ User biasa POST /tasks → 403 Forbidden
- ✅ User biasa PUT /tasks/{id} → 403 Forbidden
- ✅ User biasa DELETE /tasks/{id} → 403 Forbidden
- ✅ User biasa GET /tasks → 200 OK (boleh baca)
- ✅ Tanpa token → 401 Unauthorized

---

## 📦 Dependensi Utama

| Package              | Keterangan                        |
|----------------------|------------------------------------|
| `fastapi`            | Web framework utama                |
| `uvicorn`            | ASGI server                        |
| `python-jose`        | Pembuatan & validasi JWT           |
| `passlib`            | Hashing password (sha256_crypt)    |
| `python-multipart`   | Parsing form data (login)          |
| `httpx`              | HTTP client untuk TestClient       |
| `pytest`             | Framework pengujian                |
| `pytest-asyncio`     | Dukungan async di pytest           |

---

## 📝 Catatan

- Database menggunakan **in-memory dictionary** (tidak persisten), cocok untuk keperluan pengujian.
- Setiap test dijalankan dengan state bersih berkat fixture `reset_db` (autouse).
- Untuk production, ganti `SECRET_KEY` dengan nilai acak yang aman dan gunakan database nyata.

---

*Dibuat oleh **Ahmad Hidayat** — 2024*
