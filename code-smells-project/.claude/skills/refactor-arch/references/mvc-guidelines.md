# Guidelines de Arquitetura — MVC Alvo (Fase 3)

Para APIs backend, "View" é a **camada de apresentação HTTP**: definição de rotas, parsing do
request e serialização da resposta (JSON). Não há templates HTML.

```
HTTP request
   │
   ▼
[ View / Routes ]  ── valida formato da entrada, chama controller, devolve JSON + status
   │
   ▼
[ Controller ]     ── orquestra o caso de uso; regras de negócio (ou delega a services)
   │
   ▼
[ Model ]          ── entidades + acesso a dados (queries parametrizadas / ORM)
   │
   ▼
[ Database ]

Transversais: config (env vars) · middlewares (erros, logging) · entry point (composition root)
```

## Responsabilidades por camada

| Camada | PODE | NÃO PODE |
|---|---|---|
| **Config** (`config/`) | Ler variáveis de ambiente, definir defaults de dev, constantes de domínio (status válidos, limites) | Conter segredos de produção literais; importar app/rotas |
| **Model** (`models/`) | Definir entidade/schema, CRUD, queries (parametrizadas), mapeamento linha → objeto/dict, `to_dict()` **sem campos sensíveis** | Conhecer `request`/`response`, status HTTP, enviar e-mail, ler env direto |
| **Controller** (`controllers/`) | Implementar o caso de uso: validar regras de negócio, coordenar models e services, transações, lançar erros de domínio (`NotFoundError`, `ValidationError`) | Montar SQL; acessar `request` global (recebe dados já extraídos); formatar resposta HTTP |
| **Service** (`services/`, opcional) | Integrações e regras reutilizáveis (notificação, pagamento, hash de senha, cálculo de relatório) | Conhecer HTTP |
| **View / Routes** (`views/` ou `routes/`) | Registrar rotas, extrair body/params/query, validar **formato** de entrada, chamar controller, serializar resposta + status code | Regra de negócio; acesso a banco; `try/except` genérico em cada handler |
| **Middlewares** (`middlewares/`) | Error handler central (mapeia exceções → JSON + status), logging, auth | Regra de negócio |
| **Entry point** (`app.py` / `app.js` + `server.js`) | Composition root: criar app, carregar config, inicializar banco, injetar dependências, registrar rotas e middlewares, `listen/run` | Definir rotas de negócio inline |

## Regras obrigatórias

1. **Dependência unidirecional**: routes → controllers → (services) → models → db. Nunca o contrário.
2. **Nenhum segredo literal** no código: `os.environ.get("X", <default_dev>)` / `process.env.X ?? <default_dev>`, com `.env.example` documentando as variáveis. Segredos sensíveis (gateway de pagamento) **sem default** de produção.
3. **Queries sempre parametrizadas**.
4. **Erros centralizados**: controllers lançam exceções de domínio; um único handler converte em JSON `{ "erro"|"error": msg }` no formato que o projeto já usava, com o mesmo status code. 500 nunca expõe `str(e)`.
5. **Injeção de dependência**: a conexão/repositório é criada no entry point e passada (ou obtida via `g`/contexto de request no Flask, ou injetada no construtor no Node). Nada de `new Database()` dentro de handler.
6. **Sem estado global mutável** de módulo (exceto objetos de infraestrutura imutáveis como a instância `db = SQLAlchemy()`).
7. **Senhas** com hash forte e salt (`werkzeug.security.generate_password_hash` / `crypto.scrypt` / `bcrypt`), nunca serializadas.
8. **Contrato HTTP preservado** (paths, métodos, campos, status de sucesso).
9. Um arquivo por domínio em cada camada (`produto_model.py`, `pedido_controller.py`, ...).
10. **Debug desligado por padrão**; ativável por env var.

## Estrutura alvo por stack

### Python / Flask (monolito → MVC)
```
<projeto>/
├── app.py                      # entry point: from src.app import create_app; app.run(...)
├── requirements.txt
├── .env.example
└── src/
    ├── __init__.py
    ├── app.py                  # create_app(): composition root
    ├── config/
    │   └── settings.py         # Config a partir de env vars + constantes
    ├── database/
    │   └── connection.py       # get_db() por request (flask.g) + init_db/seed
    ├── models/
    │   └── <dominio>_model.py
    ├── controllers/
    │   └── <dominio>_controller.py
    ├── services/               # opcional
    ├── views/
    │   └── <dominio>_routes.py # Blueprints
    └── middlewares/
        └── error_handler.py    # AppError + register_error_handlers(app)
```

### Python / Flask com SQLAlchemy já em camadas (models/, routes/, services/, utils/)
Mantenha os pacotes existentes e complemente:
```
<projeto>/
├── app.py                      # create_app() + run
├── config.py                   # (ou config/settings.py) env vars
├── database.py                 # db = SQLAlchemy()
├── models/                     # mantidos; sem password no to_dict, hash forte, helpers de domínio (is_overdue)
├── controllers/                # NOVO: regra de negócio extraída das rotas
├── routes/                     # (views) apenas HTTP → controller
├── services/                   # integrações (notificação) com config injetada
├── middlewares/error_handler.py# NOVO
└── utils/                      # validação/helpers reutilizados de verdade
```

### Node.js / Express
```
<projeto>/
├── package.json                # "start": "node src/server.js"
├── .env.example
└── src/
    ├── server.js               # entry point: carrega config, cria app, listen
    ├── app.js                  # composition root: cria db, models, controllers, routers
    ├── config/index.js         # process.env
    ├── database/connection.js  # abre db, schema, seed, helpers promisificados
    ├── models/<dominio>Model.js
    ├── services/<nome>Service.js
    ├── controllers/<dominio>Controller.js
    ├── routes/<dominio>Routes.js   # express.Router (views)
    └── middlewares/errorHandler.js # (err, req, res, next)
```

## Critérios de pronto (Definition of Done da Fase 3)

- [ ] Estrutura de diretórios segue o padrão acima (adaptado à stack)
- [ ] Configuração extraída para módulo de config (sem hardcoded)
- [ ] Models abstraem os dados
- [ ] Views/Routes só fazem roteamento/serialização
- [ ] Controllers concentram o fluxo da aplicação
- [ ] Error handling centralizado
- [ ] Entry point claro (composition root)
- [ ] Aplicação inicia sem erros
- [ ] Endpoints originais respondem com os mesmos status/formatos
