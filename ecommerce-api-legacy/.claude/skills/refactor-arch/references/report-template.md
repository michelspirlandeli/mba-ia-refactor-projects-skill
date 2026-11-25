# Template do Relatório de Auditoria (Fase 2)

O relatório deve seguir **exatamente** esta estrutura (Markdown). Ele é impresso no terminal
e salvo em arquivo. Substitua os `<placeholders>`.

## Regras

1. Findings ordenados por severidade: **CRITICAL → HIGH → MEDIUM → LOW**. Dentro da mesma
   severidade, ordem do ID do catálogo.
2. Numere os findings sequencialmente (`#1`, `#2`, ...) — a Fase 3 referencia esses números.
3. `File:` sempre com caminho relativo à raiz do projeto e linha(s) exata(s):
   `arquivo.py:42`, `arquivo.py:10-35`, ou `arquivo.py:28, 47-50` para ocorrências múltiplas.
   Vários arquivos → uma linha `File:` por arquivo.
4. `Description:` cita a evidência concreta (valor do literal, nome da função, trecho curto).
5. `Impact:` consequência técnica/de negócio. `Recommendation:` ação + padrão do playbook (`P-xx`).
6. O **Summary** deve bater com a contagem real de findings.
7. Inclua a seção de APIs deprecated mesmo quando vazia ("Nenhuma API deprecated detectada para <stack/versão>").

---

## Template

```markdown
================================
ARCHITECTURE AUDIT REPORT
================================
Project: <nome-do-diretório>
Stack:   <Linguagem> + <Framework versão> (<banco>)
Files:   <N> analyzed | ~<L> lines of code
Date:    <YYYY-MM-DD>

## Summary
CRITICAL: <n> | HIGH: <n> | MEDIUM: <n> | LOW: <n>

## Findings

### #1 [CRITICAL] <Nome do anti-pattern> (AP-xx)
File: <arquivo>:<linhas>
Description: <o que foi encontrado, com evidência>
Impact: <por que importa>
Recommendation: <como corrigir> (Playbook P-xx)

### #2 [HIGH] <...> (AP-xx)
File: ...
Description: ...
Impact: ...
Recommendation: ...

<... demais findings ...>

## Deprecated APIs
| File:Line | Deprecated | Modern replacement |
|---|---|---|
| <arquivo:linha> | <api> | <substituto> |

## Architecture Overview (current → target)
- Current: <estilo atual em 1-2 linhas>
- Target:  MVC — config / models / controllers (+services) / views(routes) / middlewares / entry point

================================
Total: <N> findings
================================

Phase 2 complete. Proceed with refactoring (Phase 3)? [y/n]
```

---

## Exemplo de finding bem escrito

```markdown
### #2 [CRITICAL] SQL Injection (AP-01)
File: models.py:28, 47-50, 58-60, 68, 92, 109-111
Description: Queries montadas por concatenação de strings com dados do request, ex.:
`"SELECT * FROM usuarios WHERE email = '" + email + "' AND senha = '" + senha + "'"`.
Impact: Bypass de login (`' OR '1'='1`), leitura/alteração/remoção de qualquer tabela.
Recommendation: Usar placeholders `?` com tupla de parâmetros em todas as queries (Playbook P-01).
```

## Exemplo de finding mal escrito (evitar)

```markdown
### [HIGH] Código ruim
File: models.py
Description: O código tem problemas de segurança.
```
(sem linha, sem evidência, sem ID, sem recomendação acionável)
