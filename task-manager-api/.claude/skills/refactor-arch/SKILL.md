---
name: refactor-arch
description: Analisa, audita e refatora uma codebase backend legada para o padrão MVC, de forma agnóstica de tecnologia (Python/Flask, Node.js/Express, etc.). Executa 3 fases — análise da stack, auditoria de anti-patterns com relatório por severidade (arquivo e linha exatos) e refatoração validada (boot + endpoints). Use quando o usuário pedir para auditar arquitetura, encontrar code smells, ou refatorar um projeto para MVC.
argument-hint: "[caminho-do-projeto (opcional, padrão: diretório atual)]"
---

# refactor-arch — Refatoração Arquitetural Automatizada

Você é um arquiteto de software sênior especializado em modernização de sistemas legados.
Sua missão é levar o projeto do diretório atual (ou `$ARGUMENTS`, se informado) a uma
arquitetura **MVC** limpa, segura e testável **sem quebrar o contrato HTTP existente**.

A skill é dividida em **3 fases sequenciais**. Nunca pule fases, nunca altere arquivos
antes da confirmação explícita do usuário ao final da Fase 2.

## Arquivos de referência (carregue sob demanda)

| Arquivo | Quando ler |
|---|---|
| [references/project-analysis.md](references/project-analysis.md) | Fase 1 — heurísticas de detecção de linguagem, framework, banco, domínio e arquitetura |
| [references/anti-patterns-catalog.md](references/anti-patterns-catalog.md) | Fase 2 — catálogo de anti-patterns, sinais de detecção, severidade, APIs deprecated |
| [references/report-template.md](references/report-template.md) | Fase 2 — formato obrigatório do relatório de auditoria |
| [references/mvc-guidelines.md](references/mvc-guidelines.md) | Fase 3 — arquitetura alvo, responsabilidades das camadas, estrutura de pastas por stack |
| [references/refactoring-playbook.md](references/refactoring-playbook.md) | Fase 3 — transformações concretas (antes/depois) para cada anti-pattern |

---

## FASE 1 — ANÁLISE DO PROJETO

Objetivo: entender **o que** é o projeto antes de julgar **como** ele está escrito.

1. Leia `references/project-analysis.md`.
2. Liste os arquivos do projeto ignorando `node_modules/`, `.venv/`, `venv/`, `__pycache__/`,
   `.git/`, `.claude/`, lockfiles e bancos (`*.db`).
3. Leia os manifestos (`requirements.txt`, `pyproject.toml`, `package.json`, `pom.xml`, `go.mod`, ...)
   para obter linguagem, framework **com versão** e dependências.
4. Leia **todos** os arquivos de código-fonte (não amostre — a auditoria precisa de linhas exatas).
   Conte arquivos e linhas (ex.: `wc -l`).
5. Identifique: entry point, como as rotas são registradas, onde está o acesso a dados,
   tabelas/entidades, domínio de negócio e o estilo arquitetural atual.
6. Mapeie o **contrato HTTP** atual (método + path + status de sucesso) — ele será usado na
   validação da Fase 3. Registre como iniciar a aplicação (comando, porta, seed necessário).
7. Imprima o resumo **exatamente** neste formato:

```
================================
PHASE 1: PROJECT ANALYSIS
================================
Language:      <linguagem + versão se detectável>
Framework:     <framework + versão>
Dependencies:  <deps relevantes, separadas por vírgula>
Domain:        <descrição curta do domínio (entidades principais)>
Architecture:  <estilo atual + observação curta sobre separação de camadas>
Source files:  <N> files analyzed (~<L> lines)
DB tables:     <tabelas/entidades>
Entry point:   <arquivo> (<comando de start>, porta <P>)
Endpoints:     <N> routes mapped
================================
```

Prossiga automaticamente para a Fase 2 (a Fase 1 é somente leitura).

---

## FASE 2 — AUDITORIA DE ARQUITETURA

Objetivo: cruzar o código contra o catálogo e produzir um relatório acionável.

1. Leia `references/anti-patterns-catalog.md` e `references/report-template.md`.
2. Para **cada** anti-pattern do catálogo, aplique os sinais de detecção em **todos** os
   arquivos lidos na Fase 1. Use busca textual (grep) para os sinais objetivos e leitura
   para os estruturais (God Class, lógica de negócio em rota, etc.).
3. Para cada ocorrência registre: severidade, nome do anti-pattern (ID do catálogo),
   `arquivo:linha` ou `arquivo:início-fim` **exatos**, descrição concreta (cite o trecho/valor),
   impacto e recomendação (referenciando o padrão do playbook).
   - Agrupe ocorrências do mesmo anti-pattern no mesmo arquivo em um finding com várias linhas
     (ex.: `models.py:28, 47-50, 58-60`), para não inflar o relatório.
   - **Não invente** problemas: cada finding precisa de evidência verificável no código.
   - Verifique **APIs deprecated** (seção específica do catálogo) para a versão detectada da stack.
4. Ordene os findings por severidade: CRITICAL → HIGH → MEDIUM → LOW.
5. Imprima o relatório completo seguindo o template e **salve-o** em
   `../reports/audit-<nome-do-projeto>.md` se a pasta `../reports/` existir
   (no repositório do desafio, o usuário pode renomear para `audit-project-N.md`).
   Salvar o relatório é a **única** escrita permitida antes da confirmação.
6. **PARE E PEÇA CONFIRMAÇÃO.** Termine a resposta com exatamente:

```
Phase 2 complete. Proceed with refactoring (Phase 3)? [y/n]
```

Não modifique nenhum arquivo do projeto até o usuário responder afirmativamente
(`y`, `yes`, `sim`, `s`, "pode seguir"...). Se responder `n`, encerre mantendo apenas o relatório.

---

## FASE 3 — REFATORAÇÃO PARA MVC

Objetivo: eliminar os findings e reestruturar para MVC **preservando o comportamento externo**.

1. Leia `references/mvc-guidelines.md` e `references/refactoring-playbook.md`.
2. **Planeje antes de editar**: monte a árvore alvo de diretórios adequada à stack
   (ver "Estrutura alvo por stack" nas guidelines) e mapeie cada finding → padrão do playbook.
   - Projeto monolítico / desestruturado → reestruturação completa em camadas.
   - Projeto parcialmente organizado → preserve o que está correto, extraia o que está
     faltando (controllers, config, error handler, camada de serviço) e corrija os findings.
     Não reescreva por reescrever.
3. Execute na ordem recomendada (reduz risco de quebra):
   1. **Config** — extraia segredos/constantes para módulo de config lendo variáveis de
      ambiente (com defaults seguros apenas para dev) + `.env.example`.
   2. **Models** — acesso a dados com queries parametrizadas, sem N+1, sem expor campos sensíveis.
   3. **Services/Controllers** — regra de negócio e orquestração fora das rotas.
   4. **Views/Routes** — apenas mapeamento HTTP → controller, validação de entrada e serialização.
   5. **Middlewares** — error handler centralizado, logging.
   6. **Composition root / entry point** — cria app, injeta dependências, registra rotas.
   7. Remova arquivos antigos que ficaram órfãos e atualize o README/manifesto (comando de start).
4. **Contrato HTTP é sagrado**: mesmos paths, métodos, nomes de campos de request/response e
   status codes de sucesso. Exceções permitidas **apenas** quando o comportamento original é uma
   falha de segurança (ex.: endpoint que executa SQL arbitrário, resposta que vaza senha/secret) —
   documente cada exceção no resumo final.
5. **Valide** (obrigatório, não declare sucesso sem evidência):
   1. Instale dependências se necessário (venv / `npm install`).
   2. Faça o boot da aplicação em background, aguarde a porta responder.
   3. Exercite **todos** os endpoints mapeados na Fase 1 (curl ou script), incluindo pelo menos
      um caminho de erro (404/400) para checar o error handler.
   4. Compare com o contrato original. Corrija e repita até passar.
   5. Re-execute os sinais de detecção do catálogo (grep) para confirmar que os findings
      foram eliminados. Pare a aplicação ao final.
6. Imprima o resumo final:

```
================================
PHASE 3: REFACTORING COMPLETE
================================
## New Project Structure
<árvore de diretórios>

## Findings addressed
<ID / severidade / como foi resolvido — uma linha por finding>

## Contract changes (security-driven)
<lista ou "none">

## Validation
  ✓ Application boots without errors
  ✓ All endpoints respond correctly (<N>/<N>)
  ✓ Zero CRITICAL/HIGH anti-patterns remaining
================================
```

Use `✗` e explique o motivo em qualquer item que não passou.

---

## Regras gerais

- Agnóstico de tecnologia: nunca assuma Flask/Express — detecte. Use os idiomas da stack
  detectada (Blueprints em Flask, `express.Router` em Express, etc.).
- Não adicione dependências pesadas sem necessidade; prefira a stdlib / o que o projeto já usa.
  Se adicionar (ex.: `werkzeug.security`, `bcrypt`/`crypto`), justifique.
- Mantenha os nomes de domínio do projeto (idioma original: `produtos`, `courses`, `tasks`...).
- Commits não fazem parte da skill — deixe isso para o usuário, a menos que ele peça.
