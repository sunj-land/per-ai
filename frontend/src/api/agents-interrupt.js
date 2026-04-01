import request from "@/utils/request";

/**
 * 启动 Agent 任务
 * @param {Object} data
 * @param {string} data.agent_id - Agent 标识，如 comprehensive_demo_agent
 * @param {string} data.thread_id - 会话唯一标识
 * @param {Object} data.input_data - 启动输入数据
 */
export const startAgent = (data) => {
	return request({
		baseURL: "",
		url: "/agents-api/v1/agents/start",
		method: "post",
		data,
	});
};

/**
 * 获取 Agent 任务状态
 * @param {string} agent_id - Agent 标识
 * @param {string} thread_id - 会话唯一标识
 */
export const getAgentStatus = (agent_id, thread_id) => {
	return request({
		baseURL: "",
		url: `/agents-api/v1/agents/${agent_id}/status/${thread_id}`,
		method: "get",
	});
};

/**
 * 恢复被中断的 Agent 任务
 * @param {Object} data
 * @param {string} data.agent_id - Agent 标识
 * @param {string} data.thread_id - 会话唯一标识
 * @param {Object} data.user_feedback - 用户确认或提供的反馈数据
 */
export const resumeAgent = (data) => {
	return request({
		baseURL: "",
		url: "/agents-api/v1/agents/resume",
		method: "post",
		data,
	});
};
