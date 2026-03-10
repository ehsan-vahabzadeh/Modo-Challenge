#!/usr/bin/env bash
set -euo pipefail

# Configure this repository to use merge-style pulls and avoid ambiguous pull strategy errors.
git config pull.rebase false
git config pull.ff false

echo "Configured repo pull strategy: merge (pull.rebase=false, pull.ff=false)"
