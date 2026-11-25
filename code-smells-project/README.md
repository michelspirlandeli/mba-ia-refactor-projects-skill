# code-smells-project

API de E-commerce em Python/Flask usada como entrada do desafio `refactor-arch`. Foi **refatorada para MVC** pela skill. Relatórios: [`../reports/audit-project-1.md`](../reports/audit-project-1.md) (auditoria original) e [`../reports/reaudit-project-1.md`](../reports/reaudit-project-1.md) (re-auditoria do código refatorado, cujos findings foram corrigidos).

## Como rodar

```bash
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env    # opcional: ajuste SECRET_KEY, ADMIN_TOKEN etc. (exporte as variáveis)
python app.py
```

A aplicação sobe em `http://127.0.0.1:5000`. O banco SQLite (`loja.db`) é criado no primeiro boot.

Com `APP_ENV` de desenvolvimento, que é o padrão, o primeiro boot também cria produtos e usuários de exemplo:
- As senhas desses usuários vêm de `SEED_ADMIN_PASSWORD` e `SEED_DEMO_PASSWORD`.
- Se essas variáveis não estiverem definidas, as senhas são geradas e exibidas uma vez no log do boot.

## Estrutura

```
app.py                      # entry point (create_app + run)
src/
├── app.py                  # composition root: create_app()
├── exceptions.py           # erros de domínio (camada neutra)
├── config/settings.py      # Config via env vars + constantes de domínio
├── database/connection.py  # conexão por request (flask.g), schema, índice único, seed de dev, reset
├── models/                 # produto_model, usuario_model, pedido_model (SQL parametrizado)
├── controllers/            # regras de negócio e validação por domínio (sem dependência de Flask)
├── services/               # notification_service
├── views/                  # Blueprints (rotas HTTP)
└── middlewares/            # error_handler (erros centralizados), auth (X-Admin-Token)
```

## Variáveis de ambiente

Veja [`.env.example`](.env.example). As rotas `/admin/*` só funcionam quando `ADMIN_TOKEN` está definido. Elas exigem o header `X-Admin-Token`. Sem o token configurado, respondem 403 (fail-closed).

## Mudanças de contrato (por segurança e integridade)

- `POST /admin/query` (execução de SQL arbitrário) foi **removido**.
- `POST /admin/reset-db` exige `ADMIN_TOKEN` configurado e o header `X-Admin-Token`. Sem eles, responde 403.
- `GET /usuarios` e `GET /usuarios/<id>` não retornam mais `senha`.
- `GET /health` não retorna mais `secret_key`, `db_path` e `debug`.
- Email de usuário é único: `POST /usuarios` com email já cadastrado retorna 409.
- `POST /pedidos` para `usuario_id` inexistente retorna 400 (antes criava o pedido e baixava o estoque).
- Tipos inválidos retornam 400 em vez de 500. Exemplos: `nome` como lista, `senha` numérica, `descricao` como objeto, `estoque` fracionado.
- Respostas de erro passam a ter formato único `{"erro": "...", "sucesso": false}` (inclusive 404/405/500).
- `PUT /pedidos/<id>/status` retorna 404 para pedido inexistente.
- Os dados de exemplo só são criados em desenvolvimento e não têm mais senhas fixas no código.
- Defaults seguros:
  - `HOST` passa a ser `127.0.0.1`.
  - CORS fica desabilitado até `CORS_ORIGINS` ser definido.
