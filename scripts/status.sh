#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
PID_DIR="${PROJECT_ROOT}/pids"

if [[ -f "${PROJECT_ROOT}/.env" ]]; then
	set -a
	source "${PROJECT_ROOT}/.env"
	set +a
fi

BACKEND_PORT="${BACKEND_PORT:-8000}"
AGENT_PORT="${AGENT_PORT:-8001}"
FRONTEND_PORT="${FRONTEND_PORT:-3000}"

show_service() {
	local name="$1"
	local pid_file="${PID_DIR}/${name}.pid"
	if [[ ! -f "${pid_file}" ]]; then
		echo "${name}: stopped"
		return
	fi
	local pid
	pid="$(cat "${pid_file}")"
	if kill -0 "${pid}" 2>/dev/null; then
		echo "${name}: running (pid=${pid})"
	else
		echo "${name}: stale pid file (pid=${pid})"
	fi
}

show_port() {
	local label="$1"
	local port="$2"
	local pids
	pids="$(lsof -ti:"${port}" || true)"
	if [[ -z "${pids}" ]]; then
		echo "${label} port ${port}: free"
	else
		echo "${label} port ${port}: used by ${pids//$'\n'/,}"
	fi
}

show_service "backend"
show_service "agents"
show_service "frontend"
echo "---"
show_port "backend" "${BACKEND_PORT}"
show_port "agents" "${AGENT_PORT}"
show_port "frontend" "${FRONTEND_PORT}"
