import request from "@/utils/request";

const BASE_URL = "/v1/agent-center";

/**
 * 解包后端返回的统一数据结构
 * @param {Object} payload - 响应体数据，可能包含 code, msg, data 字段
 * @returns {any} 返回实际的业务数据 payload.data 或 payload 本身
 * @throws 抛出请求失败异常（当 code !== 0 时）
 */
const unwrapResponse = (payload) => {
	// request.js 返回 response.data
	// 如果 payload 是标准的后端响应体结构
	if (
		payload &&
		typeof payload === "object" &&
		Object.hasOwn(payload, "code")
	) {
		if (payload.code !== 0) {
			throw new Error(payload.msg || "请求失败");
		}
		return payload.data;
	}
	return payload;
};

/**
 * 获取所有的 Agent 列表
 * @param {Object} config - axios 请求配置
 * @returns {Promise<Array>} 返回 Agent 对象数组
 */
export const getAgentList = async (config = {}) => {
	const res = await request.get(`${BASE_URL}/agents`, {
		loading: "agent-list",
		...config,
	});
	return unwrapResponse(res);
};

/**
 * 同步本地的 Agent 状态
 * @param {Object} config - axios 请求配置
 * @returns {Promise<any>}
 */
export const syncAgents = async (config = {}) => {
	const res = await request.post(`${BASE_URL}/agents/sync`, {}, config);
	return unwrapResponse(res);
};

/**
 * 获取指定 Agent 的图结构或工作流数据
 * @param {string|number} id - Agent ID
 * @param {Object} config - axios 请求配置
 * @returns {Promise<Object>}
 */
export const getAgentGraph = async (id, config = {}) => {
	const res = await request.get(`${BASE_URL}/agents/${id}/graph`, config);
	return unwrapResponse(res);
};

/**
 * 获取已安装的 Skill 列表
 * @param {Object} config - axios 请求配置
 * @returns {Promise<Array>} 返回 Skill 对象数组
 */
export const getSkillList = async (config = {}) => {
	const res = await request.get(`${BASE_URL}/skills`, {
		loading: "skill-list",
		...config,
	});
	return unwrapResponse(res);
};

/**
 * 基础的安装 Skill 方法
 * @param {Object} payload - 安装所需的数据
 * @param {Object} headers - 请求头信息
 * @param {Object} config - axios 请求配置
 * @returns {Promise<Object>} 返回安装任务信息，例如 task_id
 */
export const installSkill = async (payload, headers = {}, config = {}) => {
	const res = await request.post(`${BASE_URL}/skills/install`, payload, {
		headers,
		loading: "skill-install",
		...config,
	});
	return unwrapResponse(res);
};

/**
 * 通过 URL 安装指定的 Skill
 * @param {string} url - Skill 的直链地址
 * @param {Object} config - axios 请求配置
 * @returns {Promise<Object>}
 */
export const installSkillByUrl = async (url, config = {}) => {
	return installSkill({ url, operation: "install" }, {}, config);
};

/**
 * 从 Skill Hub 在线安装 Skill
 * @param {string} name - Skill 名称
 * @param {string} version - 指定版本号
 * @param {Object} headers - 请求头信息
 * @param {Object} config - axios 请求配置
 * @returns {Promise<Object>}
 */
export const installSkillFromHub = async (
	name,
	version,
	headers = {},
	config = {},
) => {
	return installSkill({ name, version, operation: "install" }, headers, config);
};

/**
 * 获取指定 Skill 的详情
 * @param {string|number} id - Skill ID
 * @param {Object} config - axios 请求配置
 * @returns {Promise<Object>}
 */
export const getSkill = async (id, config = {}) => {
	const res = await request.get(`${BASE_URL}/skills/${id}`, config);
	return unwrapResponse(res);
};

/**
 * 获取指定 Skill 的 Markdown 文档内容
 * @param {string|number} id - Skill ID
 * @param {Object} config - axios 请求配置
 * @returns {Promise<string>}
 */
export const getSkillMarkdown = async (id, config = {}) => {
	const res = await request.get(`${BASE_URL}/skills/${id}/markdown`, config);
	return unwrapResponse(res);
};

/**
 * 创建一个新的自定义 Skill
 * @param {Object} data - Skill 配置数据
 * @param {Object} config - axios 请求配置
 * @returns {Promise<Object>}
 */
export const createSkill = async (data, config = {}) => {
	const res = await request.post(`${BASE_URL}/skills/create`, data, {
		loading: "skill-create",
		...config,
	});
	return unwrapResponse(res);
};

/**
 * 同步本地已安装的 Skill 列表
 * @param {Object} config - axios 请求配置
 * @returns {Promise<any>}
 */
export const syncSkills = async (config = {}) => {
	const res = await request.post(
		`${BASE_URL}/skills/sync`,
		{},
		{
			loading: "skill-sync",
			...config,
		},
	);
	return unwrapResponse(res);
};

/**
 * 更新指定 Skill 的 Markdown 文档
 * @param {string|number} id - Skill ID
 * @param {string} markdown - 新的 Markdown 内容
 * @param {Object} config - axios 请求配置
 * @returns {Promise<any>}
 */
export const updateSkillMarkdown = async (id, markdown, config = {}) => {
	const res = await request.put(
		`${BASE_URL}/skills/${id}/markdown`,
		{ markdown },
		config,
	);
	return unwrapResponse(res);
};

/**
 * 在 Skill Hub 中搜索 Skill
 * @param {Object} params - 搜索参数
 * @param {Object} config - axios 请求配置
 * @returns {Promise<Array>}
 */
export const searchSkillHub = async (params = {}, config = {}) => {
	const res = await request.get(`${BASE_URL}/skills/hub/search`, {
		params,
		loading: "skill-hub-search",
		...config,
	});
	return unwrapResponse(res);
};

/**
 * 获取 Skill 安装记录列表
 * @param {Object} params - 分页或筛选参数
 * @param {Object} config - axios 请求配置
 * @returns {Promise<Array>}
 */
export const getInstallRecords = async (params = {}, config = {}) => {
	const res = await request.get(`${BASE_URL}/skills/install-records`, {
		params,
		loading: "skill-records",
		...config,
	});
	return unwrapResponse(res);
};

/**
 * 卸载指定的 Skill
 * @param {string|number} id - Skill ID
 * @param {Object} config - axios 请求配置
 * @returns {Promise<any>}
 */
export const uninstallSkill = async (id, config = {}) => {
	const res = await request.delete(`${BASE_URL}/skills/${id}`, config);
	return unwrapResponse(res);
};

/**
 * 升级指定的 Skill
 * @param {string|number} id - Skill ID
 * @param {string} [version] - 目标版本号（可选，不传则默认最新）
 * @param {Object} config - axios 请求配置
 * @returns {Promise<Object>}
 */
export const upgradeSkill = async (id, version, config = {}) => {
	const res = await request.post(
		`${BASE_URL}/skills/install`,
		{
			id,
			version,
			operation: "upgrade",
		},
		{
			loading: "skill-upgrade",
			...config,
		},
	);
	return unwrapResponse(res);
};

/**
 * 建立 SSE 连接监听安装进度
 * @param {string} taskId - 任务 ID
 * @param {Function} onMessage - 接收到消息的回调
 * @param {Function} onError - 发生错误的回调
 * @returns {EventSource}
 */
export const streamInstallProgress = (taskId, onMessage, onError) => {
	const eventSource = new EventSource(
		`/api${BASE_URL}/skills/install/stream/${taskId}`,
	);

	eventSource.onmessage = (event) => {
		try {
			const data = JSON.parse(event.data);
			onMessage(data);
		} catch (e) {
			console.error("Parse SSE data error:", e);
		}
	};

	eventSource.onerror = (err) => {
		if (onError) onError(err);
		eventSource.close();
	};

	return eventSource;
};

export const getRssQualityConfig = async (config = {}) => {
	const res = await request.get(`${BASE_URL}/rss-quality/config`, {
		loading: "rss-quality-config",
		...config,
	});
	return unwrapResponse(res);
};

export const getDefaultRssQualityConfig = async (config = {}) => {
	const res = await request.get(
		`${BASE_URL}/rss-quality/config/default`,
		config,
	);
	return unwrapResponse(res);
};

export const updateRssQualityConfig = async (payload, config = {}) => {
	const res = await request.put(`${BASE_URL}/rss-quality/config`, payload, {
		loading: "rss-quality-config-save",
		...config,
	});
	return unwrapResponse(res);
};

export const scoreRssArticles = async (payload, config = {}) => {
	const res = await request.post(`${BASE_URL}/rss-quality/score`, payload, {
		loading: "rss-quality-score",
		...config,
	});
	return unwrapResponse(res);
};

export const getRssQualityResults = async (params = {}, config = {}) => {
	const res = await request.get(`${BASE_URL}/rss-quality/results`, {
		params,
		loading: "rss-quality-results",
		...config,
	});
	return unwrapResponse(res);
};

export const getRssQualityLogs = async (params = {}, config = {}) => {
	const res = await request.get(`${BASE_URL}/rss-quality/logs`, {
		params,
		loading: "rss-quality-logs",
		...config,
	});
	return unwrapResponse(res);
};
