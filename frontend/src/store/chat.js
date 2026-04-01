/*
 * @Author: Project Rules
 * @Date: 2024-03-17
 * @Description: Chat Store using Pinia
 */

import { Message, Modal } from "@arco-design/web-vue";
import { defineStore } from "pinia";
import { computed, ref } from "vue";
import {
	createSession,
	deleteSession,
	getAvailableAgents,
	getMessages,
	getModels,
	getSessions,
	sendMessageStream,
	updateSession,
} from "../api/chat";
import { useLoadingStore } from "./loading";

export const useChatStore = defineStore("chat", () => {
	const loadingStore = useLoadingStore();

	// State
	const sessions = ref([]); // 会话列表: 存储当前用户的所有聊天会话
	const currentSessionId = ref(null); // 当前选中的会话ID
	const messages = ref([]); // 当前会话的消息列表
	const models = ref([]); // 可用的AI模型列表
	const selectedModelId = ref(""); // 当前选中的AI模型ID
	const agents = ref([]); // 可用的Agent列表
	const selectedAgentId = ref(""); // 当前选中的Agent标识
	const searchQuery = ref(""); // 搜索关键词

	const isSending = computed(() => loadingStore.isLoading("chat-sending")); // 是否正在发送消息/生成回复
	const isFetching = computed(() => loadingStore.isLoading("message-list")); // 是否正在拉取消息列表

	let currentAbortController = null; // 用于中断当前流式请求的控制器

	// Actions
	/**
	 * 加载当前用户的会话列表
	 * 如果有搜索关键词，则带上 query 参数进行过滤
	 * @returns {Promise<void>}
	 * @throws 将捕获并提示加载失败的异常
	 */
	const loadSessions = async () => {
		try {
			const params = {};
			if (searchQuery.value) {
				params.query = searchQuery.value;
			}
			const res = await getSessions(params); // Loading handled in api/chat.js with 'session-list' key
			sessions.value = res;
		} catch (err) {
			console.error("Failed to load sessions", err);
			Message.error("Failed to load sessions");
		}
	};

	/**
	 * 加载特定的 QQBot 会话
	 * 成功获取后，自动选中该会话
	 * @returns {Promise<void>}
	 * @throws 捕获并提示加载 QQBot 会话失败的异常
	 */
	const loadQQBotSession = async () => {
		try {
			const { getQQBotSession } = await import("../api/chat");
			const res = await getQQBotSession();
			if (res?.id) {
				await selectSession(res.id);
			}
		} catch (err) {
			console.error("Failed to load QQBot session", err);
			Message.error("Failed to load QQBot session");
		}
	};

	/**
	 * 创建一个新的聊天会话
	 * @returns {Promise<Object>} 返回新创建的会话对象
	 * @throws 捕获并提示创建会话失败的异常
	 */
	const createNewSession = async () => {
		try {
			const res = await createSession(); // Loading handled in api/chat.js with 'session-create' key
			// ========== 步骤1：将会话添加到列表顶部 ==========
			sessions.value.unshift(res);
			// ========== 步骤2：自动选中新创建的会话 ==========
			await selectSession(res.id);
			return res;
		} catch (err) {
			console.error("Failed to create session", err);
			Message.error("Failed to create session");
		}
	};

	/**
	 * 删除指定的聊天会话
	 * @param {string|number} id - 要删除的会话ID
	 * @returns {Promise<void>}
	 * @throws 捕获并提示删除会话失败的异常
	 */
	const removeSession = async (id) => {
		try {
			await deleteSession(id); // Loading handled in api/chat.js with 'session-delete' key
			// ========== 步骤1：从会话列表中移除该会话 ==========
			sessions.value = sessions.value.filter((s) => s.id !== id);
			// ========== 步骤2：如果删除的是当前会话，则清空当前选中状态和消息列表 ==========
			if (currentSessionId.value === id) {
				currentSessionId.value = null;
				messages.value = [];
			}
			Message.success("Session deleted");
		} catch (err) {
			console.error("Failed to delete session", err);
			Message.error("Failed to delete session");
		}
	};

	/**
	 * 重命名聊天会话的标题
	 * @param {string|number} id - 会话ID
	 * @param {string} title - 新的标题
	 * @returns {Promise<void>}
	 * @throws 捕获并提示更新会话失败的异常
	 */
	const renameSession = async (id, title) => {
		try {
			await updateSession(id, title); // Loading handled in api/chat.js with 'session-update' key
			const session = sessions.value.find((s) => s.id === id);
			if (session) {
				session.title = title;
			}
		} catch (err) {
			console.error("Failed to update session", err);
			Message.error("Failed to update session");
		}
	};

	/**
	 * 选中指定会话并加载其消息记录
	 * @param {string|number} id - 要选中的会话ID
	 * @returns {Promise<void>}
	 * @throws 捕获并提示加载消息失败的异常
	 */
	const selectSession = async (id) => {
		if (currentSessionId.value === id) return;

		currentSessionId.value = id;
		try {
			const res = await getMessages(id); // Loading handled in api/chat.js with 'message-list' key
			messages.value = res;
		} catch (err) {
			console.error("Failed to load messages", err);
			Message.error("Failed to load messages");
		}
	};

	/**
	 * 获取可用的大语言模型列表
	 * @returns {Promise<void>}
	 * @throws 捕获加载模型失败的异常
	 */
	const loadModelsList = async () => {
		try {
			const res = await getModels();
			const sourceList = Array.isArray(res)
				? res
				: Array.isArray(res?.data)
					? res.data
					: [];
			const normalizedModels = sourceList
				.map((model, index) => {
					const id =
						model?.id || model?.model || model?.name || `model_${index}`;
					const name =
						model?.name || model?.label || model?.id || model?.model || id;
					return {
						...model,
						id,
						name,
					};
				})
				.filter((model) => !!model.id);
			const deepseekModel = {
				id: "deepseek/deepseek-chat",
				name: "DeepSeek Chat",
				enabled: true,
			};
			const hasDeepseek = normalizedModels.some(
				(model) => model.id === deepseekModel.id,
			);
			if (!hasDeepseek) {
				normalizedModels.push(deepseekModel);
			}
			models.value = normalizedModels;
			// 如果当前没有选中的模型，默认选中第一个
			if (normalizedModels.length > 0 && !selectedModelId.value) {
				selectedModelId.value = normalizedModels[0].id;
			}
		} catch (err) {
			console.error("Failed to load models", err);
		}
	};

	const loadAgentsList = async () => {
		try {
			const res = await getAvailableAgents();
			const sourceList = Array.isArray(res) ? res : [];
			const normalizedAgents = sourceList
				.map((agent, index) => {
					const id = agent?.name || agent?.id || `agent_${index}`;
					const name = agent?.name || agent?.id || id;
					return {
						...agent,
						id,
						name,
					};
				})
				.filter((agent) => !!agent.id);
			agents.value = normalizedAgents;
			if (
				selectedAgentId.value &&
				!normalizedAgents.some((agent) => agent.id === selectedAgentId.value)
			) {
				selectedAgentId.value = "";
			}
		} catch (err) {
			console.error("Failed to load agents", err);
			agents.value = [];
		}
	};

	/**
	 * 发送消息并接收流式回复
	 * @param {string} content - 消息文本内容
	 * @param {Array} images - 附加的图片数组
	 * @param {Array} attachments - 附件UUID数组
	 * @param {Object} extra - 额外的扩展参数
	 * @returns {Promise<void>}
	 * @throws 捕获网络请求或流解析中的异常
	 */
	const sendMessage = async (
		content,
		images = [],
		attachments = [],
		extra = {},
	) => {
		// 检查输入是否为空
		if (!content.trim() && images.length === 0 && attachments.length === 0)
			return;
		if (!currentSessionId.value) return;

		// 取消之前可能正在进行的请求
		if (currentAbortController) {
			currentAbortController.abort();
			currentAbortController = null;
		}
		currentAbortController = new AbortController();
		const mergedExtra = {
			...extra,
		};
		if (selectedAgentId.value && !mergedExtra.agent_id) {
			mergedExtra.agent_id = selectedAgentId.value;
		}
		if (!selectedAgentId.value && mergedExtra.agent_id) {
			delete mergedExtra.agent_id;
		}

		// ========== 步骤1：构造用户消息并推入消息列表 ==========
		const userMsgId = Date.now();
		const userMsg = {
			id: userMsgId,
			tempId: userMsgId,
			role: "user",
			content: content,
			images: images.map((img) => img.url), // 兼容老版本或直接使用 base64
			attachments: attachments, // 新增: 附件 UUID 列表
			attachment_objs: mergedExtra.attachment_objs || [], // 如果传递了完整对象，则填充
			extra: mergedExtra,
		};
		messages.value.push(userMsg);

		loadingStore.startLoading("chat-sending");

		// ========== 步骤2：构造助手占位消息并推入消息列表 ==========
		const assistantMsgId = Date.now() + 1;
		const assistantMsg = {
			id: assistantMsgId,
			tempId: assistantMsgId,
			role: "assistant",
			content: "",
			isNew: true,
			thinkingComplete: false,
		};
		messages.value.push(assistantMsg);

		let thinkingBuffer = "";
		let contentBuffer = "";
		const streamOptions =
			mergedExtra.stream_options &&
			typeof mergedExtra.stream_options === "object"
				? mergedExtra.stream_options
				: {};
		const stageProgressEnabled = Boolean(
			streamOptions.stage_progress_enabled !== false,
		);
		const rawStreamEnabled = Boolean(
			streamOptions.raw_stream_enabled !== false,
		);

		try {
			// ========== 步骤3：发起流式请求，实时更新占位消息内容 ==========
			await sendMessageStream(
				currentSessionId.value,
				content,
				selectedModelId.value,
				images,
				attachments,
				(data) => {
					// 处理返回的数据对象 { content, reasoning, error }
					if (data.error) {
						throw new Error(data.error);
					}

					const msg = messages.value.find(
						(m) => m.id === assistantMsgId || m.tempId === assistantMsgId,
					);
					if (msg) {
						const streamEventText = JSON.stringify(data, null, 0);
						const nextStreamEventLog = Array.isArray(msg.stream_event_log)
							? [...msg.stream_event_log, streamEventText]
							: [streamEventText];
						msg.stream_event_log = nextStreamEventLog.slice(-80);
						if (data.metadata && typeof data.metadata === "object") {
							msg.extra = {
								...(msg.extra || {}),
								...data.metadata,
							};
						}
						if (rawStreamEnabled) {
							msg.extra = {
								...(msg.extra || {}),
								last_stream_event_text: streamEventText,
							};
						}
						// 累加思考过程和实际内容
						if (data.reasoning) {
							const isStageProgressChunk =
								(data.reasoning.startsWith("阶段流：") ||
									data.reasoning.startsWith("阶段：")) &&
								data.metadata &&
								typeof data.metadata === "object" &&
								data.metadata.stream_stage === "reasoning";
							if (!isStageProgressChunk || stageProgressEnabled) {
								thinkingBuffer += data.reasoning;
								msg.thinkingComplete = false;
							}
						}
						if (data.content) {
							contentBuffer += data.content;
						}
						msg.extra = {
							...(msg.extra || {}),
							stream_reasoning_text: thinkingBuffer,
							stream_answer_text: contentBuffer,
						};

						// 包含思考块的格式重构
						if (thinkingBuffer) {
							// 格式: <think>...</think>\n\n...
							msg.content = `<think>${thinkingBuffer}</think>\n\n${contentBuffer}`;
						} else {
							msg.content = contentBuffer;
						}
					}
				},
				{ signal: currentAbortController.signal, extra: mergedExtra },
			);

			const msg = messages.value.find(
				(m) => m.id === assistantMsgId || m.tempId === assistantMsgId,
			);
			if (msg) {
				msg.isNew = false;
				msg.thinkingComplete = Boolean(thinkingBuffer);
				if (thinkingBuffer) {
					msg.content = `<think>${thinkingBuffer}</think>\n\n${contentBuffer}`;
				} else {
					msg.content = contentBuffer;
				}
			}
		} catch (err) {
			// ========== 步骤4：异常处理与资源清理 ==========
			if (err.name === "AbortError") {
				console.log("Stream aborted");
				return;
			}
			console.error("Failed to send message", err);
			// 弹出错误提示框
			Modal.error({
				title: "Message Send Failed",
				content: `Reason: ${err.message || "Unknown error"}`,
				okText: "OK",
			});

			// 如果助手消息为空（未生成任何内容），则将其从列表中移除
			if (!contentBuffer && !thinkingBuffer) {
				messages.value = messages.value.filter((m) => m.id !== assistantMsgId);
			}
		} finally {
			loadingStore.stopLoading("chat-sending");
		}
	};

	/**
	 * 停止当前的回复生成
	 * 触发 AbortController 中断请求
	 */
	const stopGeneration = () => {
		if (currentAbortController) {
			currentAbortController.abort();
			currentAbortController = null;
			loadingStore.stopLoading("chat-sending");
		}
	};

	return {
		sessions,
		currentSessionId,
		messages,
		isSending,
		isFetching,
		models,
		selectedModelId,
		agents,
		selectedAgentId,
		searchQuery,
		loadSessions,
		loadQQBotSession,
		createNewSession,
		removeSession,
		renameSession,
		selectSession,
		loadModelsList,
		loadAgentsList,
		sendMessage,
		stopGeneration,
	};
});
