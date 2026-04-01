<template>
  <div class="home-page">
    <!-- Model Selector Header -->
    <div class="chat-header">
      <a-select v-model="selectedModelId" :style="{width:'200px'}" placeholder="Select Model" @change="_handleModelChange">
         <a-option v-for="model in models" :key="model.id" :value="model.id">{{ model.name }}</a-option>
      </a-select>
      <a-select
        v-model="selectedPurpose"
        :style="{ width: '220px' }"
        placeholder="选择使用目的"
        @change="_handlePurposeChange"
      >
        <a-option v-for="item in PURPOSE_OPTIONS" :key="item.value" :value="item.value">
          {{ item.label }}
        </a-option>
      </a-select>
      <a-select
        v-model="selectedAgentId"
        :style="{ width: '260px' }"
        placeholder="选择 Agent"
        allow-clear
        @change="_handleAgentChange"
      >
        <a-option value="">无</a-option>
        <a-option v-for="agent in agents" :key="agent.id" :value="agent.id">
          {{ agent.name }}
        </a-option>
      </a-select>
      <a-popover trigger="click" position="bl">
        <a-button type="outline" size="small">流式显示设置</a-button>
        <template #content>
          <div class="stream-setting-panel">
            <div class="stream-setting-row">
              <span>显示阶段标签</span>
              <a-switch v-model="streamDisplayConfig.showStageTag" />
            </div>
            <div class="stream-setting-row">
              <span>显示阶段进度文本</span>
              <a-switch v-model="streamDisplayConfig.showStageProgressText" />
            </div>
            <div class="stream-setting-row">
              <span>显示原始流数据</span>
              <a-switch v-model="streamDisplayConfig.showRawStreamData" />
            </div>
          </div>
        </template>
      </a-popover>
    </div>

    <div class="chat-container" ref="chatContainer">
      <div v-if="!currentSessionId && messages.length === 0" class="empty-state">
         <div class="welcome-text">What can I help you with?</div>
      </div>
      <div v-else class="messages">
        <a-spin :loading="loadingStore.isLoading('message-list')" style="width: 100%">
        <div
          v-for="msg in messages"
          :key="msg.id"
          class="message-wrapper"
          :class="msg.role"
        >
          <div class="avatar">
             <a-avatar v-if="msg.role === 'assistant'" :size="32" style="background-color: rgb(var(--primary-6))">AI</a-avatar>
             <a-avatar v-else :size="32" style="background-color: rgb(var(--danger-6))">U</a-avatar>
          </div>
          <div class="message-content">
             <div class="bubble">
               <MessageContent
                  :content="msg.content"
                  :animate="!!msg.isNew"
                  :thinking-complete="msg.thinkingComplete === true || !msg.isNew"
               />
              <div v-if="streamDisplayConfig.showStageTag && (_buildRoutingDebugText(msg) || _buildStreamStageText(msg))" class="routing-debug">
                <a-tag
                  v-if="_buildStreamStageText(msg)"
                  size="small"
                  :color="_buildStreamStageColor(msg)"
                >
                  {{ _buildStreamStageText(msg) }}
                </a-tag>
                <a-tag v-if="_buildRoutingDebugText(msg)" size="small" color="arcoblue">{{ _buildRoutingDebugText(msg) }}</a-tag>
              </div>
              <div
                v-if="
                  streamDisplayConfig.showRawStreamData &&
                  _getMergedStreamSections(msg).reasoning
                "
                class="raw-stream-block"
              >
                <details class="raw-stream-thinking">
                  <summary>思维过程</summary>
                  <div class="raw-stream-text">
                    {{ _getMergedStreamSections(msg).reasoning }}
                  </div>
                </details>
              </div>
               <!-- Display Images -->
               <div v-if="msg.images && msg.images.length" class="message-images">
                  <a-image
                    v-for="(img, idx) in msg.images"
                    :key="idx"
                    :src="img"
                    width="100"
                    height="100"
                    style="margin-right: 8px; margin-top: 8px; object-fit: cover; border-radius: 4px;"
                  />
               </div>
               <!-- Display Attachments using attachment_objs -->
               <div v-if="msg.attachment_objs && msg.attachment_objs.length" class="message-attachments-container">
                   <template v-for="att in msg.attachment_objs" :key="att.uuid">
                       <!-- Image inline preview -->
                       <template v-if="att.mime_type && att.mime_type.startsWith('image/')">
                           <a-image
                               :src="_getPreviewUrl(att.uuid)"
                               width="120"
                               height="120"
                               style="margin-right: 8px; margin-top: 8px; object-fit: cover; border-radius: 4px; cursor: pointer;"
                               :preview-props="{
                                   actionsLayout: ['zoomIn', 'zoomOut', 'fullScreen', 'download']
                               }"
                           />
                       </template>
                       <!-- Non-image attachment card -->
                       <template v-else>
                           <div class="attachment-card">
                               <div class="attachment-icon">
                                   <icon-file-pdf v-if="att.mime_type && att.mime_type.includes('pdf')" :size="32" style="color: #f53f3f" />
                                   <icon-file v-else-if="att.mime_type && (att.mime_type.includes('word') || att.mime_type.includes('document'))" :size="32" style="color: #165dff" />
                                   <icon-file v-else-if="att.mime_type && (att.mime_type.includes('excel') || att.mime_type.includes('sheet'))" :size="32" style="color: #00b42a" />
                                   <icon-file-audio v-else-if="att.mime_type && att.mime_type.includes('audio')" :size="32" style="color: #ff7d00" />
                                   <icon-file-video v-else-if="att.mime_type && att.mime_type.includes('video')" :size="32" style="color: #722ed1" />
                                   <icon-file v-else :size="32" style="color: #86909c" />
                               </div>
                               <div class="attachment-info">
                                   <div class="attachment-name" :title="att.original_name">{{ att.original_name }}</div>
                                   <div class="attachment-meta">
                                       <span>{{ _formatSize(att.size) }}</span>
                                       <span style="margin-left: 8px; color: var(--color-text-3);">{{ att.created_at ? new Date(att.created_at).toLocaleString() : '' }}</span>
                                   </div>
                               </div>
                               <div class="attachment-actions">
                                   <a-button type="text" @click="_downloadAttachment(att.uuid, att.original_name)">
                                       <template #icon><icon-download /></template>
                                   </a-button>
                               </div>
                           </div>
                       </template>
                   </template>
               </div>

               <MessageActions
                  v-if="!msg.isNew || !isSending"
                  :content="msg.content"
                  :isAssistant="msg.role === 'assistant'"
                  :messageId="msg.id"
                 @regenerate="_handleRegenerate(msg.id)"
                 @feedback="_handleFeedback"
                 @share="_handleShare"
                 @favorite="_handleFavorite"
               />
             </div>
          </div>
        </div>
        <div v-if="isSending" class="message-wrapper assistant">
           <a-avatar :size="32" style="background-color: rgb(var(--primary-6))">AI</a-avatar>
           <div class="message-content">
              <div class="bubble">
                  <div class="stream-loading">
                    <icon-loading />
                    <span class="stream-loading-text">{{ liveStreamingText }}</span>
                  </div>
              </div>
           </div>
        </div>
        </a-spin>
      </div>
    </div>

    <div class="input-area-wrapper">
      <div class="input-card">
          <!-- Attachment Preview -->
          <div v-if="uploadedAttachments.length > 0" class="attachment-preview-area">
              <div v-for="(item, idx) in uploadedAttachments" :key="idx" class="attachment-preview-item" :class="{ error: item.status === 'error' }">
                  <div class="preview-content">
                      <!-- Image Preview -->
                      <img v-if="item.type.startsWith('image/')" :src="item.url" class="preview-img" />
                      <!-- File Icon for others -->
                      <div v-else class="file-icon">
                          <icon-file-pdf v-if="item.type.includes('pdf')" />
                          <icon-file v-else-if="item.type.includes('word') || item.type.includes('doc') || item.type.includes('excel') || item.type.includes('sheet')" />
                          <icon-file-audio v-else-if="item.type.includes('audio')" />
                          <icon-file-video v-else-if="item.type.includes('video')" />
                          <icon-file v-else />
                      </div>

                      <div class="file-info">
                          <span class="file-name" :title="item.name">{{ item.name }}</span>
                          <span class="file-size">{{ _formatSize(item.file.size) }}</span>
                      </div>

                    <!-- Upload Status -->
                    <div class="upload-status">
                        <a-progress
                           v-if="item.status === 'uploading'"
                           type="circle"
                           :percent="item.progress || 0"
                           :size="20"
                           :stroke-width="4"
                        />
                        <icon-check-circle-fill v-else-if="item.status === 'success'" style="color: rgb(var(--success-6))" />
                        <icon-close-circle-fill v-else-if="item.status === 'error'" style="color: rgb(var(--danger-6))" />
                    </div>
                  </div>
                  <div class="remove-btn" @click="_removeAttachment(idx)">
                      <icon-close />
                  </div>
              </div>
          </div>

          <div class="input-controls">
               <a-textarea
                v-model="inputContent"
                placeholder="发消息或输入'/'选择技能"
                :auto-size="{ minRows: 1, maxRows: 8 }"
                @keydown.enter.prevent="_handleEnterKey"
                :disabled="loadingStore.isLoading('chat-sending')"
                class="custom-textarea"
                />
          </div>

          <div class="input-actions">
              <div class="left-actions">
                  <a-dropdown trigger="click" position="tl">
                      <a-button type="text" shape="circle" class="action-btn">
                          <template #icon><icon-plus /></template>
                      </a-button>
                      <template #content>
                          <a-doption>
                              <template #icon><icon-cloud /></template>
                              选择云盘文件
                          </a-doption>
                          <a-doption>
                              <template #icon><icon-code /></template>
                              上传代码 <icon-right style="float:right; margin-top: 4px; margin-left: 8px; color: var(--color-text-3);"/>
                          </a-doption>
                          <a-doption>
                              <template #icon><icon-scissor /></template>
                              截图提问
                          </a-doption>
                          <a-doption>
                              <template #icon><icon-desktop /></template>
                              共享屏幕和应用 <icon-right style="float:right; margin-top: 4px; margin-left: 8px; color: var(--color-text-3);"/>
                          </a-doption>
                          <a-doption style="padding: 0;">
                              <a-upload
                                  :custom-request="_customUpload"
                                  :show-file-list="false"
                                  multiple
                                  style="width: 100%; display: block;"
                              >
                                  <template #upload-button>
                                      <div style="padding: 6px 12px; display: flex; align-items: center; width: 100%; cursor: pointer;">
                                          <icon-upload style="margin-right: 8px;" />
                                          上传文件或图片
                                      </div>
                                  </template>
                              </a-upload>
                          </a-doption>
                      </template>
                  </a-dropdown>

                  <div class="divider"></div>

                  <div class="shortcut-buttons">
                      <a-button
                            v-for="btn in _shortcutButtons"
                            :key="btn.id"
                            type="text"
                            class="shortcut-btn"
                            @click="handleShortcutClick(btn)"
                        >
                            <template #icon>
                                <icon-bulb v-if="btn.icon === 'icon-bulb'" />
                                <icon-search v-else-if="btn.icon === 'icon-search'" />
                                <component v-else :is="btn.icon" />
                            </template>
                            {{ btn.label }}
                            <icon-right v-if="btn.hasArrow" class="shortcut-arrow" />
                        </a-button>
                  </div>
              </div>
              <div class="right-actions">
                  <a-button
                    v-if="!inputContent.trim() && uploadedAttachments.length === 0 && !isSending"
                    type="secondary"
                    shape="circle"
                    class="mic-btn"
                  >
                      <template #icon><icon-voice /></template>
                  </a-button>
                  <a-button
                    v-else-if="!isSending"
                    type="primary"
                    shape="circle"
                    @click="handleSend"
                    :loading="loadingStore.isLoading('session-create')"
                    class="send-btn"
                    :disabled="hasPendingUploads"
                  >
                      <template #icon><icon-send /></template>
                  </a-button>
                  <a-button
                    v-else
                    type="outline"
                    status="danger"
                    shape="circle"
                    @click="chatStore.stopGeneration()"
                    class="stop-btn"
                  >
                      <template #icon><icon-record-stop /></template>
                  </a-button>
              </div>
          </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { Message } from "@arco-design/web-vue";
import { storeToRefs } from "pinia";
import { computed, nextTick, onMounted, onUnmounted, ref, watch } from "vue";
import { useLoadingStore } from "@/store/loading";
import { uploadAttachment } from "../../api/attachment";
import {
	shareSession,
	updateMessageFavorite,
	updateMessageFeedback,
} from "../../api/chat";
import MessageActions from "../../components/chat/MessageActions.vue";
import MessageContent from "../../components/chat/MessageContent.vue";
import { useChatStore } from "../../store/chat";

const chatStore = useChatStore();
const loadingStore = useLoadingStore();
const {
	currentSessionId,
	messages,
	models,
	selectedModelId,
	agents,
	selectedAgentId,
	isSending,
} = storeToRefs(chatStore);

const inputContent = ref("");
const chatContainer = ref(null);
const uploadedAttachments = ref([]); // { id, file, url, name, type, status, attachmentId, error }
const ignoreHistory = ref(false);
const selectedPurpose = ref("general");
const STREAM_DISPLAY_CONFIG_STORAGE_KEY = "chat_stream_display_config";
const streamDisplayConfig = ref({
	showStageTag: true,
	showStageProgressText: true,
	showRawStreamData: true,
});
const PURPOSE_OPTIONS = [
	{ value: "general", label: "通用对话" },
	{ value: "article_search", label: "文章检索" },
	{ value: "text_summarize", label: "文本总结" },
	{ value: "data_analysis", label: "数据分析" },
	{ value: "workflow_planning", label: "任务规划" },
];

// Configurable shortcut buttons
const _shortcutButtons = ref([
	{ id: "deep_think", label: "深度思考", icon: "icon-bulb", hasArrow: false },
	{ id: "web_search", label: "联网搜索", icon: "icon-search", hasArrow: false },
]);

const _handleShortcutClick = (btn) => {
	Message.info(`Clicked: ${btn.label}`);
	// TODO Implement specific logic based on btn.id
};

let eventSource = null;

// ... (keep existing lifecycle hooks and watchers)
onMounted(() => {
	const rawConfig = localStorage.getItem(STREAM_DISPLAY_CONFIG_STORAGE_KEY);
	if (rawConfig) {
		try {
			const parsedConfig = JSON.parse(rawConfig);
			if (parsedConfig && typeof parsedConfig === "object") {
				streamDisplayConfig.value = {
					showStageTag: parsedConfig.showStageTag !== false,
					showStageProgressText: parsedConfig.showStageProgressText !== false,
					showRawStreamData: parsedConfig.showRawStreamData !== false,
				};
			}
		} catch (_error) {}
	}
	chatStore.loadModelsList();
	chatStore.loadAgentsList();
	scrollToBottom();
});

watch(
	streamDisplayConfig,
	(newValue) => {
		localStorage.setItem(
			STREAM_DISPLAY_CONFIG_STORAGE_KEY,
			JSON.stringify({
				showStageTag: newValue.showStageTag !== false,
				showStageProgressText: newValue.showStageProgressText !== false,
				showRawStreamData: newValue.showRawStreamData !== false,
			}),
		);
	},
	{ deep: true },
);

watch(
	currentSessionId,
	(newId) => {
		if (eventSource) {
			eventSource.close();
			eventSource = null;
		}
		if (newId) {
			// 连接 SSE
			eventSource = new EventSource(`/api/v1/chat/sessions/${newId}/events`);
			eventSource.onmessage = (event) => {
				try {
          const data = JSON.parse(event.data);
          console.log("接受消息=====",data)
					if (data.type === "new_message") {
						const msg = data.message;
						// 查找乐观更新的消息（通过 id 匹配，或者通过 role 和临时数字 ID 匹配）
						const existingIdx = messages.value.findIndex(
							(m) =>
								m.id === msg.id ||
								(m.role === msg.role && typeof m.id === "number"),
						);
						if (existingIdx !== -1) {
							const isNew = messages.value[existingIdx].isNew;
							messages.value[existingIdx] = {
								...messages.value[existingIdx],
								...msg,
							};
							// 如果是 AI 消息，保留 isNew 标记以确保打字机动画正常完成
							if (isNew !== undefined) {
								messages.value[existingIdx].isNew = isNew;
							}
						} else {
							messages.value.push(msg);
						}
						scrollToBottom();
					}
				} catch (e) {
					console.error("SSE parse error", e);
				}
			};
		}
	},
	{ immediate: true },
);

onUnmounted(() => {
	if (eventSource) {
		eventSource.close();
		eventSource = null;
	}
});

watch(
	messages,
	() => {
		scrollToBottom();
	},
	{ deep: true },
);

const scrollToBottom = () => {
	nextTick(() => {
		if (chatContainer.value) {
			chatContainer.value.scrollTop = chatContainer.value.scrollHeight;
		}
	});
};

const _handleModelChange = (value) => {
	const model = models.value.find((m) => m.id === value);
	if (model) {
		Message.info(`Switched to ${model.name}`);
	}
};

const _handleAgentChange = (value) => {
	if (!value) {
		Message.info("已切换为默认对话模式");
		return;
	}
	const agent = agents.value.find((item) => item.id === value);
	if (agent) {
		Message.info(`Switched to ${agent.name}`);
	}
};

const _handlePurposeChange = (value) => {
	const selected = PURPOSE_OPTIONS.find((item) => item.value === value);
	if (selected) {
		Message.info(`当前使用目的：${selected.label}`);
	}
};

const _buildRoutingDebugText = (msg) => {
	if (!msg || msg.role !== "assistant" || !msg.extra) {
		return "";
	}
	const routing = msg.extra.routing;
	if (!routing || typeof routing !== "object") {
		return "";
	}
	const source = routing.source || "unknown";
	const targetAgent =
		routing.target_agent || msg.extra.source_agent || "unknown";
	const purpose = routing.purpose || "none";
	const confidence =
		typeof routing.confidence === "number"
			? `, conf=${Math.round(routing.confidence * 100)}%`
			: "";
	return `route:${source} -> ${targetAgent}, purpose=${purpose}${confidence}`;
};

const _buildStreamStageText = (msg) => {
	if (!msg || msg.role !== "assistant" || !msg.extra) {
		return "";
	}
	const stage = msg.extra.stream_stage;
	if (!stage || typeof stage !== "string") {
		return "";
	}
	const stageLabelMap = {
		routing: "阶段：路由中",
		reasoning: "阶段：思考中",
		final_answer: "阶段：生成答案",
	};
	return stageLabelMap[stage] || `阶段：${stage}`;
};

const _extractThinkingText = (content) => {
	if (!content || typeof content !== "string") {
		return "";
	}
	const match = content.match(/<think>([\s\S]*?)(?:<\/think>|$)/);
	return match?.[1] ? String(match[1]).trim() : "";
};

const _buildRawStreamText = (msg) => {
	if (!msg || msg.role !== "assistant" || !msg.extra) {
		return "";
	}
	const value = msg.extra.last_stream_event_text;
	if (!value || typeof value !== "string") {
		return "";
	}
	return value;
};

const _normalizeStreamEventData = (eventItem) => {
	if (!eventItem) {
		return null;
	}
	if (typeof eventItem === "string") {
		try {
			return JSON.parse(eventItem);
		} catch {
			return null;
		}
	}
	if (typeof eventItem === "object") {
		return eventItem;
	}
	return null;
};

const _getMergedStreamSections = (msg) => {
	if (!msg || msg.role !== "assistant") {
		return {
			reasoning: "",
			answer: "",
		};
	}
	if (msg.extra && typeof msg.extra === "object") {
		const cachedReasoning =
			typeof msg.extra.stream_reasoning_text === "string"
				? msg.extra.stream_reasoning_text
				: "";
		const cachedAnswer =
			typeof msg.extra.stream_answer_text === "string"
				? msg.extra.stream_answer_text
				: "";
		if (cachedReasoning || cachedAnswer) {
			return {
				reasoning: cachedReasoning.trim(),
				answer: cachedAnswer.trim(),
			};
		}
	}
	const eventLog = Array.isArray(msg.stream_event_log)
		? msg.stream_event_log
		: [];
	const fallbackEvent = _buildRawStreamText(msg);
	const streamItems =
		eventLog.length > 0 ? eventLog : fallbackEvent ? [fallbackEvent] : [];
	if (streamItems.length === 0) {
		return {
			reasoning: "",
			answer: "",
		};
	}
	let reasoningText = "";
	let answerText = "";
	streamItems.forEach((item) => {
		const eventData = _normalizeStreamEventData(item);
		if (!eventData || typeof eventData !== "object") {
			return;
		}
		const reasoning =
			typeof eventData.reasoning === "string" ? eventData.reasoning : "";
		const content =
			typeof eventData.content === "string" ? eventData.content : "";
		const isStageReasoning =
			(reasoning.startsWith("阶段流：") || reasoning.startsWith("阶段：")) &&
			eventData.metadata &&
			typeof eventData.metadata === "object" &&
			eventData.metadata.stream_stage === "reasoning";
		if (reasoning && !isStageReasoning) {
			reasoningText += reasoning;
		}
		if (content) {
			answerText += content;
		}
	});
	return {
		reasoning: reasoningText.trim(),
		answer: answerText.trim(),
	};
};

const liveStreamingText = computed(() => {
	if (!isSending.value) {
		return "";
	}
	const assistantMessages = messages.value.filter(
		(item) => item && item.role === "assistant",
	);
	if (assistantMessages.length === 0) {
		return "阶段流：正在准备请求...";
	}
	const latestAssistantMessage =
		assistantMessages[assistantMessages.length - 1];
	const mergedSections = _getMergedStreamSections(latestAssistantMessage);
	if (mergedSections.answer) {
		return mergedSections.answer;
	}
	const thinkingText = _extractThinkingText(latestAssistantMessage.content);
	if (thinkingText) {
		return "阶段流：正在思考中...";
	}
	const stageText = _buildStreamStageText(latestAssistantMessage);
	if (stageText) {
		return stageText;
	}
	return "阶段流：正在思考中...";
});

const _buildStreamStageColor = (msg) => {
	if (!msg || msg.role !== "assistant" || !msg.extra) {
		return "gray";
	}
	const stage = msg.extra.stream_stage;
	const stageColorMap = {
		routing: "gray",
		reasoning: "orangered",
		final_answer: "green",
	};
	return stageColorMap[stage] || "gray";
};

// New Helper: Format file size
const _formatSize = (bytes) => {
	if (bytes === 0) return "0 B";
	const k = 1024;
	const sizes = ["B", "KB", "MB", "GB", "TB"];
	const i = Math.floor(Math.log(bytes) / Math.log(k));
	return `${parseFloat((bytes / k ** i).toFixed(2))} ${sizes[i]}`;
};

// Define methods for downloading and previewing
const _downloadAttachment = (uuid, filename) => {
	const url = `${import.meta.env.VITE_API_BASE_URL || "/api/v1"}/attachments/${uuid}/download`;
	const link = document.createElement("a");
	link.href = url;
	link.download = filename || "download";
	document.body.appendChild(link);
	link.click();
	document.body.removeChild(link);
};

const _getPreviewUrl = (uuid) => {
	return `${import.meta.env.VITE_API_BASE_URL || "/api/v1"}/attachments/${uuid}/preview`;
};

// Computed property to check if there are pending uploads
const hasPendingUploads = computed(() => {
	return uploadedAttachments.value.some((item) => item.status === "uploading");
});

const _customUpload = async (option) => {
	const { fileItem } = option;
	const file = fileItem.file;

	// Check size (50MB)
	if (file.size > 50 * 1024 * 1024) {
		Message.error(`File ${file.name} exceeds 50MB`);
		return;
	}

	// Check max count (e.g. 9)
	if (uploadedAttachments.value.length >= 9) {
		Message.error("Max 9 attachments allowed");
		return;
	}

	// Create temp item
	const tempId = Date.now() + Math.random();
	const attachmentItem = {
		id: tempId,
		file: file,
		name: file.name,
		type: file.type,
		status: "uploading",
		progress: 0,
		url: URL.createObjectURL(file), // Local preview
		attachmentId: null,
	};

	uploadedAttachments.value.push(attachmentItem);

	try {
		const formData = new FormData();
		formData.append("file", file);
		if (currentSessionId.value) {
			formData.append("session_id", currentSessionId.value);
		}

		// Call API with progress monitoring
		const response = await uploadAttachment(formData, {
			onUploadProgress: (progressEvent) => {
				const percentCompleted = Math.round(
					(progressEvent.loaded * 100) / progressEvent.total,
				);
				const idx = uploadedAttachments.value.findIndex(
					(item) => item.id === tempId,
				);
				if (idx !== -1) {
					uploadedAttachments.value[idx].progress = percentCompleted / 100; // a-progress uses 0-1
				}
			},
		});

		// Update item with success
		const idx = uploadedAttachments.value.findIndex(
			(item) => item.id === tempId,
		);
		if (idx !== -1) {
			uploadedAttachments.value[idx].status = "success";
			uploadedAttachments.value[idx].progress = 1;
			uploadedAttachments.value[idx].attachmentId = response.uuid; // Assuming response has uuid
			// Update URL to remote if needed, but local blob is fine for preview
		}
	} catch (error) {
		console.error("Upload failed", error);
		const idx = uploadedAttachments.value.findIndex(
			(item) => item.id === tempId,
		);
		if (idx !== -1) {
			uploadedAttachments.value[idx].status = "error";
			uploadedAttachments.value[idx].error = error.message;
			Message.error(`Failed to upload ${file.name}`);
		}
	}
};

const _removeAttachment = (index) => {
	uploadedAttachments.value.splice(index, 1);
};

const _handleEnterKey = (e) => {
	if (!e.shiftKey) {
		handleSend();
	}
};

const handleSend = async () => {
	if (
		(!inputContent.value.trim() && uploadedAttachments.value.length === 0) ||
		hasPendingUploads.value
	)
		return;

	if (!currentSessionId.value) {
		await chatStore.createNewSession();
	}

	const content = inputContent.value;

	// Filter out failed uploads
	const validAttachments = uploadedAttachments.value.filter(
		(item) => item.status === "success",
	);

	// Extract attachment UUIDs and full objects
	const attachmentIds = validAttachments.map((item) => item.attachmentId);
	const attachmentObjs = validAttachments.map((item) => ({
		uuid: item.attachmentId,
		original_name: item.name,
		size: item.file.size,
		mime_type: item.type,
		created_at: new Date().toISOString(),
	}));

	// Legacy support: extract images as base64 strings if needed?
	// Current backend logic handles attachments via UUID, so we send empty images list unless we want to bypass attachment logic.
	// However, the backend logic I saw *processes* attachments.
	// BUT, the frontend `sendMessage` signature is `(content, images, attachments, extra)`.
	// I'll send images as empty list and everything as attachments.
	const images = [];

	const extra = {
		ignore_history: ignoreHistory.value,
		attachment_objs: attachmentObjs,
		stream_options: {
			stage_progress_enabled:
				streamDisplayConfig.value.showStageProgressText !== false,
			stage_tag_enabled: streamDisplayConfig.value.showStageTag !== false,
			raw_stream_enabled: streamDisplayConfig.value.showRawStreamData !== false,
		},
	};
	if (selectedPurpose.value && selectedPurpose.value !== "general") {
		extra.purpose = selectedPurpose.value;
	}

	inputContent.value = "";
	uploadedAttachments.value = [];

	await chatStore.sendMessage(content, images, attachmentIds, extra);
};

// ... (keep existing action handlers)
const _handleRegenerate = async (messageId) => {
	const msgIndex = messages.value.findIndex((m) => m.id === messageId);
	if (msgIndex === -1) return;

	let lastUserMsg = null;
	for (let i = msgIndex - 1; i >= 0; i--) {
		if (messages.value[i].role === "user") {
			lastUserMsg = messages.value[i];
			break;
		}
	}

	if (lastUserMsg) {
		messages.value.splice(msgIndex, messages.value.length - msgIndex);
		// Pass empty attachments for regenerate? Or preserve?
		// Ideally we should preserve, but for now simplest is to just re-send content.
		// If the original message had attachments, we might need to retrieve them.
		// But `sendMessage` expects new uploads or existing IDs.
		// `lastUserMsg` has `attachments` (list of UUIDs).
		await chatStore.sendMessage(
			lastUserMsg.content,
			lastUserMsg.images || [],
			lastUserMsg.attachments || [],
			lastUserMsg.extra,
		);
	}
};

const _handleFeedback = async (data) => {
	try {
		await updateMessageFeedback(data.messageId, data.type);
	} catch (_e) {
		Message.error("反馈失败");
	}
};

const _handleShare = async () => {
	if (!currentSessionId.value) return;
	try {
		const res = await shareSession(currentSessionId.value);
		if (res.share_id) {
			const shareUrl = `${window.location.origin}/share/${res.share_id}`;
			navigator.clipboard.writeText(shareUrl).then(() => {
				Message.success("Link copied to clipboard");
			});
		}
	} catch (_e) {
		Message.error("Share failed");
	}
};

const _handleFavorite = async (data) => {
	try {
		await updateMessageFavorite(data.messageId, data.isFavorite);
		const msg = messages.value.find((m) => m.id === data.messageId);
		if (msg) msg.is_favorite = data.isFavorite;
	} catch (_e) {
		Message.error("Favorite failed");
	}
};
</script>

<style scoped>
/* ... existing styles ... */
.home-page {
  height: 100vh;
  display: flex;
  flex-direction: column;
  background-color: var(--color-bg-1);
}

.chat-header {
    padding: 16px;
    border-bottom: 1px solid var(--color-border);
    display: flex;
    justify-content: center;
    gap: 12px;
}

.stream-setting-panel {
  min-width: 220px;
}

.stream-setting-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 6px 0;
}

.stream-loading {
  display: inline-flex;
  align-items: center;
  gap: 0.5rem;
}

.stream-loading-text {
  color: var(--color-text-2);
}

.raw-stream-block {
  margin-top: 0.5rem;
  padding: 0.5rem;
  border-radius: 6px;
  background-color: var(--color-fill-2);
  color: var(--color-text-3);
  font-size: 12px;
  line-height: 1.5;
  white-space: pre-wrap;
  word-break: break-all;
}

.chat-container {
  flex: 1;
  overflow-y: auto;
  padding: 20px;
  display: flex;
  flex-direction: column;
}

.empty-state {
    flex: 1;
    display: flex;
    align-items: center;
    justify-content: center;
}
.welcome-text {
    font-size: 24px;
    font-weight: bold;
    color: var(--color-text-2);
}

.messages {
    max-width: 800px;
    margin: 0 auto;
    width: 100%;
}

.message-wrapper {
    display: flex;
    margin-bottom: 24px;
    gap: 12px;
}
.message-wrapper.user {
    flex-direction: row-reverse;
}
.message-wrapper.user .avatar {
    display: none;
}
.message-wrapper.assistant .avatar {
    margin-top: 4px;
}

.bubble {
    padding: 12px 16px;
    border-radius: 8px;
    font-size: 16px;
    line-height: 1.6;
}
.message-wrapper.assistant .bubble {
    background-color: transparent;
    padding: 4px 0;
    color: var(--color-text-1);
}
.message-wrapper.user .bubble {
    background-color: var(--color-fill-2);
    color: var(--color-text-1);
    border-radius: 12px;
}

.message-attachments {
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
    margin-top: 8px;
}

.message-attachments-container {
    display: flex;
    flex-direction: column;
    gap: 8px;
    margin-top: 12px;
}

.attachment-card {
    display: flex;
    align-items: center;
    background-color: var(--color-bg-2);
    border: 1px solid var(--color-border);
    border-radius: 8px;
    padding: 12px;
    width: 320px;
    box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05);
    transition: all 0.2s;
}

.attachment-card:hover {
    box-shadow: 0 4px 8px rgba(0, 0, 0, 0.1);
}

.attachment-icon {
    display: flex;
    align-items: center;
    justify-content: center;
    margin-right: 12px;
    background-color: var(--color-fill-2);
    border-radius: 8px;
    padding: 8px;
}

.attachment-info {
    flex: 1;
    min-width: 0;
    display: flex;
    flex-direction: column;
    justify-content: center;
}

.attachment-name {
    font-size: 14px;
    font-weight: 500;
    color: var(--color-text-1);
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
    margin-bottom: 4px;
}

.attachment-meta {
    font-size: 12px;
    color: var(--color-text-3);
    display: flex;
    align-items: center;
}

.attachment-actions {
    margin-left: 8px;
}

.attachment-chip {
    display: inline-flex;
    align-items: center;
    gap: 4px;
    padding: 4px 12px;
    background-color: var(--color-fill-2);
    border: 1px solid var(--color-border);
    border-radius: 16px;
    font-size: 12px;
    color: var(--color-text-1);
    text-decoration: none;
    transition: all 0.2s;
}

.attachment-chip:hover {
    background-color: var(--color-fill-3);
    border-color: rgb(var(--primary-6));
    color: rgb(var(--primary-6));
}

.input-area-wrapper {
    padding: 20px;
    border-top: 1px solid var(--color-border);
    display: flex;
    justify-content: center;
}
.input-card {
    width: 100%;
    max-width: 800px;
    background-color: var(--color-bg-2);
    border: 1px solid var(--color-border-2);
    border-radius: 16px;
    padding: 12px 16px;
    display: flex;
    flex-direction: column;
    gap: 8px;
    box-shadow: 0 4px 12px rgba(0,0,0,0.05);
    transition: border-color 0.2s;
}

.input-card:focus-within {
    border-color: rgb(var(--primary-5));
    box-shadow: 0 4px 12px rgba(var(--primary-5), 0.1);
}

.attachment-preview-area {
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
    margin-bottom: 8px;
    padding: 8px;
    background-color: var(--color-fill-1);
    border-radius: 8px;
}

.attachment-preview-item {
    position: relative;
    width: 160px;
    height: 60px;
    background-color: var(--color-bg-1);
    border: 1px solid var(--color-border);
    border-radius: 6px;
    display: flex;
    align-items: center;
    padding: 4px;
    overflow: hidden;
}
.attachment-preview-item.error {
    border-color: rgb(var(--danger-6));
}

.preview-content {
    display: flex;
    align-items: center;
    gap: 8px;
    width: 100%;
}

.preview-img {
    width: 40px;
    height: 40px;
    object-fit: cover;
    border-radius: 4px;
}
.file-icon {
    width: 40px;
    height: 40px;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 24px;
    color: var(--color-text-2);
    background-color: var(--color-fill-2);
    border-radius: 4px;
}

.file-info {
    flex: 1;
    overflow: hidden;
    display: flex;
    flex-direction: column;
    justify-content: center;
}
.file-name {
    font-size: 12px;
    color: var(--color-text-1);
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
}
.file-size {
    font-size: 10px;
    color: var(--color-text-3);
}

.upload-status {
    margin-right: 4px;
}

.remove-btn {
    position: absolute;
    top: 2px;
    right: 2px;
    background: rgba(0,0,0,0.5);
    color: white;
    border-radius: 50%;
    width: 16px;
    height: 16px;
    display: flex;
    align-items: center;
    justify-content: center;
    cursor: pointer;
    font-size: 10px;
    display: none; /* Show on hover */
}
.attachment-preview-item:hover .remove-btn {
    display: flex;
}

.custom-textarea :deep(.arco-textarea) {
    border: none;
    background: transparent;
    padding: 0;
    resize: none;
    box-shadow: none;
    font-size: 15px;
    line-height: 1.5;
}
.custom-textarea :deep(.arco-textarea:focus) {
    box-shadow: none;
}

.input-actions {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-top: 4px;
}
.left-actions {
    display: flex;
    align-items: center;
    gap: 12px;
}
.right-actions {
    display: flex;
    align-items: center;
}
.action-btn {
    color: var(--color-text-2);
}
.action-btn:hover {
    color: rgb(var(--primary-6));
    background-color: var(--color-fill-2);
}

.divider {
    width: 1px;
    height: 16px;
    background-color: var(--color-border);
    margin: 0 4px;
}

.shortcut-buttons {
    display: flex;
    gap: 8px;
}

.shortcut-btn {
    color: var(--color-text-2);
    font-size: 13px;
    border-radius: 6px;
}

.shortcut-btn:hover {
    background-color: var(--color-fill-2);
    color: var(--color-text-1);
}

.shortcut-arrow {
    margin-left: 4px;
    font-size: 12px;
}

.ignore-history-checkbox {
    font-size: 12px;
    color: var(--color-text-3);
}

.routing-debug {
    margin-top: 0.5rem;
}
</style>
