#!/usr/bin/env sh
# Smoke test do ecommerce-api-legacy (rode com a API em http://localhost:3000).
B=${1:-http://localhost:3000}
c() { printf '%-7s %-32s ' "$1" "$2"; curl -s -o /dev/null -w "%{http_code}\n" -X "$1" "$B$2" -H "Content-Type: application/json" ${3:+-d "$3"}; }
c POST /api/checkout '{"usr":"Guilherme","eml":"gui@fullcycle.com.br","pwd":"senhaforte","c_id":2,"card":"4111222233334444"}'
c POST /api/checkout '{"usr":"João","eml":"joao@teste.com","pwd":"123","c_id":1,"card":"5111222233334444"}'
c POST /api/checkout '{"usr":"Leonan","eml":"leonan@fullcycle.com.br","c_id":2,"card":"4111"}'
c POST /api/checkout '{"usr":"X","eml":"x@x.com","c_id":99,"card":"4111"}'
c POST /api/checkout '{"usr":"X"}'
c GET /api/admin/financial-report
c DELETE /api/users/1
c DELETE /api/users/999
c GET /nao-existe
