# code-smells-project

API de E-commerce em Python/Flask usada como entrada do desafio `refactor-arch` — **refatorada para MVC** pela skill (relatório em [`../reports/audit-project-1.md`](../reports/audit-project-1.md)).

## Como rodar

```bash
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env    # opcional: ajuste SECRET_KEY, ADMIN_TOKEN etc. (exporte as variáveis)
python app.py
```

A aplicação sobe em `http://localhost:5000`. O banco SQLite (`loja.db`) é criado automaticamente no primeiro boot, já com produtos e usuários de exemplo (senhas gravadas com hash).

## Estrutura

```
app.py                      # entry point (create_app + run)
src/
├── app.py                  # composition root: create_app()
├── config/settings.py      # Config via env vars + constantes de domínio
├── database/connection.py  # conexão por request (flask.g), schema e seed
├── models/                 # produto_model, usuario_model, pedido_model (SQL parametrizado)
├── controllers/            # regras de negócio e validação por domínio
├── services/               # notification_service
├── views/                  # Blueprints (rotas HTTP)
└── middlewares/            # error_handler (erros centralizados), auth (X-Admin-Token)
```

## Variáveis de ambiente

Veja [`.env.example`](.env.example). Se `ADMIN_TOKEN` estiver definido, `POST /admin/reset-db` exige o header `X-Admin-Token`.

## Mudanças de contrato (por segurança)

- `POST /admin/query` (execução de SQL arbitrário) foi **removido**.
- `GET /usuarios` e `GET /usuarios/<id>` não retornam mais `senha`.
- `GET /health` não retorna mais `secret_key`, `db_path` e `debug`.
- Respostas de erro passam a ter formato único `{"erro": "...", "sucesso": false}` (inclusive 404/405/500).
- `PUT /pedidos/<id>/status` retorna 404 para pedido inexistente.
