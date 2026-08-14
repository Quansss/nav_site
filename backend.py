"""
导航站后端 - FastAPI + SQLite + JWT
"""
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime, timedelta
import sqlite3, hashlib, secrets, hmac, base64, json, os
from contextlib import contextmanager

DATABASE = os.environ.get("NAV_DB_PATH", "nav.db")

# ── DB ──────────────────────────────────────────────────────────────────────
def init_db():
    with get_db() as db:
        db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                role TEXT NOT NULL DEFAULT 'user',
                status TEXT NOT NULL DEFAULT 'approved',
                created_at TEXT NOT NULL
            )
        """)
        db.execute("""
            CREATE TABLE IF NOT EXISTS links (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                url TEXT NOT NULL,
                description TEXT DEFAULT '',
                category TEXT DEFAULT '',
                favicon TEXT DEFAULT '',
                visibility TEXT NOT NULL DEFAULT 'user',
                created_by INTEGER,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                FOREIGN KEY (created_by) REFERENCES users(id)
            )
        """)
        db.execute("CREATE INDEX IF NOT EXISTS idx_links_visibility ON links(visibility)")
        # 兼容旧库：补充 username/password 列
        cols = {r[1] for r in db.execute("PRAGMA table_info(links)").fetchall()}
        if "username" not in cols:
            db.execute("ALTER TABLE links ADD COLUMN username TEXT DEFAULT ''")
        if "password" not in cols:
            db.execute("ALTER TABLE links ADD COLUMN password TEXT DEFAULT ''")
        if "sort_order" not in cols:
            db.execute("ALTER TABLE links ADD COLUMN sort_order INTEGER DEFAULT 0")

        cur = db.execute("SELECT id FROM users WHERE email='971954959@qq.com'")
        if not cur.fetchone():
            h = hashlib.sha256("admin123".encode()).hexdigest()
            db.execute(
                "INSERT INTO users (email,password_hash,role,status,created_at) VALUES (?,?,?,?,?)",
                ("971954959@qq.com", h, "admin", "approved", datetime.now().isoformat())
            )
            print("[OK] admin created")

        cur = db.execute("SELECT id FROM links LIMIT 1")
        if not cur.fetchone():
            db.execute("""
                INSERT INTO links (title,url,description,category,favicon,visibility,created_by,created_at,updated_at) VALUES
                ('百度','https://www.baidu.com','中文搜索引擎','搜索','','guest',1,datetime('now'),datetime('now')),
                ('Google','https://www.google.com','全球搜索','搜索','','guest',1,datetime('now'),datetime('now')),
                ('GitHub','https://github.com','代码托管平台','开发','','user',1,datetime('now'),datetime('now')),
                ('知乎','https://www.zhihu.com','问答社区','社区','','user',1,datetime('now'),datetime('now')),
                ('内网管理','http://192.168.1.1','路由器管理后台','工具','','admin',1,datetime('now'),datetime('now'))
            """)
            print("[OK] sample links inserted")

@contextmanager
def get_db():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.commit()
        conn.close()

# ── Auth ─────────────────────────────────────────────────────────────────────
# 无状态签名 token（HMAC），重启后依然有效
SECRET_KEY = os.environ.get("NAV_SECRET", "nav-site-secret-change-me").encode()

def _b64e(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()

def _b64d(s: str) -> bytes:
    pad = "=" * (-len(s) % 4)
    return base64.urlsafe_b64decode(s + pad)

def create_token(user_row) -> str:
    header = _b64e(json.dumps({"alg": "HS256", "typ": "JWT"}).encode())
    payload = _b64e(json.dumps({
        "user_id": user_row["id"],
        "email": user_row["email"],
        "role": user_row["role"],
        "exp": (datetime.now() + timedelta(hours=24 * 7)).timestamp()
    }).encode())
    sig = _b64e(hmac.new(SECRET_KEY, f"{header}.{payload}".encode(), hashlib.sha256).digest())
    return f"{header}.{payload}.{sig}"

def verify_token(token: str) -> Optional[dict]:
    try:
        header, payload, sig = token.split(".")
        expect = _b64e(hmac.new(SECRET_KEY, f"{header}.{payload}".encode(), hashlib.sha256).digest())
        if not hmac.compare_digest(sig, expect):
            return None
        data = json.loads(_b64d(payload))
        if datetime.now().timestamp() > data.get("exp", 0):
            return None
        return data
    except Exception:
        return None

def get_user_from_request(request: Request) -> Optional[dict]:
    auth = request.headers.get("Authorization", "")
    if not auth:
        return None
    return verify_token(auth.replace("Bearer ", ""))

def require_user(request: Request) -> dict:
    user = get_user_from_request(request)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return user

def require_role(request: Request, roles: tuple):
    user = require_user(request)
    if user["role"] not in roles:
        raise HTTPException(status_code=403, detail="Forbidden")
    return user

# ── Pydantic ────────────────────────────────────────────────────────────────
class LoginReq(BaseModel):
    email: str
    password: str

class RegisterReq(BaseModel):
    email: str
    password: str

class LinkCreate(BaseModel):
    title: str
    url: str
    description: str = ""
    category: str = ""
    favicon: str = ""
    visibility: str = "user"
    username: str = ""
    password: str = ""
    sort_order: int = 0

class LinkUpdate(BaseModel):
    title: Optional[str] = None
    url: Optional[str] = None
    description: Optional[str] = None
    category: Optional[str] = None
    favicon: Optional[str] = None
    visibility: Optional[str] = None
    username: Optional[str] = None
    password: Optional[str] = None
    sort_order: Optional[int] = None

class RoleUpdate(BaseModel):
    role: str

# ── App ─────────────────────────────────────────────────────────────────────
app = FastAPI(title="Nav Site")
app.add_middleware(
    CORSMiddleware, allow_origins=["*"], allow_credentials=True,
    allow_methods=["*"], allow_headers=["*"],
)
init_db()

# ── Helpers ─────────────────────────────────────────────────────────────────
def link_to_out(row, can_edit: bool = False, viewer_uid: int = None, viewer_role: str = None) -> dict:
    # 凭据可见性：管理员 / 创建者本人 才能看到明文密码
    show_creds = viewer_role == "admin" or (viewer_uid and row["created_by"] == viewer_uid)
    return {
        "id": row["id"], "title": row["title"], "url": row["url"],
        "description": row["description"] or "",
        "category": row["category"] or "",
        "favicon": row["favicon"] or "",
        "visibility": row["visibility"],
        "created_by": row["created_by"],
        "created_at": row["created_at"],
        "sort_order": row["sort_order"] if "sort_order" in row.keys() else 0,
        "can_edit": can_edit,
        "username": (row["username"] or "") if show_creds else "",
        "password": (row["password"] or "") if show_creds else "",
        "has_credentials": bool(((row["username"] or "") or (row["password"] or ""))) and show_creds,
    }

def allowed_vis(role: str) -> tuple:
    if role == "admin":
        return ("guest", "user", "admin")
    elif role == "user":
        return ("guest", "user")
    return ("guest",)

def vis_filter(allowed: tuple) -> str:
    return " OR ".join([f"visibility='{v}'" for v in allowed])

@app.get("/api/debug-headers")
def debug_headers(request: Request):
    return dict(request.headers)

# ── Auth Routes ─────────────────────────────────────────────────────────────
@app.post("/api/auth/login")
def login(req: LoginReq):
    with get_db() as db:
        row = db.execute(
            "SELECT * FROM users WHERE email=?", (req.email,)
        ).fetchone()
    pw_hash = hashlib.sha256(req.password.encode()).hexdigest()
    if not row or row["password_hash"] != pw_hash:
        raise HTTPException(status_code=401, detail="邮箱或密码错误")
    if row["status"] != "approved":
        status_msg = {"pending": "账号待审核，请等待管理员批准", "rejected": "账号已被拒绝"}.get(row["status"], "账号状态异常")
        raise HTTPException(status_code=403, detail=status_msg)
    token = create_token(row)
    return {
        "access_token": token,
        "token_type": "bearer",
        "user": {
            "id": row["id"], "email": row["email"],
            "role": row["role"], "status": row["status"], "created_at": row["created_at"]
        }
    }

@app.post("/api/auth/register")
def register(req: RegisterReq):
    """注册新用户（邮箱），默认待审核状态。"""
    email = (req.email or '').strip().lower()
    pwd = req.password or ''
    # 基础校验
    if not email or '@' not in email or '.' not in email.split('@')[-1]:
        raise HTTPException(status_code=400, detail="请输入有效的邮箱地址")
    if len(pwd) < 6:
        raise HTTPException(status_code=400, detail="密码至少 6 位")
    pw_hash = hashlib.sha256(pwd.encode()).hexdigest()
    now = datetime.now().isoformat()
    with get_db() as db:
        existing = db.execute("SELECT id,status FROM users WHERE email=?", (email,)).fetchone()
        if existing:
            # 已存在：pending 提示等待，approved/rejected 提示已注册
            if existing["status"] == "pending":
                raise HTTPException(status_code=202, detail="该邮箱已提交注册，等待管理员审核")
            raise HTTPException(status_code=409, detail="该邮箱已被注册")
        cur = db.execute(
            "INSERT INTO users (email,password_hash,role,status,created_at) VALUES (?,?,?,?,?)",
            (email, pw_hash, "user", "pending", now)
        )
        row = db.execute("SELECT * FROM users WHERE id=?", (cur.lastrowid,)).fetchone()
    # 不发 token，返回提示
    return {
        "registered": True,
        "message": "注册申请已提交，请等待管理员审核",
        "user": {
            "id": row["id"], "email": row["email"],
            "role": row["role"], "status": row["status"], "created_at": row["created_at"]
        }
    }

@app.get("/api/auth/me")
def me(request: Request):
    user = get_user_from_request(request)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return {"id": user["user_id"], "email": user["email"],
            "role": user["role"], "created_at": ""}

@app.post("/api/auth/logout")
def logout(request: Request):
    # 无状态 token：客户端删除即可，这里仅做兼容
    return {"ok": True}

# ── Link Routes ────────────────────────────────────────────────────────────
@app.get("/api/links")
def list_links(request: Request, q: str = "", category: str = ""):
    user = get_user_from_request(request)
    role = user["role"] if user else "guest"
    uid = user["user_id"] if user else None
    allowed = allowed_vis(role)
    vf = vis_filter(allowed)

    sql = f"SELECT * FROM links WHERE ({vf})"
    params = []
    if q:
        sql += " AND (title LIKE ? OR description LIKE ? OR url LIKE ?)"
        p = f"%{q}%"
        params.extend([p, p, p])
    if category:
        sql += " AND category = ?"
        params.append(category)
    sql += " ORDER BY sort_order ASC, id DESC"

    with get_db() as db:
        rows = db.execute(sql, params).fetchall()
    return [
        link_to_out(
            r,
            can_edit=(role == "admin" or (uid and r["created_by"] == uid)),
            viewer_uid=uid,
            viewer_role=role,
        )
        for r in rows
    ]

@app.get("/api/links/categories")
def list_categories(request: Request):
    user = get_user_from_request(request)
    role = user["role"] if user else "guest"
    allowed = allowed_vis(role)
    vf = vis_filter(allowed)
    with get_db() as db:
        rows = db.execute(
            f"SELECT DISTINCT category FROM links WHERE ({vf}) AND category != '' ORDER BY category"
        ).fetchall()
    return [r["category"] for r in rows]

@app.post("/api/links")
def create_link(request: Request, data: LinkCreate):
    user = require_role(request, ("admin",))
    now = datetime.now().isoformat()
    with get_db() as db:
        cur = db.execute(
            "INSERT INTO links (title,url,description,category,favicon,visibility,created_by,created_at,updated_at,username,password,sort_order) "
            "VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
            (data.title, data.url, data.description, data.category,
             data.favicon, data.visibility, user["user_id"], now, now,
             data.username, data.password, data.sort_order)
        )
        row = db.execute("SELECT * FROM links WHERE id=?", (cur.lastrowid,)).fetchone()
    return link_to_out(row, can_edit=True, viewer_uid=user["user_id"], viewer_role=user["role"])

class ReorderReq(BaseModel):
    ids: List[int]


@app.put("/api/links/reorder")
def reorder_links(request: Request, data: ReorderReq):
    """管理员批量设置链接排序：ids 顺序即展示顺序，sort_order 取数组下标*10"""
    user = require_role(request, ("admin",))
    with get_db() as db:
        for i, lid in enumerate(data.ids):
            db.execute("UPDATE links SET sort_order=? WHERE id=?", (i * 10, lid))
    return {"ok": True}

# ── Admin Routes ────────────────────────────────────────────────────────────

@app.put("/api/links/{lid}")
def update_link(lid: int, request: Request, data: LinkUpdate):
    user = require_role(request, ("admin",))
    with get_db() as db:
        row = db.execute("SELECT * FROM links WHERE id=?", (lid,)).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Not found")
    if user["role"] != "admin" and row["created_by"] != user["user_id"]:
        raise HTTPException(status_code=403, detail="Forbidden")
    updates = {k: v for k, v in data.model_dump().items() if v is not None}
    if not updates:
        return link_to_out(row, viewer_uid=user["user_id"], viewer_role=user["role"])
    updates["updated_at"] = datetime.now().isoformat()
    set_clause = ", ".join([f"{k}=?" for k in updates])
    vals = list(updates.values()) + [lid]
    with get_db() as db:
        db.execute(f"UPDATE links SET {set_clause} WHERE id=?", vals)
        row = db.execute("SELECT * FROM links WHERE id=?", (lid,)).fetchone()
    return link_to_out(row, can_edit=True, viewer_uid=user["user_id"], viewer_role=user["role"])

@app.delete("/api/links/{lid}")
def delete_link(lid: int, request: Request):
    user = require_role(request, ("admin",))
    with get_db() as db:
        row = db.execute("SELECT * FROM links WHERE id=?", (lid,)).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Not found")
    if user["role"] != "admin" and row["created_by"] != user["user_id"]:
        raise HTTPException(status_code=403, detail="Forbidden")
    with get_db() as db:
        db.execute("DELETE FROM links WHERE id=?", (lid,))
    return {"ok": True}


@app.get("/api/admin/users")
def admin_users(request: Request):
    require_role(request, ("admin",))
    with get_db() as db:
        rows = db.execute("SELECT id, email, role, status, created_at FROM users ORDER BY id").fetchall()
    return [dict(r) for r in rows]

@app.put("/api/admin/users/{uid}/role")
def update_role(uid: int, request: Request, data: RoleUpdate):
    require_role(request, ("admin",))
    if data.role not in ("admin", "user"):
        raise HTTPException(status_code=400, detail="Invalid role")
    with get_db() as db:
        db.execute("UPDATE users SET role=? WHERE id=?", (data.role, uid))
    return {"ok": True}

@app.post("/api/admin/users")
def create_user(email: str, password: str, role: str = "user", request: Request = None):
    require_role(request, ("admin",))
    if role not in ("admin", "user"):
        raise HTTPException(status_code=400, detail="Invalid role")
    try:
        with get_db() as db:
            db.execute(
                "INSERT INTO users (email,password_hash,role,status,created_at) VALUES (?,?,?,?,?)",
                (email, hashlib.sha256(password.encode()).hexdigest(),
                 role, "approved", datetime.now().isoformat())
            )
        return {"ok": True}
    except sqlite3.IntegrityError:
        raise HTTPException(status_code=400, detail="邮箱已存在")

@app.delete("/api/admin/users/{uid}")
def delete_user(uid: int, request: Request):
    require_role(request, ("admin",))
    with get_db() as db:
        db.execute("DELETE FROM users WHERE id=?", (uid,))
    return {"ok": True}

class ChangePwReq(BaseModel):
    old_password: Optional[str] = None
    new_password: str

@app.post("/api/me/password")
def change_my_password(request: Request, data: ChangePwReq):
    """已登录用户修改自己的密码（需提供旧密码）。"""
    user = require_user(request)
    uid = user["user_id"]
    if not data.old_password:
        raise HTTPException(status_code=400, detail="请提供旧密码")
    if len(data.new_password) < 6:
        raise HTTPException(status_code=400, detail="新密码至少 6 位")
    with get_db() as db:
        row = db.execute("SELECT * FROM users WHERE id=?", (uid,)).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="用户不存在")
        if row["password_hash"] != hashlib.sha256(data.old_password.encode()).hexdigest():
            raise HTTPException(status_code=401, detail="旧密码错误")
        db.execute(
            "UPDATE users SET password_hash=? WHERE id=?",
            (hashlib.sha256(data.new_password.encode()).hexdigest(), uid)
        )
    return {"ok": True}

class AdminResetPwReq(BaseModel):
    new_password: str

@app.post("/api/admin/users/{uid}/reset-password")
def admin_reset_password(uid: int, request: Request, data: AdminResetPwReq):
    """管理员重置任意用户密码（无需旧密码）。"""
    require_role(request, ("admin",))
    if len(data.new_password) < 6:
        raise HTTPException(status_code=400, detail="新密码至少 6 位")
    with get_db() as db:
        row = db.execute("SELECT id FROM users WHERE id=?", (uid,)).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="用户不存在")
        db.execute(
            "UPDATE users SET password_hash=? WHERE id=?",
            (hashlib.sha256(data.new_password.encode()).hexdigest(), uid)
        )
    return {"ok": True}

@app.get("/api/admin/pending-users")
def list_pending_users(request: Request):
    """管理员查看待审核用户列表。"""
    require_role(request, ("admin",))
    with get_db() as db:
        rows = db.execute(
            "SELECT id, email, role, status, created_at FROM users WHERE status='pending' ORDER BY created_at DESC"
        ).fetchall()
    return [dict(r) for r in rows]

class ApproveReq(BaseModel):
    action: str  # 'approve' or 'reject'

@app.post("/api/admin/users/{uid}/approve")
def approve_user(uid: int, request: Request, data: ApproveReq):
    """管理员审核用户：通过或拒绝。"""
    require_role(request, ("admin",))
    if data.action not in ("approve", "reject"):
        raise HTTPException(status_code=400, detail="action 必须是 approve 或 reject")
    new_status = "approved" if data.action == "approve" else "rejected"
    with get_db() as db:
        row = db.execute("SELECT * FROM users WHERE id=?", (uid,)).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="用户不存在")
        if row["status"] != "pending":
            raise HTTPException(status_code=400, detail=f"用户当前状态为 {row['status']}，无法审核")
        db.execute("UPDATE users SET status=? WHERE id=?", (new_status, uid))
    return {"ok": True, "new_status": new_status}

# ── Static ─────────────────────────────────────────────────────────────────
@app.get("/")
def root():
    return FileResponse("static/index.html")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend:app", host="0.0.0.0", port=8766, reload=True)
