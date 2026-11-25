================================
ARCHITECTURE AUDIT REPORT
================================
Project: code-smells-project
Stack:   Python 3.12 (local) + Flask 3.1.1 (SQLite via sqlite3, SQL manual)
Files:   28 analyzed | ~962 lines of code
Date:    2026-11-25

> Re-auditoria: o projeto já foi refatorado para MVC (commit `fa71211`). Este relatório cobre
> apenas o que **permanece** no código atual. Os findings de validação foram confirmados
> executando requisições contra um banco descartável (Flask test client).

## Summary
CRITICAL: 1 | HIGH: 2 | MEDIUM: 1 | LOW: 4

## Findings

### #1 [CRITICAL] Endpoint administrativo destrutivo sem autenticação por padrão (AP-03)
File: src/middlewares/auth.py:16-20
File: src/config/settings.py:13-14
File: .env.example:4
Description: `require_admin` é *fail-open*: com `ADMIN_TOKEN` vazio (o default de `Config` e do
`.env.example`) a rota executa normalmente, apenas com `logger.warning`. Confirmado:
`POST /admin/reset-db` sem header → `200 {"mensagem": "Banco de dados resetado"}`, apagando
`produtos`, `usuarios`, `pedidos` e `itens_pedido`.
Impact: Qualquer cliente anônimo apaga todos os dados em qualquer deploy que esqueça de definir
a variável. A proteção depende de uma configuração opcional.
Recommendation: Tornar o middleware *fail-closed*: sem `ADMIN_TOKEN` a rota responde 403 (ou só
fica aberta quando `APP_ENV` for explicitamente de desenvolvimento) (Playbook P-03).

### #2 [HIGH] Credenciais de demonstração em texto claro no seed (AP-02)
File: src/database/connection.py:55-60, 93-96
Description: `USUARIOS_SEED` contém `("Admin", "admin@loja.com", "admin123", "admin")` e mais
duas senhas literais (`"123456"`, `"senha123"`). O seed roda em **qualquer** ambiente sempre que
`produtos` está vazio, criando uma conta `admin` com senha conhecida. A severidade foi reduzida de
CRITICAL porque as senhas são gravadas com hash e o login hoje não concede privilégios.
Impact: Conta administrativa com credencial pública em produção; qualquer autorização futura
baseada em `tipo` herda a brecha.
Recommendation: Rodar o seed de usuários só em desenvolvimento (`APP_ENV`) e ler a senha do admin
de variável de ambiente, sem literal no código (Playbook P-02).

### #3 [HIGH] Integridade de dados não garantida (AP-10)
File: src/database/connection.py:18-39
File: src/controllers/usuario_controller.py:31-43
File: src/controllers/pedido_controller.py:28-30
Description: O schema não tem `UNIQUE(email)`, `FOREIGN KEY` nem `NOT NULL`, e os controllers não
verificam esses casos. Confirmado: dois `POST /usuarios` com `dup@b.co` → `201` e `201`;
`POST /pedidos` com `usuario_id: 9999` (inexistente) → `201`, com baixa de estoque.
Impact: Usuários duplicados por e-mail (o login usa `fetchone()` e pega a primeira linha, de forma
ambígua), pedidos órfãos que consomem estoque real e relatórios de venda distorcidos.
Recommendation: Checar e-mail já cadastrado (400) e existência do usuário (400/404) no controller,
e adicionar índice `UNIQUE` em `usuarios.email` via `CREATE UNIQUE INDEX IF NOT EXISTS` (Playbook P-10).

### #4 [MEDIUM] Validação de tipos incompleta resulta em 500 (AP-12)
File: src/controllers/usuario_controller.py:33-39
File: src/controllers/pedido_controller.py:28-30
File: src/controllers/produto_controller.py:23-24
Description: Os campos são checados por presença, mas não por tipo. Confirmado:
`nome: ["x"]` → 500; `senha: 123` → 500 (`generate_password_hash` com int); `usuario_id: {"a":1}`
→ 500 (binding do sqlite); `descricao: {"x":1}` → 500. Além disso, `estoque: 1.5` é aceito
(`exigir_numero` não exige inteiro) e grava estoque fracionado.
Impact: Erros de entrada do cliente aparecem como erro interno, poluem os logs com stack traces e
deixam dados inválidos no banco.
Recommendation: Usar `exigir_inteiro_positivo` para `usuario_id`, criar `exigir_texto` para
`nome`/`senha`/`descricao` e exigir inteiro ≥ 0 para `estoque` (Playbook P-12).

### #5 [LOW] Responsabilidades fora da camada correta (AP-07)
File: src/controllers/validators.py:2
File: src/controllers/sistema_controller.py:4, 14, 36-37
File: src/models/pedido_model.py:116-122
Description: As exceções de domínio (`ValidationError`, `NotFoundError`...) estão definidas em
`middlewares/error_handler.py`, então controllers e validators importam da camada HTTP.
`sistema_controller` lê `flask.current_app` diretamente. `pedido_model.limpar_tudo()` apaga
**todas** as tabelas, incluindo as de outros domínios. A severidade foi reduzida de HIGH porque o
acoplamento é pequeno e tudo continua testável via `create_app(config_object)`.
Impact: Controllers ficam presos ao Flask e ao módulo de middleware, e o reset do banco fica
num model de domínio que não é dono dessas tabelas.
Recommendation: Mover as exceções para `src/exceptions.py` (o middleware só as mapeia), passar
versão e ambiente como parâmetros ao controller e mover `limpar_tudo` para `database/connection.py`
(Playbook P-07).

### #6 [LOW] Defaults de configuração permissivos (AP-15)
File: src/config/settings.py:17, 20
Description: `HOST` tem default `"0.0.0.0"` (escuta em todas as interfaces) e `CORS_ORIGINS`
tem default `"*"`. Ambos já vêm de variável de ambiente, por isso a severidade foi reduzida de MEDIUM.
Impact: Um deploy sem `.env` fica exposto na rede e aceita qualquer origem.
Recommendation: Usar defaults seguros (`127.0.0.1`, sem CORS amplo) e deixar a abertura como
opt-in via env (Playbook P-02).

### #7 [LOW] Status de pedido como strings literais duplicadas (AP-17)
File: src/models/pedido_model.py:103-105
File: src/services/notification_service.py:12-14
File: src/database/connection.py:23, 29
Description: `'pendente'`, `'aprovado'` e `'cancelado'` aparecem literais no SQL do relatório e no
service de notificação, e `'cliente'`/`'pendente'` como `DEFAULT` do schema, embora
`STATUS_PEDIDO_VALIDOS`, `STATUS_PEDIDO_INICIAL` e `TIPO_USUARIO_PADRAO` existam em `settings.py`.
Impact: Renomear um status exige alterar vários arquivos, com risco de divergência silenciosa.
Recommendation: Definir constantes nomeadas por status em `settings.py` e passá-las como
parâmetro na query de resumo (Playbook P-15).

### #8 [LOW] Logger declarado e não utilizado (AP-20)
File: src/controllers/pedido_controller.py:2, 10
Description: `import logging` e `logger = logging.getLogger(__name__)` são declarados, mas
nenhuma chamada `logger.` existe no arquivo. Criação de pedido e mudança de status não geram log
de auditoria, ao contrário de produtos e usuários.
Impact: Código morto e falta de rastreabilidade nas operações que movimentam estoque.
Recommendation: Registrar `logger.info` na criação e na mudança de status, ou remover o import (Playbook P-15).

## Deprecated APIs
| File:Line | Deprecated | Modern replacement |
|---|---|---|
| — | Nenhuma API deprecated detectada para Python 3.12 / Flask 3.1.1 | — |

## Architecture Overview (current → target)
- Current: MVC adequado: config isolada, models com SQL parametrizado, controllers com as regras,
  Blueprints finos, error handler central e composition root (`create_app`). Restam lacunas
  de segurança por default (admin fail-open, seed), de integridade e de validação de tipos.
- Target:  MVC: config / models / controllers (+services) / views(routes) / middlewares / entry point.
  Será um ajuste pontual, sem reestruturar o projeto.
- Falsos positivos descartados: as f-strings em `pedido_model.py:39` e `produto_model.py:27, 71`
  interpolam apenas placeholders `?` ou cláusulas montadas pelo próprio código, e os valores seguem
  como parâmetros. Não há SQL Injection.
- Observação de contrato (fora do escopo): `GET /usuarios` e `GET /relatorios/vendas` são públicos
  e expõem e-mails e faturamento. Mudar isso quebraria o contrato original e depende de decisão
  de produto.

================================
Total: 8 findings
================================
