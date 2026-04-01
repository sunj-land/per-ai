#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
PID_DIR="${PROJECT_ROOT}/pids"

graceful_stop() {
	local pid="$1"
	if ! kill -0 "${pid}" 2>/dev/null; then
		return 0
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

stop_by_pid_file() {
	local pid_file="$1"
	if [[ ! -f "${pid_file}" ]]; then
		return
	fi
	local pid
	pid="$(cat "${pid_file}")"
	if [[ -n "${pid}" ]]; then
		graceful_stop "${pid}"
	fi
	rm -f "${pid_file}"
}

stop_by_pid_file "${PID_DIR}/backend.pid"
stop_by_pid_file "${PID_DIR}/agents.pid"
stop_by_pid_file "${PID_DIR}/frontend.pid"
stop_by_pid_file "${PID_DIR}/backend.tail.pid"
stop_by_pid_file "${PID_DIR}/agents.tail.pid"
stop_by_pid_file "${PID_DIR}/frontend.tail.pid"

echo "开发环境进程已停止。"
