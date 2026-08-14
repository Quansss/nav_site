#!/usr/bin/env python3
import urllib.request, json, sys

BASE = "http://127.0.0.1:8765"

def api(path, method="GET", data=None, token=None):
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    body = json.dumps(data).encode() if data else None
    req = urllib.request.Request(f"{BASE}{path}", data=body, headers=headers, method=method)
    with urllib.request.urlopen(req, timeout=5) as r:
        return json.loads(r.read())

print("=== 测试 1: 公开链接列表 ===")
links = api("/api/links")
print(f"  返回 {len(links)} 条链接:", [l['title'] for l in links])

print("\n=== 测试 2: 管理员登录 ===")
token_data = api("/api/auth/login", "POST", {"username": "admin", "password": "admin123"})
token = token_data["access_token"]
user = token_data["user"]
print(f"  登录成功: {user['username']} ({user['role']})")
print(f"  Token: {token[:16]}...")

print("\n=== 测试 3: 获取所有链接（含管理员可见）===")
all_links = api("/api/links", token=token)
print(f"  共 {len(all_links)} 条:", [l['title'] for l in all_links])

print("\n=== 测试 4: 发布新链接 ===")
new_link = api("/api/links", "POST", {
    "title": "测试链接",
    "url": "https://example.com",
    "description": "这是一个测试",
    "category": "测试",
    "visibility": "user"
}, token=token)
print(f"  创建成功: ID={new_link['id']}, title={new_link['title']}")

print("\n=== 测试 5: 删除测试链接 ===")
api(f"/api/links/{new_link['id']}", "DELETE", token=token)
print("  删除成功")

print("\n=== 测试 6: 获取用户列表 ===")
users = api("/api/admin/users", token=token)
print(f"  用户列表: {users}")

print("\n=== All tests passed ===")
