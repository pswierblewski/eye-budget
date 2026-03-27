#!/bin/bash
# Usage:
#   scp pawel@192.168.1.184:/home/pawel/eye-budget/backend/.env /tmp/backend.env
#   bash scripts/set-github-secrets.sh /tmp/backend.env
#   rm /tmp/backend.env

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENV_EXAMPLE="$SCRIPT_DIR/../.env.example"
ENV_FILE="${1:-}"

if [[ ! -f "$ENV_EXAMPLE" ]]; then
  echo "ERROR: .env.example not found at $ENV_EXAMPLE"
  exit 1
fi

if [[ -n "$ENV_FILE" ]]; then
  if [[ ! -f "$ENV_FILE" ]]; then
    echo "ERROR: env file not found: $ENV_FILE"
    exit 1
  fi
  set -a
  # shellcheck disable=SC1090
  source "$ENV_FILE"
  set +a
fi

if ! command -v gh &>/dev/null; then
  echo "ERROR: gh CLI not found. Install from https://cli.github.com"
  exit 1
fi

echo "Setting GitHub secrets from .env.example variable names..."
echo ""

set_count=0
skip_count=0

while IFS= read -r line; do
  [[ "$line" =~ ^[[:space:]]*# ]] && continue
  [[ -z "${line//[[:space:]]/}" ]] && continue

  key="${line%%=*}"
  key="${key//[[:space:]]/}"
  [[ "$key" =~ ^[A-Za-z_][A-Za-z0-9_]*$ ]] || continue

  value="${!key:-}"

  if [[ -z "$value" ]]; then
    echo "  SKIP  $key (not in environment)"
    ((skip_count++)) || true
    continue
  fi

  gh secret set "$key" -b "$value"
  echo "  SET   $key"
  ((set_count++)) || true

done < "$ENV_EXAMPLE"

echo ""
echo "Done: $set_count set, $skip_count skipped."
