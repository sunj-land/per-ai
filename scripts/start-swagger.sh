#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

if [[ -f "${PROJECT_ROOT}/.env" ]]; then
    set -a
    source "${PROJECT_ROOT}/.env"
    set +a
fi

BACKEND_PORT="${BACKEND_PORT:-8000}"
AGENT_PORT="${AGENT_PORT:-8001}"

BACKEND_SWAGGER="http://127.0.0.1:${BACKEND_PORT}/docs"
AGENT_SWAGGER="http://127.0.0.1:${AGENT_PORT}/docs"

check_http_200() {
    local url="$1"
    local code
    code="$(curl -s -m 2 -o /dev/null -w '%{http_code}' "${url}" 2>/dev/null || true)"
    [[ "${code}" == "200" ]]
}

open_url() {
    local url="$1"
    if command -v open >/dev/null 2>&1; then
        open "${url}"
    elif command -v xdg-open >/dev/null 2>&1; then
        xdg-open "${url}"
    else
        echo "  无法自动打开浏览器，请手动访问: ${url}"
    fi
}

OPENED=0

if check_http_200 "http://127.0.0.1:${BACKEND_PORT}/health"; then
    echo "Backend Swagger: ${BACKEND_SWAGGER}"
    open_url "${BACKEND_SWAGGER}"
    OPENED=$((OPENED + 1))
else
    echo "Backend 未运行 (端口 ${BACKEND_PORT})，跳过。"
fi

if check_http_200 "http://127.0.0.1:${AGENT_PORT}/health"; then
    echo "Agents  Swagger: ${AGENT_SWAGGER}"
    open_url "${AGENT_SWAGGER}"
    OPENED=$((OPENED + 1))
else
    echo "Agents  未运行 (端口 ${AGENT_PORT})，跳过。"
fi

if [[ "${OPENED}" -eq 0 ]]; then
    echo "两个服务均未启动，请先运行 scripts/start-dev.sh。" >&2
    exit 1
fi
