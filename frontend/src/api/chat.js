import request from "@/utils/request";

const BASE_URL = "/v1/chat";

/**
 * 创建一个新的聊天会话
 * @returns {Promise<Object>} 返回包含新会话信息的对象
 */
export const createSession = () =>
	request.post(`${BASE_URL}/sessions`, {}, { loading: "session-create" });

/**
 * 获取 QQBot 专用的聊天会话
 * @returns {Promise<Object>} 返回 QQBot 会话对象
 */
export const getQQBotSession = () => request.get(`${BASE_URL}/qqbot-session`);

/**
 * 获取当前用户的聊天会话列表
 * @param {Object} params - 查询参数（如 query 用于搜索过滤）
 * @returns {Promise<Array>} 返回会话列表数组
 */
export const getSessions = (params) =>
	request.get(`${BASE_URL}/sessions`, {
		params,
		loading: "session-list",
	});

/**
 * 获取指定会话的历史消息记录
 * @param {string|number} sessionId - 会话ID
 * @returns {Promise<Array>} 返回消息对象数组
 */
export const getMessages = (sessionId) =>
	request.get(`${BASE_URL}/sessions/${sessionId}/messages`, {
		loading: "message-list",
	});

/**
 * 删除指定的聊天会话
 * @param {string|number} sessionId - 会话ID
 * @returns {Promise<void>}
 */
export const deleteSession = (sessionId) =>
	request.delete(`${BASE_URL}/sessions/${sessionId}`, {
		loading: "session-delete",
	});

/**
 * 更新聊天会话的标题
 * @param {string|number} sessionId - 会话ID
 * @param {string} title - 新的标题内容
 * @returns {Promise<void>}
 */
export const updateSession = (sessionId, title) =>
	request.patch(
		`${BASE_URL}/sessions/${sessionId}`,
		{ title },
		{ loading: "session-update" },
	);

/**
 * 获取系统支持的 AI 模型列表
 * @returns {Promise<Array>} 返回模型信息数组
 */
export const getModels = () =>
	request.get(`${BASE_URL}/models`, { loading: false });

export const getAvailableAgents = () =>
	request.get("/v1/agents/list", { loading: false, silent: true });

/**
 * 更新单条消息的反馈状态（如点赞/踩）
 * @param {string|number} messageId - 消息ID
 * @param {string} feedback - 反馈类型 ('like' | 'dislike' | null)
 * @returns {Promise<void>}
 */
export const updateMessageFeedback = (messageId, feedback) =>
	request.post(`${BASE_URL}/messages/${messageId}/feedback`, { feedback });

/**
 * 更新单条消息的收藏状态
 * @param {string|number} messageId - 消息ID
 * @param {boolean} isFavorite - 是否收藏
 * @returns {Promise<void>}
 */
export const updateMessageFavorite = (messageId, isFavorite) =>
	request.post(`${BASE_URL}/messages/${messageId}/favorite`, {
		is_favorite: isFavorite,
	});

/**
 * 将指定会话分享并生成分享链接
 * @param {string|number} sessionId - 会话ID
 * @returns {Promise<Object>} 返回分享链接或 shareId 信息
 */
export const shareSession = (sessionId) =>
	request.post(`${BASE_URL}/sessions/${sessionId}/share`);

/**
 * 获取他人分享的会话内容
 * @param {string} shareId - 分享ID
 * @returns {Promise<Object>} 返回分享的会话和消息详情
 */
export const getSharedSession = (shareId) =>
	request.get(`${BASE_URL}/shared/${shareId}`);

/**
 * 发送消息并处理流式响应
 * @param {string|number} sessionId - 当前会话ID
 * @param {string} content - 用户输入的消息文本
 * @param {string} modelId - 选用的 AI 模型ID
 * @param {Array} images - 附带的图片数据
 * @param {Array} attachments - 附带的文件UUID列表
 * @param {Function} onChunk - 接收到流数据块时的回调函数
 * @param {Object} options - 额外配置选项（如 abort signal）
 * @returns {Promise<void>}
 * @throws 抛出网络异常或解析异常
 */
export const sendMessageStream = async (
	sessionId,
	content,
	modelId,
	images,
	attachments,
	onChunk,
	options = {},
) => {
	// Note: Streaming is handled via fetch to support reading the stream
	// We can manually trigger loading store if needed, but usually chat UI handles this state
	// specifically for the "typing" effect.

	const token = localStorage.getItem("access_token");
	const headers = {
		"Content-Type": "application/json",
	};
	if (token) {
		headers.Authorization = `Bearer ${token}`;
	}

	try {
		// Use relative path which goes through proxy
		const response = await fetch(`/api${BASE_URL}/sessions/${sessionId}/send`, {
			method: "POST",
			headers,
			body: JSON.stringify({
				content,
				model_id: modelId,
				images: images || [],
				attachments: attachments || [],
				extra: options.extra || {},
			}),
			signal: options.signal,
		});

		if (!response.ok) {
			let errorMessage = `HTTP error! status: ${response.status}`;
			try {
				const errorData = await response.json();
				if (errorData.detail) errorMessage = errorData.detail;
			} catch (_e) {
				/* ignore */
			}
			throw new Error(errorMessage);
		}

		const reader = response.body.getReader();
		const decoder = new TextDecoder();
		let buffer = "";

		while (true) {
			const { value, done } = await reader.read();
			if (done) break;

			const chunk = decoder.decode(value, { stream: true });
			buffer += chunk;

			// Split by newlines, handling potential split JSON
			const lines = buffer.split("\n");
			// Keep the last partial line in buffer
			buffer = lines.pop() || "";

			for (const line of lines) {
				if (!line.trim()) continue;

				// Check for plain text error from backend
				if (line.startsWith("Error:")) {
					throw new Error(line);
				}

				let data;
				try {
					let jsonStr = line;
					if (line.startsWith("data: ")) {
						jsonStr = line.slice(6);
					}
					if (jsonStr.trim() === "[DONE]") continue;

					data = JSON.parse(jsonStr);
				} catch (_e) {
					console.warn("Failed to parse JSON chunk:", line);
					continue;
				}

				if (data.error) {
					throw new Error(data.error);
				}
				onChunk(data);
			}
		}

		// Process remaining buffer
		if (buffer.trim() && buffer.trim() !== "[DONE]") {
			if (buffer.startsWith("Error:")) {
				throw new Error(buffer);
			}
			let data;
			try {
				let jsonStr = buffer;
				if (buffer.startsWith("data: ")) {
					jsonStr = buffer.slice(6);
				}
				data = JSON.parse(jsonStr);
			} catch (_e) {
				// ignore
			}
			if (data) {
				if (data.error) {
					throw new Error(data.error);
				}
				onChunk(data);
			}
		}
	} catch (error) {
		console.error("Streaming error:", error);
		throw error;
	}
};
