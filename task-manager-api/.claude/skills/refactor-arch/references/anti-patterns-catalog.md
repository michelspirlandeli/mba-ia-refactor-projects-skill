# Catálogo de Anti-Patterns (Fase 2)

Cada entrada tem: **ID**, severidade padrão, descrição, **sinais de detecção** (objetivos,
greppáveis sempre que possível), exceções e o padrão do playbook que corrige.

## Escala de severidade

| Severidade | Critério |
|---|---|
| **CRITICAL** | Falha grave de segurança ou arquitetura: expõe dados sensíveis (credenciais hardcoded, SQL Injection, execução arbitrária), ou viola completamente a separação de responsabilidades (God Class com banco + regra + roteamento). |
| **HIGH** | Forte violação de MVC/SOLID que dificulta manutenção e testes: regra de negócio em controller/rota, acoplamento forte sem DI, estado global mutável, criptografia fraca. |
| **MEDIUM** | Padronização, duplicação, performance moderada: N+1, validação ausente, middleware inadequado, error handling inconsistente, APIs deprecated. |
| **LOW** | Legibilidade: nomes ruins, magic numbers, imports não usados, `print` como log, código morto. |

Ajuste a severidade **para cima** se o contexto agravar (ex.: segredo de produção `pk_live_`)
e **para baixo** se mitigar (ex.: rota só acessível em dev). Justifique na descrição.

---

## CRITICAL

### AP-01 — SQL Injection (SQL montado por concatenação/interpolação)
- **Sinais**:
  - Python: `execute("..." + var)`, `execute(f"...{var}...")`, `execute("..." % var)`, `query += " AND x = '" + v + "'"`
  - JS: `` db.run(`... ${var} ...`) ``, `"SELECT ... " + req.body.x`
  - Regex: `execute\(\s*f?["'].*(\+|\{|%)` · `(run|get|all|query)\(\s*` + "`" + `.*\$\{`
- **Não é finding**: uso de placeholders `?`, `%s`, `:name` com parâmetros separados; ORM (`filter_by`, `.like(f'%{q}%')` do SQLAlchemy é parametrizado).
- **Playbook**: P-01.

### AP-02 — Credenciais / segredos hardcoded
- **Sinais**: literais atribuídos a `SECRET_KEY`, `password`, `pass`, `dbPass`, `api_key`, `*Key`, `token`, `smtp*`, `email_password`; prefixos `pk_live_`, `sk_live_`, `AKIA`; URIs com usuário:senha; senhas em seeds com texto em claro em produção.
- Regex: `(?i)(secret|passw|pass|pwd|api_?key|token|gateway).{0,20}[:=]\s*["'][^"']{3,}["']`
- **Agravante**: segredo devolvido em resposta HTTP (ex.: health check com `secret_key`) ou impresso em log.
- **Playbook**: P-02.

### AP-03 — Execução arbitrária / endpoint administrativo sem autenticação
- **Sinais**: rota que recebe SQL/código do cliente (`dados.get("sql")` → `execute(query)`), `eval(`, `exec(`, `child_process.exec(req...`; rotas `/admin/*` destrutivas (reset/delete em massa, relatórios financeiros) sem qualquer verificação de auth.
- **Playbook**: P-03.

### AP-04 — God Class / God File
- **Sinais**: um arquivo/classe que concentra **3 ou mais** de: criação de schema/conexão, SQL, regra de negócio, roteamento HTTP, formatação de resposta, config — para **mais de um domínio**. Classes com nomes genéricos (`AppManager`, `Manager`, `Helper`) com > ~100 linhas; um `models.py` com funções de todos os domínios (> ~250 linhas).
- **Playbook**: P-04.

### AP-05 — Exposição de dados sensíveis na resposta
- **Sinais**: serialização de `senha`/`password`/`pass`/`hash` (`to_dict()` incluindo `password`; `SELECT *` de usuários devolvido cru); retornar `secret_key`, `debug`, `db_path` em endpoints públicos; logar número de cartão / dados de pagamento (`console.log(... cc ...)`).
- **Playbook**: P-05.

## HIGH

### AP-06 — Regra de negócio na camada de rota/controller ("Fat Controller")
- **Sinais**: handlers HTTP com cálculo de totais, descontos, faixas de preço, decisão de status de pagamento, orquestração de várias escritas, envio de notificações; > ~40 linhas por handler; callbacks aninhados (> 3 níveis = "callback hell") misturando HTTP e persistência.
- **Playbook**: P-06.

### AP-07 — Acoplamento forte / ausência de Injeção de Dependência
- **Sinais**: controllers/rotas importam o driver ou a conexão global (`from database import get_db` em controller; `this.db` usado dentro de rotas); `new Service()` instanciado dentro do handler; impossível substituir o banco em teste.
- **Playbook**: P-07.

### AP-08 — Estado global mutável
- **Sinais**: `global x` em Python; variáveis de módulo mutáveis exportadas (`let globalCache = {}`, `let totalRevenue = 0`, `module.exports = { cache }`); conexão singleton mutável compartilhada entre threads (`check_same_thread=False`); listas acumuladoras em instância de serviço usadas como "banco" (`self.notifications = []`).
- **Playbook**: P-08.

### AP-09 — Hash de senha fraco / armazenamento em texto puro / auth falsa
- **Sinais**: senha gravada sem hash; `hashlib.md5(`, `sha1(`; "hash" caseiro (`Buffer.from(pwd).toString('base64')` em loop); comparação `senha = '<input>'` no SQL; token fake (`'fake-jwt-token-' + id`); senha default quando ausente (`p || "123456"`).
- **Playbook**: P-09.

### AP-10 — Integridade de dados / transações ausentes
- **Sinais**: várias escritas relacionadas sem transação (pedido + itens + baixa de estoque; matrícula + pagamento); delete de pai deixando filhos órfãos (comentário "ficaram sujos"); erros de callback ignorados (`(err) => { res.send(...) }` sem checar `err`).
- **Playbook**: P-10.

## MEDIUM

### AP-11 — Queries N+1
- **Sinais**: query dentro de `for`/`forEach` sobre resultado de outra query (`for row in rows: cursor.execute(...)`, `for t in tasks: User.query.get(t.user_id)`, `courses.forEach(c => db.all(...))`, `len(u.tasks)` com lazy-load em loop, `.count()` por item em loop); múltiplos `COUNT(*)` separados que caberiam em um `GROUP BY`.
- **Playbook**: P-11.

### AP-12 — Validação de entrada ausente ou duplicada
- **Sinais**: `request.get_json()` usado sem checar `None` (`dados.get` em `None` → 500); validação de tipo ausente (`priority < 1` com string → TypeError); a **mesma** validação copiada em create/update/handlers (listas de status/roles repetidas); helper de validação existente mas não usado.
- **Playbook**: P-12.

### AP-13 — Error handling inconsistente / engolindo exceções
- **Sinais**: `except:` nu; `except Exception as e: return jsonify({"erro": str(e)}), 500` repetido em todo handler (vaza detalhes internos); ausência de error handler global (`@app.errorhandler`, middleware `(err, req, res, next)`); respostas de erro em formatos diferentes (texto puro vs JSON).
- **Playbook**: P-13.

### AP-14 — Uso de APIs deprecated / obsoletas
Verifique a versão da stack detectada na Fase 1.

| Stack | API deprecated | Equivalente moderno |
|---|---|---|
| Python ≥ 3.12 | `datetime.utcnow()` / `datetime.utcfromtimestamp()` | `datetime.now(timezone.utc)` |
| SQLAlchemy ≥ 2.0 / Flask-SQLAlchemy ≥ 3 | `Model.query.get(id)` (LegacyAPIWarning) | `db.session.get(Model, id)` |
| SQLAlchemy ≥ 2.0 | `Model.query.filter(...).all()` (API "1.x legacy") | `db.session.execute(db.select(Model).where(...)).scalars()` (recomendado; `.query` ainda funciona) |
| Flask ≥ 2.3 | `app.before_first_request`, `flask.json.JSONEncoder`, `FLASK_ENV` | lógica no factory / `app.json` provider / `FLASK_DEBUG` |
| Node.js | `new Buffer(x)` | `Buffer.from(x)` |
| Node.js | `url.parse()`, `querystring` | `new URL()`, `URLSearchParams` |
| Express 4 | `body-parser` separado, `req.param()`, `res.send(status, body)` | `express.json()`, `req.params/req.query`, `res.status(s).send(b)` |
| Node sqlite3 | API de callbacks aninhados | wrapper com `util.promisify` / `async/await` |
| JS | `var` | `const` / `let` |
| Python | `type(x) == list` | `isinstance(x, list)` |

- **Sinais**: grep pelas APIs da coluna esquerda. Liste **cada** ocorrência (arquivo:linha).
- **Playbook**: P-14.

### AP-15 — Configuração acoplada ao código / ambiente
- **Sinais**: `debug=True` / `DEBUG = True` fixo; porta/host/URI do banco literais; `app.run(host="0.0.0.0", debug=True)`; CORS liberado globalmente sem config; `':memory:'` fixo.
- **Playbook**: P-02.

### AP-16 — Efeitos colaterais/side effects síncronos no fluxo da requisição
- **Sinais**: envio de e-mail/SMS/push simulado com `print` dentro do controller; `smtplib.SMTP(...)` chamado inline; laço de 10.000 iterações para "hash" bloqueando o event loop.
- **Playbook**: P-06 / P-09.

## LOW

### AP-17 — Magic numbers / strings
- **Sinais**: limiares e taxas soltos (`> 10000`, `* 0.1`, `len(password) < 4`, `priority <= 2`), listas literais de status/categorias/roles repetidas, porta `3000`/`5000`, cores `'#000000'`, prefixo de cartão `"4"`.
- **Playbook**: P-15.

### AP-18 — Nomes ruins / pouco descritivos
- **Sinais**: variáveis de 1–3 letras fora de loops curtos (`u`, `e`, `p`, `cid`, `cc`, `d`), campos de API abreviados (`usr`, `eml`, `pwd`), nomes enganosos (`badCrypto`, `AppManager`, `logAndCache` que faz duas coisas).
- **Observação**: nomes de campos do **contrato HTTP** não devem ser renomeados — apenas as variáveis internas.
- **Playbook**: P-15.

### AP-19 — Logging com `print`/`console.log` e dados pessoais em log
- **Sinais**: `print(` / `console.log(` como mecanismo de log em controllers; log de e-mail de login, cartão, etc.
- **Playbook**: P-16.

### AP-20 — Código morto / imports não utilizados / duplicação trivial
- **Sinais**: `import os, sys, json` sem uso; funções/métodos nunca chamados (`validate_status` no model enquanto a rota valida na mão); variáveis exportadas não usadas (`totalRevenue`); serialização manual duplicando `to_dict()`.
- **Playbook**: P-15.

---

## Procedimento de varredura recomendado

1. Rode os greps objetivos (AP-01, 02, 05, 08, 09, 11, 13, 14, 17, 19, 20) em todos os fontes.
2. Leia cada handler/rota para os estruturais (AP-03, 04, 06, 07, 10, 12, 16).
3. Deduplicate: mesmo AP + mesmo arquivo → um finding com várias linhas.
4. Um mesmo trecho pode gerar findings distintos se violar APs diferentes (ex.: SQL injection e God File).
5. Mínimo esperado por projeto: ≥ 5 findings e ≥ 1 CRITICAL/HIGH — se não atingir, revise a varredura antes de concluir que o projeto está limpo.
