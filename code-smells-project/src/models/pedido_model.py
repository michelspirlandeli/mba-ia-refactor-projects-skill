"""Acesso a dados de pedidos e itens (transações explícitas, sem N+1)."""
from src.database.connection import get_db


class EstoqueInsuficiente(Exception):
    def __init__(self, produto_id):
        super().__init__(produto_id)
        self.produto_id = produto_id


def criar_com_itens(usuario_id, total, itens, status_inicial):
    """Cria pedido + itens e baixa o estoque atomicamente.

    `itens` = [(produto_id, quantidade, preco_unitario), ...]
    A baixa só ocorre se ainda houver estoque (UPDATE condicional); caso contrário, rollback.
    """
    db = get_db()
    with db:  # commit no sucesso, rollback em qualquer exceção
        pedido_id = db.execute(
            "INSERT INTO pedidos (usuario_id, status, total) VALUES (?, ?, ?)",
            (usuario_id, status_inicial, total),
        ).lastrowid
        for produto_id, quantidade, preco_unitario in itens:
            db.execute(
                "INSERT INTO itens_pedido (pedido_id, produto_id, quantidade, preco_unitario) VALUES (?, ?, ?, ?)",
                (pedido_id, produto_id, quantidade, preco_unitario),
            )
            baixa = db.execute(
                "UPDATE produtos SET estoque = estoque - ? WHERE id = ? AND estoque >= ?",
                (quantidade, produto_id, quantidade),
            )
            if baixa.rowcount == 0:
                raise EstoqueInsuficiente(produto_id)
    return pedido_id


def _listar(where="", params=()):
    db = get_db()
    pedidos = db.execute(f"SELECT * FROM pedidos {where}", params).fetchall()
    if not pedidos:
        return []

    ids = [p["id"] for p in pedidos]
    placeholders = ",".join("?" * len(ids))
    itens = db.execute(
        f"""
        SELECT i.pedido_id, i.produto_id, i.quantidade, i.preco_unitario,
               COALESCE(p.nome, 'Desconhecido') AS produto_nome
        FROM itens_pedido i
        LEFT JOIN produtos p ON p.id = i.produto_id
        WHERE i.pedido_id IN ({placeholders})
        ORDER BY i.id
        """,
        ids,
    ).fetchall()

    itens_por_pedido = {}
    for item in itens:
        itens_por_pedido.setdefault(item["pedido_id"], []).append({
            "produto_id": item["produto_id"],
            "produto_nome": item["produto_nome"],
            "quantidade": item["quantidade"],
            "preco_unitario": item["preco_unitario"],
        })

    return [
        {
            "id": p["id"],
            "usuario_id": p["usuario_id"],
            "status": p["status"],
            "total": p["total"],
            "criado_em": p["criado_em"],
            "itens": itens_por_pedido.get(p["id"], []),
        }
        for p in pedidos
    ]


def listar_todos():
    return _listar()


def listar_por_usuario(usuario_id):
    return _listar("WHERE usuario_id = ?", (usuario_id,))


def existe(pedido_id):
    return get_db().execute("SELECT 1 FROM pedidos WHERE id = ?", (pedido_id,)).fetchone() is not None


def atualizar_status(pedido_id, novo_status):
    db = get_db()
    with db:
        db.execute("UPDATE pedidos SET status = ? WHERE id = ?", (novo_status, pedido_id))


def resumo_vendas():
    """Agregados de vendas em uma única query."""
    row = get_db().execute(
        """
        SELECT COUNT(*)                                             AS total_pedidos,
               COALESCE(SUM(total), 0)                              AS faturamento,
               COALESCE(SUM(CASE WHEN status = 'pendente'  THEN 1 ELSE 0 END), 0) AS pendentes,
               COALESCE(SUM(CASE WHEN status = 'aprovado'  THEN 1 ELSE 0 END), 0) AS aprovados,
               COALESCE(SUM(CASE WHEN status = 'cancelado' THEN 1 ELSE 0 END), 0) AS cancelados
        FROM pedidos
        """
    ).fetchone()
    return dict(row)


def contar():
    return get_db().execute("SELECT COUNT(*) FROM pedidos").fetchone()[0]


def limpar_tudo():
    db = get_db()
    with db:
        db.execute("DELETE FROM itens_pedido")
        db.execute("DELETE FROM pedidos")
        db.execute("DELETE FROM produtos")
        db.execute("DELETE FROM usuarios")
