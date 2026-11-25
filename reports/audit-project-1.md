```
================================
PHASE 1: PROJECT ANALYSIS
================================
Language:      Python 3.12 (local)
Framework:     Flask 3.1.1
Dependencies:  flask-cors 5.0.1, sqlite3 (stdlib)
Domain:        E-commerce API (produtos, usuários, pedidos, relatórios de vendas)
Architecture:  Monolítica com camadas nominais ("falso MVC") — 4 arquivos; models.py concentra SQL + regra
               de negócio de 4 domínios; controllers acessam o banco direto; app.py mistura rotas, config e SQL admin
Source files:  4 files analyzed (~780 lines)
DB tables:     produtos, usuarios, pedidos, itens_pedido
Entry point:   app.py (python app.py, porta 5000)
Endpoints:     20 routes mapped
================================
```

================================
ARCHITECTURE AUDIT REPORT
================================
Project: code-smells-project
Stack:   Python + Flask 3.1.1 (SQLite via sqlite3, SQL manual)
Files:   4 analyzed | ~780 lines of code
Date:    2026-11-25

## Summary
CRITICAL: 5 | HIGH: 5 | MEDIUM: 4 | LOW: 4

## Findings

### #1 [CRITICAL] SQL Injection (AP-01)
File: models.py:28, 47-50, 57-61, 68, 92, 109-111, 126-129, 140, 148-151, 155-166, 174, 188, 192, 220, 224, 279-281, 289-297
Description: Todas as queries são montadas por concatenação de strings com dados do request, ex.:
`"SELECT * FROM usuarios WHERE email = '" + email + "' AND senha = '" + senha + "'"` (login) e
`query += " AND (nome LIKE '%" + termo + "%' ..."` (busca). Confirmado em execução: login com
email `' OR '1'='1' --` retorna 200 autenticado como Admin.
Impact: Bypass de autenticação, leitura/alteração/remoção de qualquer tabela por qualquer cliente.
Recommendation: Placeholders `?` com tupla de parâmetros em todas as queries; busca com cláusulas dinâmicas parametrizadas (Playbook P-01).

### #2 [CRITICAL] Hardcoded Credentials (AP-02)
File: app.py:7
File: controllers.py:289
Description: `SECRET_KEY` hardcoded como `'minha-chave-super-secreta-123'` no código-fonte e repetido literalmente no health check.
Impact: Qualquer pessoa com acesso ao repositório pode forjar sessões/assinaturas; segredo não pode ser rotacionado sem deploy.
Recommendation: Ler `SECRET_KEY` de variável de ambiente em `config/settings.py`, com `.env.example` (Playbook P-02).

### #3 [CRITICAL] Endpoints administrativos sem autenticação com execução arbitrária de SQL (AP-03)
File: app.py:47-57, 59-78
Description: `POST /admin/query` executa qualquer SQL recebido no campo `sql` (`cursor.execute(query)`) e `POST /admin/reset-db` apaga todas as tabelas — ambos sem qualquer autenticação.
Impact: Comprometimento total do banco (exfiltração, destruição de dados) por um único request anônimo.
Recommendation: Remover `/admin/query`; proteger `/admin/reset-db` com token administrativo vindo de config e desabilitado por padrão (Playbook P-03).

### #4 [CRITICAL] God File / Fake MVC (AP-04)
File: models.py:1-314
File: app.py:1-88
Description: `models.py` contém, para 4 domínios (produtos, usuários, pedidos, relatórios), queries SQL, regras de negócio (cálculo de total, baixa de estoque, faixas de desconto), validação de estoque e formatação de resposta. `app.py` mistura config, registro de rotas, handlers com SQL inline e bootstrap do servidor.
Impact: Impossível testar em isolamento; qualquer mudança em um domínio afeta os demais; alto risco de regressão.
Recommendation: Separar em `config/`, `models/` (um por domínio), `controllers/`, `views/` (Blueprints), `middlewares/` e um `create_app()` como composition root (Playbook P-04, P-07).

### #5 [CRITICAL] Exposição de dados sensíveis nas respostas (AP-05)
File: models.py:83, 99
File: controllers.py:285-289
Description: `GET /usuarios` e `GET /usuarios/<id>` devolvem o campo `senha` (em texto puro). `GET /health` devolve `secret_key`, `db_path`, `debug: true` e `ambiente: "producao"`.
Impact: Vazamento de credenciais de todos os usuários e do segredo da aplicação para qualquer cliente anônimo.
Recommendation: Serializar usuários sem `senha`; health check retorna apenas status e contagens (Playbook P-05).

### #6 [HIGH] Senhas armazenadas e comparadas em texto puro (AP-09)
File: models.py:105-131
File: database.py:75-79
Description: `criar_usuario` grava a senha recebida sem hash; `login_usuario` compara a senha no `WHERE` da query; o seed grava `admin123`, `123456`, `senha123` em claro.
Impact: Qualquer vazamento do banco (ou o #1/#5) expõe imediatamente as senhas reais dos usuários.
Recommendation: `werkzeug.security.generate_password_hash`/`check_password_hash`; login busca por email e verifica o hash em código; seed com hashes (Playbook P-09).

### #7 [HIGH] Estado global mutável — conexão singleton compartilhada (AP-08)
File: database.py:4-11
Description: `db_connection` é uma variável global mutada via `global db_connection` e aberta com `check_same_thread=False`, compartilhada por todas as threads/requests do servidor.
Impact: Condições de corrida entre requests, transações de um request misturadas às de outro, conexão nunca fechada; impossível injetar um banco de teste.
Recommendation: Conexão por request em `flask.g` com `teardown_appcontext`, caminho do banco vindo da config (Playbook P-08).

### #8 [HIGH] Acoplamento forte sem injeção de dependência (AP-07)
File: controllers.py:3, 264-277
File: app.py:4, 49-55, 66-69
Description: Controllers e handlers de `app.py` importam `get_db` e executam SQL diretamente (`cursor.execute("SELECT COUNT(*) FROM produtos")` no health check; `DELETE FROM ...` em `reset_database`), pulando a camada de model.
Impact: Regras de acesso a dados espalhadas; trocar o banco ou testar controllers exige o SQLite real.
Recommendation: Toda query no model; controllers dependem apenas de models; composition root em `create_app()` (Playbook P-07).

### #9 [HIGH] Regra de negócio e side effects na camada errada (AP-06 / AP-16)
File: models.py:256-262
File: controllers.py:208-210, 247-250
Description: Política comercial de desconto (faixas 10%/5%/2%) está no model de acesso a dados; envio de email/SMS/push e notificações de status são `print` inline no controller HTTP.
Impact: Regra de negócio não reutilizável nem testável isoladamente; notificações acopladas ao request.
Recommendation: Mover cálculo de desconto para o controller de relatórios com faixas em config; extrair `NotificationService` (Playbook P-06).

### #10 [HIGH] Ausência de transação / integridade no fluxo de pedido (AP-10)
File: models.py:133-169
Description: `criar_pedido` valida o estoque em um laço, depois insere pedido, itens e baixa estoque em outro laço, sem transação explícita nem rollback; se algo falhar no meio, o estado parcial permanece na conexão global e é commitado pelo próximo request. A verificação de estoque e a baixa não são atômicas.
Impact: Pedidos sem itens, estoque negativo e inconsistências sob concorrência.
Recommendation: Executar inserts e baixa de estoque dentro de `with db:` (commit/rollback automático) (Playbook P-10).

### #11 [MEDIUM] Queries N+1 (AP-11)
File: models.py:171-201, 203-233, 154-156, 239-254
Description: Para cada pedido é feita uma query de itens e, para cada item, uma query de produto (`cursor2`/`cursor3` dentro de laços aninhados). `criar_pedido` re-consulta o preço de cada produto já lido. O relatório faz 5 queries separadas onde um `GROUP BY` resolve.
Impact: 1 + N + N×M queries por listagem; degrada linearmente com o volume de pedidos.
Recommendation: Uma query com `LEFT JOIN produtos` + `WHERE pedido_id IN (...)` e agrupamento em memória; agregação com `SUM(CASE ...)` (Playbook P-11).

### #12 [MEDIUM] Validação de entrada ausente/duplicada (AP-12)
File: controllers.py:24-62, 64-96, 167-170, 237-240
Description: Validação de produto copiada entre `criar_produto` e `atualizar_produto` (e a de update é mais fraca: não valida nome/categoria). `login` e `atualizar_status_pedido` chamam `dados.get(...)` sem checar `None` (body ausente → 500). Não há checagem de tipo (`preco: "abc"` → `TypeError` → 500), nem formato de email.
Impact: Erros 500 para entradas inválidas; regras inconsistentes entre create/update.
Recommendation: Validador único por entidade, `request.get_json(silent=True)` e erros 400 via `ValidationError` (Playbook P-12).

### #13 [MEDIUM] Error handling inconsistente e vazando detalhes internos (AP-13)
File: controllers.py:10-12, 21-22, 60-62, 95-96, 108-109, 125-126, 133-134, 143-144, 164-165, 185-186, 218-220, 226-227, 234-235, 254-255, 261-262, 291-292
Description: Todos os 18 handlers repetem `except Exception as e: return jsonify({"erro": str(e)}), 500`; não existe error handler global; 404 de rota inexistente retorna HTML.
Impact: Mensagens internas (SQL, stack) expostas ao cliente; duplicação; formato de erro inconsistente.
Recommendation: `middlewares/error_handler.py` com `AppError`/`NotFoundError` e handler genérico que não expõe `str(e)` (Playbook P-13).

### #14 [MEDIUM] Configuração acoplada ao código (AP-15)
File: app.py:8, 9, 88
File: database.py:5
Description: `DEBUG = True` fixo, `app.run(host="0.0.0.0", port=5000, debug=True)` (debugger Werkzeug exposto na rede), CORS aberto sem configuração, caminho do banco `loja.db` literal.
Impact: Debugger interativo (execução remota de código) acessível em qualquer interface; impossível configurar por ambiente.
Recommendation: `Config` lendo `FLASK_DEBUG`, `HOST`, `PORT`, `DATABASE_PATH`, `CORS_ORIGINS` do ambiente (Playbook P-02).

### #15 [LOW] Magic numbers e strings (AP-17)
File: controllers.py:47, 49, 52, 242, 285-286
File: models.py:257-262
Description: Limites `2`/`200` de nome, lista de categorias, lista de status, faixas `10000/5000/1000` e taxas `0.1/0.05/0.02`, versão `"1.0.0"` e `"producao"` literais.
Impact: Regras de negócio escondidas e duplicadas; alteração exige caçar literais.
Recommendation: Constantes nomeadas em `config/settings.py` (Playbook P-15).

### #16 [LOW] Logging com print e dados pessoais em log (AP-19)
File: controllers.py:8, 11, 57, 61, 106, 161, 179, 182, 208-210, 219, 248, 250
File: app.py:56, 83-86
Description: `print` usado como log, incluindo emails de login (`"Login falhou: " + email`).
Impact: Sem nível/estrutura de log; PII em stdout.
Recommendation: `logging` com logger por módulo, sem PII (Playbook P-16).

### #17 [LOW] Código morto e duplicação de serialização (AP-20)
File: models.py:2, 12-21, 31-40, 79-86, 95-102, 304-313, 171-201, 203-233
File: database.py:2
Description: Imports não usados (`sqlite3` em models.py, `os` em database.py); o mapeamento linha→dict de produto é copiado 3 vezes, o de usuário 2 vezes; `get_pedidos_usuario` e `get_todos_pedidos` são cópias quase idênticas.
Impact: Manutenção multiplicada; divergência entre cópias.
Recommendation: Funções `_row_to_produto`/`_row_to_usuario` únicas e um `_listar_pedidos(where, params)` (Playbook P-15).

### #18 [LOW] Nomes que sombreiam builtins (AP-18)
File: controllers.py:14, 56, 64, 98, 160
File: models.py:24, 54, 65, 89
Description: Parâmetros e variáveis chamados `id`, sombreando o builtin `id()`.
Impact: Legibilidade e risco de bugs sutis.
Recommendation: Renomear para `produto_id`, `usuario_id` (Playbook P-15).

## Deprecated APIs
| File:Line | Deprecated | Modern replacement |
|---|---|---|
| — | Nenhuma API deprecated detectada para Python 3.12 + Flask 3.1.1 (o código usa apenas `sqlite3`, `jsonify`, `add_url_rule`, todos suportados) | — |

## Architecture Overview (current → target)
- Current: monolito com camadas nominais — models.py faz tudo, controllers acessam o banco, app.py mistura rotas/config/SQL.
- Target:  MVC — src/config / src/database / src/models / src/controllers (+services) / src/views / src/middlewares / create_app()

================================
Total: 18 findings
================================

Phase 2 complete. Proceed with refactoring (Phase 3)? [y/n]
