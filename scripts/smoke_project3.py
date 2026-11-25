"""Smoke test do task-manager-api: exercita todos os endpoints e imprime status + formato.

Uso:
  python scripts/smoke_project3.py [BASE_URL] [--auth] [--security]
  --auth      a API roda com AUTH_REQUIRED=true: faz login como admin e envia o token
  --security  casos extras de autorização / validação / rate limit (requer --auth)
Senha dos usuários do seed: variável SEED_PASSWORD (padrão "1234").
"""
import json
import os
import sys
import urllib.request

args = [a for a in sys.argv[1:] if not a.startswith("--")]
BASE = args[0] if args else "http://127.0.0.1:5000"
AUTH = "--auth" in sys.argv
SECURITY = "--security" in sys.argv
PW = os.environ.get("SEED_PASSWORD", "1234")


def call(method, path, body=None, token=None):
    data = json.dumps(body).encode() if body is not None else None
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(BASE + path, data=data, method=method, headers=headers)
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


def login(email):
    return call("POST", "/login", {"email": email, "password": PW})[1]["token"]


def shape(p, depth=0):
    if isinstance(p, dict):
        return {k: (shape(v, depth + 1) if isinstance(v, (dict, list)) and depth < 1 else type(v).__name__)
                for k, v in sorted(p.items())}
    if isinstance(p, list):
        return [shape(p[0], depth)] if p else []
    return type(p).__name__


def run(cases, token=None):
    for method, path, body in cases:
        status, payload = call(method, path, body, token)
        print(f"{status} {method:6} {path[:45]:45} {json.dumps(shape(payload), ensure_ascii=False)[:260]}")


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
    ("POST", "/login", {"email": "joao@email.com", "password": PW}),
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

admin_token = login("joao@email.com") if AUTH else None
run(cases, admin_token)

if SECURITY:
    maria = login("maria@email.com")  # role "user", id 2
    print("--- autorização (maria, role user)")
    run([
        ("GET", "/tasks", None),                                     # 200 leitura liberada
        ("PUT", "/users/1", {"password": "hacked123"}),              # 403 alterar outro usuário
        ("DELETE", "/users/1", None),                                # 403 só admin
        ("PUT", "/users/2", {"role": "admin"}),                      # 403 auto-promoção
        ("PUT", "/users/2", {"name": "Maria S."}),                   # 200 alterar a si mesma
        ("GET", "/reports/summary", None),                           # 403 só admin/manager
        ("GET", "/reports/user/1", None),                            # 403 relatório de outro
        ("GET", "/reports/user/2", None),                            # 200 próprio relatório
        ("PUT", "/tasks/1", {"status": "done"}),                     # 403 task do joao
        ("PUT", "/tasks/2", {"status": "done"}),                     # 200 task própria
        ("POST", "/tasks", {"title": "Para o joao", "user_id": 1}),  # 403 atribuir a outro
        ("POST", "/categories", {"name": "Hack"}),                   # 403 só admin/manager
    ], maria)
    print("--- sem token / validação / cadastro público")
    run([
        ("GET", "/tasks", None),                                                          # 401
        ("POST", "/users", {"name": "Eve", "email": "eve@email.com", "password": "segredo1", "role": "admin"}),  # 403
        ("POST", "/users", {"name": "Eve", "email": "eve@email.com", "password": "123"}),  # 400 senha curta
    ])
    run([
        ("POST", "/tasks", {"title": "Task tags", "tags": {"a": 1}}),                     # 400
        ("POST", "/tasks", {"title": "Task desc", "description": {"a": 1}}),              # 400
        ("POST", "/categories", {"name": ["x"]}),                                          # 400
        ("GET", "/tasks/search?q=%25", None),                                              # 200 [] (% literal)
        ("GET", "/tasks?page=1&per_page=3", None),                                         # 200 paginado
    ], admin_token)
    print("--- rate limit de login (6 falhas seguidas)")
    for _ in range(6):
        status, _payload = call("POST", "/login", {"email": "pedro@email.com", "password": "errada"})
        print(status, end=" ")
    print()
