#!/usr/bin/env sh
# Smoke test do ecommerce-api-legacy.
# Uso: ADMIN_TOKEN=<token> SEED_USER_PASSWORD=<senha> sh scripts/smoke_project2.sh [http://localhost:3000] [--security]
# (a API deve estar rodando com os mesmos ADMIN_TOKEN e SEED_USER_PASSWORD)
B=${1:-http://localhost:3000}
T=${ADMIN_TOKEN:-}
P=${SEED_USER_PASSWORD:-}
c() { printf '%-7s %-32s ' "$1" "$2"; curl -s -o /dev/null -w "%{http_code}\n" -X "$1" "$B$2" -H "Content-Type: application/json" ${T:+-H "X-Admin-Token: $T"} ${3:+-d "$3"}; }

c POST /api/checkout '{"usr":"Guilherme","eml":"gui@fullcycle.com.br","pwd":"senhaforte","c_id":2,"card":"4111222233334444"}'
c POST /api/checkout '{"usr":"João","eml":"joao@teste.com","pwd":"123","c_id":1,"card":"5111222233334444"}'
c POST /api/checkout "{\"usr\":\"Leonan\",\"eml\":\"leonan@fullcycle.com.br\",\"pwd\":\"$P\",\"c_id\":2,\"card\":\"4111\"}"
c POST /api/checkout '{"usr":"X","eml":"x@x.com","c_id":99,"card":"4111"}'
c POST /api/checkout '{"usr":"X"}'
c GET /api/admin/financial-report
c DELETE /api/users/1
c DELETE /api/users/999
c GET /nao-existe

if [ "$2" = "--security" ]; then
  echo "--- segurança / integridade"
  c POST /api/checkout '{"usr":"Guilherme","eml":"gui@fullcycle.com.br","pwd":"errada1","c_id":1,"card":"4111"}'      # 401 senha errada
  c POST /api/checkout '{"usr":"Guilherme","eml":"gui@fullcycle.com.br","c_id":1,"card":"4111"}'                    # 401 sem senha
  c POST /api/checkout '{"usr":"Guilherme","eml":"gui@fullcycle.com.br","pwd":"senhaforte","c_id":2,"card":"4111"}' # 409 já matriculado
  c POST /api/checkout '{"usr":{"a":1},"eml":"y@y.com","pwd":"senhaforte","c_id":1,"card":"4111"}'                 # 400 tipo
  c POST /api/checkout '{"usr":"Y","eml":["y@y.com"],"pwd":"senhaforte","c_id":1,"card":"4111"}'                   # 400 tipo
  c POST /api/checkout '{"usr":"Y","eml":"y@y.com","pwd":123456,"c_id":1,"card":"4111"}'                           # 400 tipo
  c POST /api/checkout '{"usr":"Y","eml":"y@y.com","pwd":"123","c_id":1,"card":"4111"}'                            # 400 senha curta
  printf '%-7s %-32s ' POST '/api/checkout (latin9)'; curl -s -o /dev/null -w "%{http_code}\n" -X POST "$B/api/checkout" -H "Content-Type: application/json; charset=latin9" -d '{}'  # 415
  printf '%-7s %-32s ' GET '/api/admin/... (sem token)'; curl -s -o /dev/null -w "%{http_code}\n" "$B/api/admin/financial-report"            # 403
fi
