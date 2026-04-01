"""
main.py — FastAPI Microservice: JWT Auth, RBAC, dan Task CRUD
=============================================================
Author     :  Ahmad Hidayat
Teknologi  :  FastAPI, python-jose (JWT), passlib (sha256_crypt), python-multipart
Database   :  In-memory dictionary (simulasi, tanpa database persisten)
"""

from datetime import datetime, timedelta, timezone
from typing import Optional, List
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import BaseModel

# ---------------------------------------------------------------------------
# Konfigurasi JWT
# ---------------------------------------------------------------------------
SECRET_KEY = "kunci_rahasia_ahmad_hidayat_2024"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60

# ---------------------------------------------------------------------------
# Inisialisasi Aplikasi
# ---------------------------------------------------------------------------
app = FastAPI(
    title="Task Manager API",
    description="FastAPI Microservice — JWT Auth + RBAC + Task CRUD | by Ahmad Hidayat",
    version="1.0.0",
)

pwd_context = CryptContext(schemes=["sha256_crypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/login")

# ---------------------------------------------------------------------------
# Mock Database (in-memory)
# ---------------------------------------------------------------------------
# Format: { "username": {"username": str, "hashed_password": str, "role": str} }
users_store: dict = {}
fake_users_db = users_store  # alias untuk kompatibilitas test

# Format: { id: {"id": int, "title": str, "description": str, "owner": str} }
tasks_store: dict = {}
fake_tasks_db = tasks_store  # alias untuk kompatibilitas test
task_id_counter: int = 1  # penanda ID otomatis naik


# ---------------------------------------------------------------------------
# Pydantic Schemas
# ---------------------------------------------------------------------------
class UserRegister(BaseModel):
    username: str
    password: str
    role: str = "user"  # default role adalah 'user'


class Token(BaseModel):
    access_token: str
    token_type: str


class TokenData(BaseModel):
    username: Optional[str] = None
    role: Optional[str] = None


class TaskCreate(BaseModel):
    title: str
    description: str = ""


class TaskUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None


class TaskOut(BaseModel):
    id: int
    title: str
    description: str
    owner: str


# ---------------------------------------------------------------------------
# Helper Functions
# ---------------------------------------------------------------------------
def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (expires_delta or timedelta(minutes=15))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


async def get_current_user(token: str = Depends(oauth2_scheme)) -> dict:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        role: str = payload.get("role")
        if username is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    user = fake_users_db.get(username)
    if user is None:
        raise credentials_exception
    return user


def require_admin(current_user: dict = Depends(get_current_user)) -> dict:
    """Dependency guard: hanya role 'admin' yang diperbolehkan mengakses."""
    if current_user.get("role") != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access Denied",
        )
    return current_user


# ---------------------------------------------------------------------------
# AUTH Endpoints
# ---------------------------------------------------------------------------
@app.post("/register", status_code=status.HTTP_201_CREATED, tags=["Auth"])
def register(user: UserRegister):
    """Registrasi pengguna baru."""
    if user.username in fake_users_db:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already registered",
        )
    if user.role not in ("admin", "user"):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Role must be 'admin' or 'user'",
        )
    fake_users_db[user.username] = {
        "username": user.username,
        "hashed_password": hash_password(user.password),
        "role": user.role,
    }
    return {"message": "User registered successfully", "username": user.username, "role": user.role}


@app.post("/login", response_model=Token, tags=["Auth"])
def login(form_data: OAuth2PasswordRequestForm = Depends()):
    """Login dan dapatkan JWT access token."""
    user = fake_users_db.get(form_data.username)
    if not user or not verify_password(form_data.password, user["hashed_password"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    token = create_access_token(
        data={"sub": user["username"], "role": user["role"]},
        expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES),
    )
    return {"access_token": token, "token_type": "bearer"}


# ---------------------------------------------------------------------------
# TASK CRUD Endpoints
# ---------------------------------------------------------------------------
@app.get("/tasks", response_model=List[TaskOut], tags=["Tasks"])
def get_tasks(current_user: dict = Depends(get_current_user)):
    """Ambil seluruh daftar task. Dapat diakses admin maupun user biasa."""
    return list(tasks_store.values())


@app.get("/tasks/{task_id}", response_model=TaskOut, tags=["Tasks"])
def get_task(task_id: int, current_user: dict = Depends(get_current_user)):
    """Ambil satu task berdasarkan ID. Dapat diakses admin maupun user biasa."""
    task = tasks_store.get(task_id)
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")
    return task


@app.post("/tasks", response_model=TaskOut, status_code=status.HTTP_201_CREATED, tags=["Tasks"])
def create_task(task: TaskCreate, current_user: dict = Depends(require_admin)):
    """Tambahkan task baru. Hanya admin yang dapat mengakses endpoint ini."""
    global task_id_counter
    new_id = task_id_counter
    new_task = {
        "id": new_id,
        "title": task.title,
        "description": task.description,
        "owner": current_user["username"],
    }
    tasks_store[new_id] = new_task
    task_id_counter += 1
    return new_task


@app.put("/tasks/{task_id}", response_model=TaskOut, tags=["Tasks"])
def update_task(task_id: int, task: TaskUpdate, current_user: dict = Depends(require_admin)):
    """Perbarui data task. Hanya admin yang dapat mengakses endpoint ini."""
    record = tasks_store.get(task_id)
    if not record:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")
    if task.title is not None:
        record["title"] = task.title
    if task.description is not None:
        record["description"] = task.description
    tasks_store[task_id] = record
    return record


@app.delete("/tasks/{task_id}", tags=["Tasks"])
def delete_task(task_id: int, current_user: dict = Depends(require_admin)):
    """Hapus task dari sistem. Hanya admin yang dapat mengakses endpoint ini."""
    if task_id not in tasks_store:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")
    del tasks_store[task_id]
    return {"message": f"Task {task_id} berhasil dihapus"}
