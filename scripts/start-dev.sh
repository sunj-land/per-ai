#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
LOG_DIR="${PROJECT_ROOT}/logs"
PID_DIR="${PROJECT_ROOT}/pids"
SKIP_PORTS=0

print_help() {
	cat <<'EOF'
用法:
  scripts/start-dev.sh [debug-cli] [--skip-ports] [--help]

参数:
  debug-cli      以调试模式启动 langgraph-cli
  --skip-ports   跳过端口占用检测与清理
  --help         显示帮助信息
EOF
}

check_langgraph_config() {
    if ! python3 -c "import json, sys; json.load(open('agents/langgraph.json'))" 2>/dev/null; then
        echo "Error: agents/langgraph.json contains invalid JSON." >&2
        return 1
    fi
    return 0
}

for arg in "$@"; do
	case "${arg}" in
	debug-cli)
		DEBUG_CLI=1
		;;
	--skip-ports)
		SKIP_PORTS=1
		;;
	--help)
		print_help
		exit 0
		;;
	*)
		echo "未知参数: ${arg}" >&2
		print_help
		exit 2
		;;
	esac
done

mkdir -p "${LOG_DIR}" "${PID_DIR}"

if [[ "${DEBUG_CLI:-0}" -eq 1 ]]; then
    if ! check_langgraph_config; then
        exit 1
    fi

    LOG_FILE="${LOG_DIR}/langgraph-debug.log"
    echo "Starting langgraph-cli debug mode..."
    echo "Logs will be saved to ${LOG_FILE}"

    ENV_OPT=""
    if [[ -f "${PROJECT_ROOT}/.env" ]]; then
        ENV_OPT="--env ${PROJECT_ROOT}/.env"
    fi

    # Check if langgraph is installed
    if ! command -v langgraph >/dev/null 2>&1; then
        echo "Error: langgraph-cli not found. Please install it."
        exit 127
    fi

    set +e
    langgraph dev --host 0.0.0.0 --port 8000 --config agents/langgraph.json --watch $ENV_OPT | tee "${LOG_FILE}"
    EXIT_CODE=${PIPESTATUS[0]}
    set -e

    if [[ "${EXIT_CODE}" -ne 0 ]]; then
        echo "langgraph-cli failed with exit code ${EXIT_CODE}."
        echo "Log path: ${LOG_FILE}"
        exit "${EXIT_CODE}"
    fi
    exit 0
fi


if [[ -f "${PROJECT_ROOT}/.env" ]]; then
	set -a
	source "${PROJECT_ROOT}/.env"
	set +a
fi

BACKEND_PORT="${BACKEND_PORT:-8000}"
AGENT_PORT="${AGENT_PORT:-8001}"
FRONTEND_PORT="${FRONTEND_PORT:-3000}"

if [[ -n "${BACKEND_START_CMD:-}" ]]; then
	BACKEND_CMD="${BACKEND_START_CMD}"
elif [[ -f "${PROJECT_ROOT}/backend/pom.xml" ]]; then
	BACKEND_CMD="mvn spring-boot:run -Dspring.profiles.active=dev"
else
	BACKEND_CMD="uvicorn app.main:app --host 0.0.0.0 --port ${BACKEND_PORT} --reload"
fi
if command -v python >/dev/null 2>&1; then
        DEFAULT_AGENT_CMD="python -m main"
else
        DEFAULT_AGENT_CMD="python3 -m main"
fi
AGENT_CMD="${AGENT_START_CMD:-${DEFAULT_AGENT_CMD}}"
FRONTEND_CMD="${FRONTEND_START_CMD:-pnpm --dir frontend run dev}"

graceful_kill_pid() {
	local pid="$1"
	if ! kill -0 "${pid}" 2>/dev/null; then
		return
	fi
	kill -15 "${pid}" 2>/dev/null || true
	local start_ts
	start_ts="$(date +%s)"
	while kill -0 "${pid}" 2>/dev/null; do
		local now_ts
		now_ts="$(date +%s)"
		if ((now_ts - start_ts >= 10)); then
			kill -9 "${pid}" 2>/dev/null || true
			break
		fi
		sleep 1
	done
}

free_port_if_needed() {
	local port="$1"
	local pids
	pids="$(lsof -ti:"${port}" || true)"
	if [[ -z "${pids}" ]]; then
		return
	fi
	echo "端口 ${port} 被占用，正在尝试优雅关闭..."
	for pid in ${pids}; do
		graceful_kill_pid "${pid}"
	done
}

if [[ "${SKIP_PORTS}" -eq 0 ]]; then
	free_port_if_needed "${BACKEND_PORT}"
	free_port_if_needed "${AGENT_PORT}"
	free_port_if_needed "${FRONTEND_PORT}"
fi

start_service() {
	local name="$1"
	local cmd="$2"
	local cwd="$3"
	local logfile="$4"
	local pidfile="${PID_DIR}/${name}.pid"
	: >"${logfile}"
	(
		cd "${cwd}"
		exec bash -lc "${cmd}" >>"${logfile}" 2>&1
	) &
	local pid="$!"
	echo "${pid}" >"${pidfile}"
}

tail_service_log() {
	local name="$1"
	local logfile="$2"
	local color="$3"
	(tail -n 0 -F "${logfile}" 2>/dev/null | awk -v prefix="[${name}] " -v c="${color}" '{print c prefix $0 "\033[0m"; fflush();}') &
	echo "$!" >"${PID_DIR}/${name}.tail.pid"
}

cleanup_started() {
	"${SCRIPT_DIR}/stop-dev.sh" >/dev/null 2>&1 || true
}

trap cleanup_started ERR

BACKEND_LOG="${LOG_DIR}/backend.log"
AGENTS_LOG="${LOG_DIR}/agents.log"
FRONTEND_LOG="${LOG_DIR}/frontend.log"

start_service "backend" "${BACKEND_CMD}" "${PROJECT_ROOT}/backend" "${BACKEND_LOG}"
start_service "agents" "${AGENT_CMD}" "${PROJECT_ROOT}/agents" "${AGENTS_LOG}"
start_service "frontend" "${FRONTEND_CMD}" "${PROJECT_ROOT}" "${FRONTEND_LOG}"

tail_service_log "backend" "${BACKEND_LOG}" "\033[1;34m"
tail_service_log "agents" "${AGENTS_LOG}" "\033[1;35m"
tail_service_log "frontend" "${FRONTEND_LOG}" "\033[1;32m"

check_http_200() {
        local url="$1"
        local code
        code="$(curl -s -m 2 -o /dev/null -w '%{http_code}' "${url}" 2>/dev/null || true)"
        [[ "${code}" == "200" ]]
}

check_frontend_health() {
	check_http_200 "http://127.0.0.1:${FRONTEND_PORT}/frontend/health" ||
		check_http_200 "http://127.0.0.1:${FRONTEND_PORT}/"
}

check_port_listening() {
	local port="$1"
	lsof -ti:"${port}" >/dev/null 2>&1
}

wait_for_health() {
	local deadline=$((SECONDS + 30))
	while ((SECONDS < deadline)); do
		if check_http_200 "http://127.0.0.1:${BACKEND_PORT}/health" &&
			check_http_200 "http://127.0.0.1:${AGENT_PORT}/health" &&
			(check_frontend_health || check_port_listening "${FRONTEND_PORT}"); then
			return 0
		fi
		sleep 1
	done
	return 1
}

if ! wait_for_health; then
	echo "健康检查失败，正在输出最近日志并停止所有进程..." >&2
	tail -n 80 "${BACKEND_LOG}" >&2 || true
	tail -n 80 "${AGENTS_LOG}" >&2 || true
	tail -n 80 "${FRONTEND_LOG}" >&2 || true
	cleanup_started
	exit 20
fi

trap - ERR
echo "全部服务启动成功。"
echo "Backend:  http://127.0.0.1:${BACKEND_PORT}/health"
echo "Agents:   http://127.0.0.1:${AGENT_PORT}/health"
echo "Frontend: http://127.0.0.1:${FRONTEND_PORT}/"
