"""Smoke test do code-smells-project: exercita todos os endpoints e imprime status + chaves."""
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
        payload = raw.decode()[:80]
    return status, payload

def shape(p):
    if isinstance(p, dict):
        return {k: shape(v) if k in ("dados",) else type(v).__name__ for k, v in sorted(p.items())}
    if isinstance(p, list):
        return [shape(p[0])] if p else []
    return type(p).__name__

cases = [
    ("GET", "/", None),
    ("GET", "/health", None),
    ("GET", "/produtos", None),
    ("GET", "/produtos/1", None),
    ("GET", "/produtos/999", None),
    ("GET", "/produtos/busca?q=mouse&categoria=informatica&preco_min=10&preco_max=500", None),
    ("POST", "/produtos", {"nome": "Livro Clean Code", "descricao": "Livro", "preco": 99.9, "estoque": 5, "categoria": "livros"}),
    ("POST", "/produtos", {"nome": "X"}),
    ("POST", "/produtos", {"nome": "Ab", "preco": 1, "estoque": 1, "categoria": "invalida"}),
    ("PUT", "/produtos/11", {"nome": "Livro Clean Code 2", "preco": 109.9, "estoque": 4, "categoria": "livros"}),
    ("PUT", "/produtos/999", {"nome": "x", "preco": 1, "estoque": 1}),
    ("DELETE", "/produtos/11", None),
    ("DELETE", "/produtos/999", None),
    ("GET", "/usuarios", None),
    ("GET", "/usuarios/1", None),
    ("GET", "/usuarios/999", None),
    ("POST", "/usuarios", {"nome": "Ana", "email": "ana@email.com", "senha": "segredo1"}),
    ("POST", "/usuarios", {"nome": "Ana"}),
    ("POST", "/login", {"email": "ana@email.com", "senha": "segredo1"}),
    ("POST", "/login", {"email": "ana@email.com", "senha": "errada"}),
    ("POST", "/login", {"email": "' OR '1'='1' --", "senha": "x"}),
    ("POST", "/pedidos", {"usuario_id": 2, "itens": [{"produto_id": 1, "quantidade": 1}, {"produto_id": 2, "quantidade": 2}]}),
    ("POST", "/pedidos", {"usuario_id": 2, "itens": [{"produto_id": 999, "quantidade": 1}]}),
    ("POST", "/pedidos", {"usuario_id": 2, "itens": []}),
    ("GET", "/pedidos", None),
    ("GET", "/pedidos/usuario/2", None),
    ("PUT", "/pedidos/1/status", {"status": "aprovado"}),
    ("PUT", "/pedidos/1/status", {"status": "xyz"}),
    ("GET", "/relatorios/vendas", None),
    ("GET", "/rota-inexistente", None),
]

for method, path, body in cases:
    status, payload = call(method, path, body)
    print(f"{status} {method:6} {path[:60]:60} {json.dumps(shape(payload), ensure_ascii=False)[:200]}")
