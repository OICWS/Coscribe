#!/usr/bin/env bash
# The checks CI runs, in the same order, so a local pass means a CI pass.
#   bash scripts/check.sh          everything (the tests take about 4 minutes on 4 CPUs)
#   bash scripts/check.sh --fast   everything except pytest
set -euo pipefail
cd "$(dirname "$0")/.."

if [ -d .venv/bin ]; then
  PATH="$PWD/.venv/bin:$PATH"
elif [ -d .venv/Scripts ]; then
  PATH="$PWD/.venv/Scripts:$PATH"
fi

fast=0
[ "${1:-}" = "--fast" ] && fast=1

echo "== frontend: tsc -b and vite build =="
# `tsc -b` is stricter than `tsc --noEmit -p .`; CI runs this one.
(cd frontend && npm run build)

echo "== frontend unit tests (vitest) =="
(cd frontend && npm test)

echo "== oxlint =="
(cd frontend && npx --no-install oxlint)

echo "== ruff =="
ruff check src tests
# A text file opened without an encoding reads in the locale's code page on
# Windows, not UTF-8. It is a preview rule, and `preview = true` in the config
# would turn on other rules' preview behaviour too, so it runs on its own.
ruff check --preview --select PLW1514 src tests

echo "== mypy =="
mypy src

echo "== import boundaries =="
lint-imports

# Numbers about the code that may only get better (quality/baseline.json): a worse
# number fails. Raising one is the maintainer's decision (`ratchet.py --update --accept-worse`).
echo "== generated wire types =="
python scripts/gen_wire_ts.py --check

echo "== component map =="
python scripts/gen_components.py --check

echo "== ratchet =="
python scripts/ratchet.py --enforce

if [ "$fast" -eq 0 ]; then
  echo "== pytest =="
  if [ -n "${COSCRIBE_COVERAGE:-}" ]; then
    # CI sets this; locally it costs a fifth more time for a number nobody reads.
    pytest -q -n 4 --reruns 1 --cov --cov-report=term --cov-report=xml
  else
    pytest -q -n 4 --reruns 1
  fi
fi
echo "All checks passed."
