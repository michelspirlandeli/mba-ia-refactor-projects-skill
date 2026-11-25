"""Casos de uso de pedidos."""
import logging

from src.config.settings import STATUS_PEDIDO_INICIAL, STATUS_PEDIDO_VALIDOS
from src.controllers.validators import exigir_inteiro_positivo, exigir_payload
from src.exceptions import NotFoundError, ValidationError
from src.models import pedido_model, produto_model, usuario_model
from src.services import notification_service

logger = logging.getLogger(__name__)


def _validar_itens(itens):
    if not itens or not isinstance(itens, list):
        raise ValidationError("Pedido deve ter pelo menos 1 item")
    normalizados = []
    for item in itens:
        if not isinstance(item, dict):
            raise ValidationError("Item de pedido inválido")
        produto_id = exigir_inteiro_positivo(item.get("produto_id"), "produto_id")
        quantidade = exigir_inteiro_positivo(item.get("quantidade"), "quantidade")
        normalizados.append((produto_id, quantidade))
    return normalizados


def criar(dados):
    exigir_payload(dados)
    usuario_id = dados.get("usuario_id")
    if not usuario_id:
        raise ValidationError("Usuario ID é obrigatório")
    exigir_inteiro_positivo(usuario_id, "usuario_id")
    if not usuario_model.existe(usuario_id):
        raise ValidationError(f"Usuário {usuario_id} não encontrado")
    itens = _validar_itens(dados.get("itens", []))

    # Uma única query para todos os produtos do pedido (antes: 2 queries por item).
    produtos = produto_model.buscar_por_ids([pid for pid, _ in itens])
    total = 0
    linhas = []
    for produto_id, quantidade in itens:
        produto = produtos.get(produto_id)
        if produto is None:
            raise ValidationError(f"Produto {produto_id} não encontrado")
        if produto["estoque"] < quantidade:
            raise ValidationError("Estoque insuficiente para " + produto["nome"])
        total += produto["preco"] * quantidade
        linhas.append((produto_id, quantidade, produto["preco"]))

    try:
        pedido_id = pedido_model.criar_com_itens(usuario_id, total, linhas, STATUS_PEDIDO_INICIAL)
    except pedido_model.EstoqueInsuficiente as exc:
        raise ValidationError("Estoque insuficiente para " + produtos[exc.produto_id]["nome"])

    logger.info("Pedido criado id=%s usuario_id=%s total=%.2f", pedido_id, usuario_id, total)
    notification_service.pedido_criado(pedido_id, usuario_id)
    return {"pedido_id": pedido_id, "total": total}


def listar_todos():
    return pedido_model.listar_todos()


def listar_por_usuario(usuario_id):
    return pedido_model.listar_por_usuario(usuario_id)


def atualizar_status(pedido_id, dados):
    exigir_payload(dados)
    novo_status = dados.get("status", "")
    if novo_status not in STATUS_PEDIDO_VALIDOS:
        raise ValidationError("Status inválido")
    if not pedido_model.existe(pedido_id):
        raise NotFoundError("Pedido não encontrado")

    pedido_model.atualizar_status(pedido_id, novo_status)
    logger.info("Pedido %s alterado para status=%s", pedido_id, novo_status)
    notification_service.status_pedido_alterado(pedido_id, novo_status)
