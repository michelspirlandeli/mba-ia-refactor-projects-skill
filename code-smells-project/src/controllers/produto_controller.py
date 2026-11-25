"""Casos de uso de produtos."""
import logging

from src.config.settings import CATEGORIA_PADRAO, CATEGORIAS_VALIDAS, NOME_PRODUTO_MAX, NOME_PRODUTO_MIN
from src.controllers.validators import exigir_inteiro, exigir_numero, exigir_payload, numero_opcional, texto_opcional
from src.exceptions import NotFoundError, ValidationError
from src.models import produto_model

logger = logging.getLogger(__name__)


def _validar_produto(dados):
    """Validação única para criação e atualização (antes duplicada)."""
    exigir_payload(dados)
    for campo, rotulo in (("nome", "Nome"), ("preco", "Preço"), ("estoque", "Estoque")):
        if campo not in dados:
            raise ValidationError(f"{rotulo} é obrigatório")

    nome = dados["nome"]
    if not isinstance(nome, str):
        raise ValidationError("Nome inválido")
    preco = exigir_numero(dados["preco"], "Preço")
    estoque = exigir_inteiro(dados["estoque"], "Estoque")
    descricao = texto_opcional(dados.get("descricao"), "Descrição")
    categoria = dados.get("categoria", CATEGORIA_PADRAO)

    if preco < 0:
        raise ValidationError("Preço não pode ser negativo")
    if estoque < 0:
        raise ValidationError("Estoque não pode ser negativo")
    if len(nome) < NOME_PRODUTO_MIN:
        raise ValidationError("Nome muito curto")
    if len(nome) > NOME_PRODUTO_MAX:
        raise ValidationError("Nome muito longo")
    if categoria not in CATEGORIAS_VALIDAS:
        raise ValidationError("Categoria inválida. Válidas: " + str(list(CATEGORIAS_VALIDAS)))

    return {"nome": nome, "descricao": descricao, "preco": preco, "estoque": estoque, "categoria": categoria}


def listar():
    produtos = produto_model.listar()
    logger.debug("Listando %d produtos", len(produtos))
    return produtos


def obter(produto_id):
    produto = produto_model.buscar_por_id(produto_id)
    if not produto:
        raise NotFoundError("Produto não encontrado")
    return produto


def criar(dados):
    produto = _validar_produto(dados)
    produto_id = produto_model.criar(**produto)
    logger.info("Produto criado id=%s", produto_id)
    return produto_id


def atualizar(produto_id, dados):
    obter(produto_id)
    produto = _validar_produto(dados)
    produto_model.atualizar(produto_id, **produto)


def deletar(produto_id):
    obter(produto_id)
    produto_model.deletar(produto_id)
    logger.info("Produto deletado id=%s", produto_id)


def buscar(termo, categoria, preco_min, preco_max):
    return produto_model.buscar(
        termo=termo,
        categoria=categoria,
        preco_min=numero_opcional(preco_min, "preco_min"),
        preco_max=numero_opcional(preco_max, "preco_max"),
    )
