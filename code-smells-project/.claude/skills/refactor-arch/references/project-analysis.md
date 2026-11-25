# Análise de Projeto — Heurísticas de Detecção (Fase 1)

Objetivo: identificar linguagem, framework, banco de dados, domínio e arquitetura atual
**a partir de evidências no código**, nunca por suposição.

## 1. Detecção de linguagem

| Evidência (arquivo/extensão) | Linguagem |
|---|---|
| `requirements.txt`, `pyproject.toml`, `setup.py`, `Pipfile`, `*.py` | Python |
| `package.json`, `*.js`, `*.mjs`, `*.cjs` | JavaScript (Node.js) |
| `tsconfig.json`, `*.ts` | TypeScript |
| `pom.xml`, `build.gradle`, `*.java` | Java |
| `go.mod`, `*.go` | Go |
| `composer.json`, `*.php` | PHP |
| `Gemfile`, `*.rb` | Ruby |
| `*.csproj`, `*.cs` | C# |

Versão: `.python-version`, `runtime.txt`, `engines` no `package.json`, `.nvmrc`. Se não houver,
informe a versão do runtime local (`python --version`, `node --version`) indicando "(local)".

## 2. Detecção de framework (e versão)

| Sinal no manifesto | Sinal no código | Framework |
|---|---|---|
| `flask==X` | `Flask(__name__)`, `@app.route`, `Blueprint` | Flask |
| `fastapi` | `FastAPI()`, `@app.get` | FastAPI |
| `django` | `settings.py`, `urls.py`, `manage.py` | Django |
| `"express": "^X"` | `require('express')`, `app.get(`, `express.Router()` | Express |
| `"@nestjs/core"` | `@Controller()`, `@Module()` | NestJS |
| `"fastify"` | `fastify()` | Fastify |
| `spring-boot-starter-web` | `@RestController` | Spring Boot |

Use a versão **declarada** no manifesto (ex.: `flask==3.1.1`, `express ^4.18.2`). Se o lockfile
existir, ele indica a versão resolvida.

## 3. Detecção de banco de dados / camada de persistência

| Sinal | Banco / acesso |
|---|---|
| `import sqlite3`, `sqlite3.connect(` | SQLite via driver cru (SQL manual) |
| `require('sqlite3')`, `new sqlite3.Database(` | SQLite via driver cru (callbacks) |
| `':memory:'` | Banco em memória (dados somem no restart) |
| `flask_sqlalchemy`, `db.Model`, `db.Column` | ORM SQLAlchemy |
| `SQLALCHEMY_DATABASE_URI` | URI de conexão (ver se está hardcoded) |
| `mongoose`, `pymongo` | MongoDB |
| `pg`, `psycopg2`, `mysql2`, `prisma`, `sequelize`, `typeorm` | Relacionais via driver/ORM |

Tabelas/entidades: procure `CREATE TABLE <nome>`, `__tablename__ = '<nome>'`, `class X(db.Model)`,
`mongoose.model('X')`. Liste todas.

## 4. Mapeamento de rotas (contrato HTTP)

| Stack | Padrões a procurar |
|---|---|
| Flask | `@app.route(`, `@<bp>.route(`, `app.add_url_rule(`, `methods=[...]`, `register_blueprint` |
| Express | `app.get/post/put/delete/patch(`, `router.<verb>(`, `app.use('<prefix>', router)` |
| FastAPI | `@app.<verb>(`, `APIRouter` |

Para cada rota registre: método, path, handler (`arquivo:linha`) e status de sucesso.
**Atenção a conflitos de ordem**: ex. `/tasks/<int:id>` vs `/tasks/search` — a ordem e os
conversores de tipo influenciam o roteamento e precisam ser preservados.

## 5. Identificação do domínio

Inferir pelo vocabulário de tabelas, rotas e seeds:
- `produtos`, `pedidos`, `itens_pedido`, `carrinho` → **E-commerce**
- `courses`, `enrollments`, `payments`, `checkout` → **LMS / plataforma de cursos com checkout**
- `tasks`, `categories`, `due_date`, `priority` → **Task Manager**

Descreva em uma linha: "<Domínio> (<entidades principais>)".

## 6. Classificação da arquitetura atual

| Estilo | Sinais |
|---|---|
| **Monolito "big ball of mud"** | Poucos arquivos; rotas, SQL, regra de negócio e config no mesmo arquivo/classe; nomes genéricos (`AppManager`, `utils`, `helpers`, `models.py` com tudo) |
| **Camadas nominais (falso MVC)** | Arquivos chamados `controllers.py`/`models.py` existem, mas controllers acessam o banco direto ou models contêm regra de negócio/formatação de todos os domínios |
| **Parcialmente em camadas** | Pastas `models/`, `routes/`, `services/`, `utils/` existem, mas as rotas concentram validação, regra de negócio e queries; services pouco usados; config no entry point |
| **MVC / camadas adequado** | Config isolada, models só com dados, controllers/services com regra, rotas finas, error handler central, composição no entry point |

Conte **acoplamentos cruzados**: quem importa o banco diretamente? Quantos arquivos fazem
query? Existe estado global (`global`, `let x = {}` em módulo exportado)?

## 7. Como iniciar a aplicação (para a validação da Fase 3)

| Stack | Instalação | Start | Porta padrão |
|---|---|---|---|
| Python/Flask | `python -m venv .venv` + `pip install -r requirements.txt` | `python app.py` (ver `if __name__ == "__main__"`) | 5000 |
| Node/Express | `npm install` | `npm start` (ver `scripts.start`) | ver `listen(` |

Verifique se há **seed** obrigatório (`seed.py`, scripts de seed, inserts no boot) e se o banco
é arquivo ou memória. Leia o README do projeto — ele costuma dizer como rodar.

## 8. Checklist da Fase 1

- [ ] Linguagem e versão
- [ ] Framework e versão
- [ ] Dependências relevantes
- [ ] Domínio descrito
- [ ] Arquitetura atual classificada (tabela da seção 6)
- [ ] Nº de arquivos-fonte e linhas (sem `node_modules`, venvs, lockfiles)
- [ ] Tabelas/entidades
- [ ] Entry point + comando de start + porta
- [ ] Lista completa de endpoints (contrato HTTP)
