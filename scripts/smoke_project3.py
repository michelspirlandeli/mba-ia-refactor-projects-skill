"""Smoke test do task-manager-api: exercita todos os endpoints e imprime status + formato."""
import json, sys, urllib.request

BASE = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:5000"

def call(method, path, body=None):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(BASE + path, data=data, method=method,
                                 headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req) as r:
            status, raw = r.status, r.read()
    except urllib.error.HTTPError as e:
        status, raw = e.code, e.read()
    try:
        payload = json.loads(raw)
    except Exception:
        payload = raw.decode()[:60]
    return status, payload

def shape(p, depth=0):
    if isinstance(p, dict):
        return {k: (shape(v, depth + 1) if isinstance(v, (dict, list)) and depth < 1 else type(v).__name__)
                for k, v in sorted(p.items())}
    if isinstance(p, list):
        return [shape(p[0], depth)] if p else []
    return type(p).__name__

cases = [
    ("GET", "/", None),
    ("GET", "/health", None),
    ("GET", "/tasks", None),
    ("GET", "/tasks/1", None),
    ("GET", "/tasks/999", None),
    ("GET", "/tasks/search?q=login&status=in_progress", None),
    ("GET", "/tasks/stats", None),
    ("POST", "/tasks", {"title": "Nova task", "priority": 2, "user_id": 1, "category_id": 1, "due_date": "2030-01-01", "tags": ["a", "b"]}),
    ("POST", "/tasks", {"title": "ab"}),
    ("POST", "/tasks", {"title": "Task X", "priority": 9}),
    ("POST", "/tasks", {"title": "Task X", "user_id": 999}),
    ("PUT", "/tasks/11", {"status": "done", "priority": 1}),
    ("PUT", "/tasks/11", {"status": "xyz"}),
    ("PUT", "/tasks/999", {"status": "done"}),
    ("DELETE", "/tasks/11", None),
    ("DELETE", "/tasks/999", None),
    ("GET", "/users", None),
    ("GET", "/users/1", None),
    ("GET", "/users/999", None),
    ("POST", "/users", {"name": "Ana", "email": "ana@email.com", "password": "segredo1"}),
    ("POST", "/users", {"name": "Ana", "email": "ana@email.com", "password": "segredo1"}),
    ("POST", "/users", {"name": "Ana", "email": "invalido", "password": "segredo1"}),
    ("PUT", "/users/4", {"name": "Ana Maria", "role": "manager"}),
    ("GET", "/users/1/tasks", None),
    ("POST", "/login", {"email": "joao@email.com", "password": "1234"}),
    ("POST", "/login", {"email": "joao@email.com", "password": "errada"}),
    ("DELETE", "/users/4", None),
    ("GET", "/reports/summary", None),
    ("GET", "/reports/user/1", None),
    ("GET", "/reports/user/999", None),
    ("GET", "/categories", None),
    ("POST", "/categories", {"name": "QA", "color": "#123456"}),
    ("PUT", "/categories/5", {"name": "Quality"}),
    ("DELETE", "/categories/5", None),
    ("DELETE", "/categories/999", None),
    ("GET", "/rota-inexistente", None),
]

for method, path, body in cases:
    status, payload = call(method, path, body)
    print(f"{status} {method:6} {path[:45]:45} {json.dumps(shape(payload), ensure_ascii=False)[:260]}")
