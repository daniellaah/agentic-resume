#!/usr/bin/env bash
set -euo pipefail

API_URL="${API_URL:-http://127.0.0.1:8000}"
REQUEST_FILE="${REQUEST_FILE:-examples/tailor_request.json}"

curl \
  --fail-with-body \
  --silent \
  --show-error \
  --request POST \
  --header "Content-Type: application/json" \
  --data "@${REQUEST_FILE}" \
  "${API_URL}/tailor"
