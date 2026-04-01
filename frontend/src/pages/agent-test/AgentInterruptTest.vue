<template>
  <div class="chat-container">
    <!-- 顶部控制栏 -->
    <div class="chat-header">
      <div class="header-left">
        <span class="title">Agent 调试控制台</span>
        <a-select v-model="currentAgent" :style="{ width: '240px' }" placeholder="选择 Agent">
          <a-option v-for="agent in agentOptions" :key="agent.value" :value="agent.value">
            {{ agent.label }}
          </a-option>
        </a-select>
        <span class="thread-info">当前会话: {{ threadId }}</span>
      </div>
      <div class="header-right">
        <a-button type="outline" @click="resetSession">
          <template #icon><icon-refresh /></template>
          清空会话
        </a-button>
      </div>
    </div>

    <!-- 消息展示区 -->
    <div class="chat-messages" ref="messageListRef">
      <div v-if="messages.length === 0" class="empty-tip">
        请在下方输入内容开始与 Agent 对话...
      </div>

      <div v-for="(msg, index) in messages" :key="index" :class="['message-wrapper', msg.role]">
        <div class="avatar">
          <a-avatar :style="{ backgroundColor: msg.role === 'user' ? '#165DFF' : (msg.role === 'system' ? '#86909c' : '#00b42a') }">
            <icon-user v-if="msg.role === 'user'" />
            <icon-info-circle v-else-if="msg.role === 'system'" />
            <icon-robot v-else />
          </a-avatar>
        </div>
        <div class="message-content">
          <div :class="['bubble', msg.type === 'tool_calls' || msg.type === 'tool_result' ? 'tool-bubble' : '']">
            <!-- 文本消息 -->
            <template v-if="msg.type === 'text'">
              {{ msg.content }}
            </template>
            <!-- 工具调用消息 -->
            <template v-else-if="msg.type === 'tool_calls'">
              <div class="tool-call-box">
                <div class="tool-title"><icon-tool /> 尝试调用工具: {{ msg.tool_name }}</div>
                <pre class="tool-code">{{ msg.tool_args }}</pre>
              </div>
            </template>
            <!-- 工具结果消息 -->
            <template v-else-if="msg.type === 'tool_result'">
              <div class="tool-result-box">
                <div class="tool-title"><icon-check-circle /> 工具执行完毕: {{ msg.tool_name }}</div>
                <pre class="tool-code">{{ msg.content }}</pre>
              </div>
            </template>
          </div>
        </div>
      </div>

      <!-- 加载中状态 -->
      <div v-if="loading" class="message-wrapper assistant">
        <div class="avatar"><a-avatar style="background-color: #00b42a"><icon-robot /></a-avatar></div>
        <div class="message-content">
          <div class="bubble"><a-spin dot /> Agent 思考中...</div>
        </div>
      </div>

      <!-- 中断等待确认卡片 -->
      <div v-if="isInterrupted" class="message-wrapper assistant">
        <div class="avatar"><a-avatar style="background-color: #00b42a"><icon-robot /></a-avatar></div>
        <div class="message-content">
          <div class="interrupt-box">
            <a-alert type="warning" title="任务已挂起 (需人工审批)">
              Agent 当前正处于 <b>{{ pendingNodes.join(', ') }}</b> 节点，准备执行敏感操作，是否允许继续？
            </a-alert>
            <div class="interrupt-actions">
              <a-space>
                <a-button type="primary" @click="handleResume(true)">同意执行</a-button>
                <a-button type="outline" status="danger" @click="handleResume(false)">拒绝操作</a-button>
              </a-space>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- 底部输入区 -->
    <div class="chat-input-area">
      <a-textarea
        v-model="inputMessage"
        placeholder="输入指令，按 Enter 发送 (Shift+Enter 换行)..."
        :auto-size="{ minRows: 2, maxRows: 5 }"
        @keydown.enter.prevent="handleKeydown"
        :disabled="loading || isInterrupted"
      />
      <a-button
        type="primary"
        class="send-btn"
        @click="handleSend"
        :disabled="!inputMessage.trim() || loading || isInterrupted"
      >
        发送 <icon-send />
      </a-button>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, nextTick } from "vue";
import { Message } from "@arco-design/web-vue";
import {
	IconUser,
	IconRobot,
	IconInfoCircle,
	IconRefresh,
	IconSend,
	IconTool,
	IconCheckCircle,
} from "@arco-design/web-vue/es/icon";
import {
	startAgent,
	getAgentStatus,
	resumeAgent,
} from "@/api/agents-interrupt";

// ========== 状态数据 ==========
const agentOptions = [
	{
		label: "综合演示 Agent (含文件/计算工具)",
		value: "comprehensive_demo_agent",
	},
	{ label: "系统专家 Agent", value: "system_expert_agent" },
	{ label: "图像处理 Agent", value: "image_agent" },
	{ label: "文本处理 Agent", value: "text_agent" },
	{ label: "数据分析 Agent", value: "data_agent" },
	{ label: "工作流协调 Agent", value: "workflow_agent" },
];

const currentAgent = ref("comprehensive_demo_agent");
const threadId = ref("thread_" + Date.now());
const messages = ref([]);
const inputMessage = ref("");
const loading = ref(false);
const isInterrupted = ref(false);
const pendingNodes = ref([]);
const messageListRef = ref(null);

// ========== 方法 ==========

/**
 * 滚动到最底部
 */
const scrollToBottom = async () => {
	await nextTick();
	if (messageListRef.value) {
		messageListRef.value.scrollTop = messageListRef.value.scrollHeight;
	}
};

/**
 * 重置会话
 */
const resetSession = () => {
	threadId.value = "thread_" + Date.now();
	messages.value = [];
	isInterrupted.value = false;
	pendingNodes.value = [];
	inputMessage.value = "";
	Message.success("会话已重置");
};

/**
 * 解析 LangGraph 返回的 messages 数组为本地 UI 格式
 */
const parseStateMessages = (rawMessages) => {
	if (!rawMessages || !Array.isArray(rawMessages)) return [];

	const parsed = [];
	for (const m of rawMessages) {
		// HumanMessage
		if (m.type === "human") {
			parsed.push({ role: "user", type: "text", content: m.content });
		}
		// AIMessage
		else if (m.type === "ai") {
			if (m.content) {
				parsed.push({ role: "assistant", type: "text", content: m.content });
			}
			if (m.tool_calls && m.tool_calls.length > 0) {
				for (const tc of m.tool_calls) {
					parsed.push({
						role: "assistant",
						type: "tool_calls",
						tool_name: tc.name,
						tool_args: JSON.stringify(tc.args, null, 2),
					});
				}
			}
		}
		// ToolMessage
		else if (m.type === "tool") {
			parsed.push({
				role: "assistant",
				type: "tool_result",
				tool_name: m.name,
				content: m.content,
			});
		}
		// SystemMessage (通常是初始 prompt，不在界面展示，除非你想调试)
	}
	return parsed;
};

/**
 * 更新界面状态
 */
const updateState = (data) => {
	if (data.state && data.state.messages) {
		messages.value = parseStateMessages(data.state.messages);
	}

	if (data.status === "interrupted") {
		isInterrupted.value = true;
		pendingNodes.value = data.pending_nodes || [];
	} else {
		isInterrupted.value = false;
		pendingNodes.value = [];
	}

	if (data.error) {
		messages.value.push({
			role: "system",
			type: "text",
			content: "执行发生错误: " + data.error,
		});
	}

	scrollToBottom();
};

/**
 * 发送消息
 */
const handleSend = async () => {
	const text = inputMessage.value.trim();
	if (!text || loading.value || isInterrupted.value) return;

	// 乐观更新 UI
	messages.value.push({ role: "user", type: "text", content: text });
	inputMessage.value = "";
	scrollToBottom();
	loading.value = true;

	try {
		const res = await startAgent({
			agent_id: currentAgent.value,
			thread_id: threadId.value,
			input_data: { messages: [["user", text]] },
		});

		const data = res.data || res;
		updateState(data);
	} catch (err) {
		const errorMsg = err.response?.data?.detail || err.message;
		Message.error("请求失败: " + errorMsg);
		messages.value.push({
			role: "system",
			type: "text",
			content: `网络请求失败: ${errorMsg}`,
		});
		scrollToBottom();
	} finally {
		loading.value = false;
	}
};

/**
 * 处理 Enter 发送
 */
const handleKeydown = (e) => {
	if (e.shiftKey) return; // Shift + Enter 换行
	handleSend();
};

/**
 * 恢复 Agent（审批中断）
 */
const handleResume = async (isApproved) => {
	loading.value = true;
	isInterrupted.value = false;

	// 添加本地提示
	messages.value.push({
		role: "system",
		type: "text",
		content: isApproved
			? "【系统】您已同意执行该操作，Agent 继续执行中..."
			: "【系统】您已拒绝该操作，Agent 将取消执行。",
	});
	scrollToBottom();

	try {
		// 构造 feedback
		// comprehensive_demo_agent 预期的是 {"requires_user_input": false} 即可继续
		const feedback = isApproved
			? { requires_user_input: false }
			: { requires_user_input: false, error: "User rejected the action." };

		const res = await resumeAgent({
			agent_id: currentAgent.value,
			thread_id: threadId.value,
			user_feedback: feedback,
		});

		const data = res.data || res;
		updateState(data);
	} catch (err) {
		const errorMsg = err.response?.data?.detail || err.message;
		Message.error("恢复执行失败: " + errorMsg);
		messages.value.push({
			role: "system",
			type: "text",
			content: `恢复请求失败: ${errorMsg}`,
		});
		isInterrupted.value = true; // 恢复 UI 状态
		scrollToBottom();
	} finally {
		loading.value = false;
	}
};
</script>

<style scoped>
.chat-container {
  display: flex;
  flex-direction: column;
  height: calc(100vh - 40px); /* 适配后台布局高度 */
  background: #f7f8fa;
  border-radius: 8px;
  overflow: hidden;
  margin: 20px;
  box-shadow: 0 4px 10px rgba(0,0,0,0.05);
}

.chat-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px 24px;
  background: #fff;
  border-bottom: 1px solid #e5e6eb;
}

.chat-header .title {
  font-size: 18px;
  font-weight: 600;
  margin-right: 16px;
  color: #1d2129;
}

.thread-info {
  margin-left: 16px;
  font-size: 12px;
  color: #86909c;
}

.chat-messages {
  flex: 1;
  padding: 24px;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.empty-tip {
  text-align: center;
  color: #86909c;
  margin-top: 100px;
  font-size: 14px;
}

.message-wrapper {
  display: flex;
  align-items: flex-start;
  gap: 12px;
  max-width: 85%;
}

.message-wrapper.user {
  align-self: flex-end;
  flex-direction: row-reverse;
}

.message-wrapper.assistant {
  align-self: flex-start;
}

.message-wrapper.system {
  align-self: center;
  max-width: 95%;
}

.bubble {
  padding: 12px 16px;
  border-radius: 8px;
  font-size: 14px;
  line-height: 1.6;
  word-wrap: break-word;
  white-space: pre-wrap;
}

.user .bubble {
  background: #165DFF;
  color: #fff;
  border-top-right-radius: 2px;
}

.assistant .bubble {
  background: #fff;
  color: #1d2129;
  border-top-left-radius: 2px;
  box-shadow: 0 2px 8px rgba(0,0,0,0.04);
}

.system .bubble {
  background: transparent;
  color: #86909c;
  font-size: 12px;
  text-align: center;
  padding: 4px 12px;
}

.tool-bubble {
  padding: 0;
  background: transparent !important;
  box-shadow: none !important;
}

.tool-call-box, .tool-result-box {
  background: #f2f3f5;
  padding: 12px 16px;
  border-radius: 8px;
  border: 1px solid #e5e6eb;
}

.tool-result-box {
  background: #e8f3ff;
  border-color: #btd1ff;
}

.tool-title {
  font-weight: 600;
  margin-bottom: 8px;
  color: #4e5969;
  display: flex;
  align-items: center;
  gap: 6px;
}

.tool-code {
  margin: 0;
  white-space: pre-wrap;
  font-family: monospace;
  font-size: 13px;
  color: #1d2129;
  background: rgba(255, 255, 255, 0.6);
  padding: 8px;
  border-radius: 4px;
}

.interrupt-box {
  background: #fff;
  padding: 16px;
  border-radius: 8px;
  box-shadow: 0 4px 12px rgba(0,0,0,0.08);
  border: 1px solid #ffe58f;
  min-width: 300px;
}

.interrupt-actions {
  margin-top: 16px;
  display: flex;
  justify-content: flex-end;
}

.chat-input-area {
  padding: 16px 24px;
  background: #fff;
  border-top: 1px solid #e5e6eb;
  display: flex;
  gap: 16px;
  align-items: flex-end;
}

.send-btn {
  height: 36px;
  padding: 0 20px;
}
</style>
