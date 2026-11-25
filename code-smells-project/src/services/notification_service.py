"""Notificações (email/SMS/push). Hoje apenas registra em log; ponto único para integrar um provedor real."""
import logging

from src.config.settings import STATUS_APROVADO, STATUS_CANCELADO

logger = logging.getLogger(__name__)


def pedido_criado(pedido_id, usuario_id):
    logger.info("Notificação [email/sms/push]: pedido %s criado para usuário %s", pedido_id, usuario_id)


def status_pedido_alterado(pedido_id, novo_status):
    if novo_status == STATUS_APROVADO:
        logger.info("Notificação: pedido %s aprovado — preparar envio", pedido_id)
    elif novo_status == STATUS_CANCELADO:
        logger.info("Notificação: pedido %s cancelado — devolver estoque", pedido_id)
