#!/bin/sh
set -eu
cd "$(dirname "$0")/.."
set -a
. ./.env
set +a
export USQUANT_TEST_MYSQL=1
.venv/bin/python -m unittest discover -s tests -v
.venv/bin/python -m usquant demo --backend mysql --native
