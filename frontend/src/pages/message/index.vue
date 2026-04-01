<!--
 * @Author: Message Center
 * @Date: 2026-03-16
 * @Description: 消息中心页面，支持查看、搜索、过滤和AI总结
-->
<template>
  <div class="p-4">
    <a-card title="消息中心" :bordered="false">
      <!-- 筛选栏 -->
      <a-row :gutter="16" class="mb-4">
        <a-col :span="6">
          <a-select
            v-model="filters.channel_id"
            placeholder="选择渠道"
            allow-clear
            :loading="channelsLoading"
          >
            <a-option
              v-for="channel in channels"
              :key="channel.id"
              :value="channel.id"
              :label="channel.name"
            />
          </a-select>
        </a-col>
        <a-col :span="8">
          <a-range-picker
            v-model="filters.dateRange"
            show-time
            format="YYYY-MM-DD HH:mm:ss"
            style="width: 100%"
          />
        </a-col>
        <a-col :span="6">
          <a-input
            v-model="filters.keyword"
            placeholder="搜索消息内容"
            allow-clear
            @press-enter="handleSearch"
          />
        </a-col>
        <a-col :span="4" class="text-right">
          <a-space>
            <a-button type="primary" @click="handleSearch">
              <template #icon><icon-search /></template>
              查询
            </a-button>
            <a-button @click="handleReset">
              <template #icon><icon-refresh /></template>
              重置
            </a-button>
          </a-space>
        </a-col>
      </a-row>

      <!-- 操作栏 -->
      <div class="mb-4 flex justify-between">
        <a-space>
          <a-button
            type="primary"
            status="success"
            :disabled="selectedKeys.length === 0"
            @click="handleSummarySelected"
          >
            <template #icon><icon-robot /></template>
            AI 总结选中 ({{ selectedKeys.length }})
          </a-button>
          <a-button
            type="outline"
            status="warning"
            @click="handleSummaryQuery"
          >
            <template #icon><icon-robot /></template>
            AI 总结当前查询结果 (前50条)
          </a-button>
        </a-space>

        <a-radio-group v-model="filters.status" type="button" @change="handleSearch">
          <a-radio value="">全部</a-radio>
          <a-radio value="success">成功</a-radio>
          <a-radio value="failed">失败</a-radio>
          <a-radio value="pending">发送中</a-radio>
        </a-radio-group>
      </div>

      <!-- 消息列表 -->
      <a-table
        row-key="id"
        :data="messages"
        :loading="loading"
        :pagination="pagination"
        :row-selection="rowSelection"
        v-model:selected-keys="selectedKeys"
        @page-change="handlePageChange"
        @page-size-change="handlePageSizeChange"
      >
        <template #columns>
          <a-table-column title="时间" data-index="created_at" :width="180">
            <template #cell="{ record }">
              {{ formatDate(record.created_at) }}
            </template>
          </a-table-column>
          <a-table-column title="渠道" data-index="channel_id" :width="150">
            <template #cell="{ record }">
              {{ getChannelName(record.channel_id) }}
            </template>
          </a-table-column>
          <a-table-column title="内容" data-index="content">
            <template #cell="{ record }">
              <div class="truncate-content" :title="record.content">
                {{ record.content.length > 50 ? record.content.slice(0, 50) + '...' : record.content }}
              </div>
            </template>
          </a-table-column>
          <a-table-column title="状态" data-index="status" :width="100">
            <template #cell="{ record }">
              <a-tag :color="getStatusColor(record.status)">
                {{ record.status }}
              </a-tag>
            </template>
          </a-table-column>
          <a-table-column title="操作" :width="100" align="center">
            <template #cell="{ record }">
              <a-button type="text" size="small" @click="handleDetail(record)">
                查看
              </a-button>
            </template>
          </a-table-column>
        </template>
      </a-table>
    </a-card>

    <!-- 详情弹窗 -->
    <a-modal v-model:visible="detailVisible" title="消息详情" width="600px" :footer="false">
      <div v-if="currentMessage">
        <a-descriptions :column="1" bordered>
          <a-descriptions-item label="发送时间">
            {{ formatDate(currentMessage.created_at) }}
          </a-descriptions-item>
          <a-descriptions-item label="渠道">
            {{ getChannelName(currentMessage.channel_id) }}
          </a-descriptions-item>
          <a-descriptions-item label="状态">
            <a-tag :color="getStatusColor(currentMessage.status)">
              {{ currentMessage.status }}
            </a-tag>
          </a-descriptions-item>
          <a-descriptions-item label="消息内容">
            <div class="whitespace-pre-wrap p-2 bg-gray-50 rounded max-h-60 overflow-y-auto">
              {{ currentMessage.content }}
            </div>
          </a-descriptions-item>
          <a-descriptions-item label="发送结果" v-if="currentMessage.result">
            <div class="whitespace-pre-wrap p-2 bg-gray-50 rounded max-h-40 overflow-y-auto text-xs">
              {{ currentMessage.result }}
            </div>
          </a-descriptions-item>
        </a-descriptions>
      </div>
    </a-modal>

    <!-- AI 总结弹窗 -->
    <a-modal
      v-model:visible="summaryVisible"
      title="AI 消息总结"
      width="600px"
      :footer="false"
      :mask-closable="false"
    >
      <div class="summary-container">
        <div v-if="summaryLoading && !summaryContent" class="text-center py-4">
          <a-spin tip="正在生成总结..." />
        </div>
        <div v-else class="markdown-body p-4 bg-gray-50 rounded min-h-[200px]">
          <div v-html="renderMarkdown(summaryContent)"></div>
        </div>
      </div>
    </a-modal>
  </div>
</template>

<script setup>
import { Message } from "@arco-design/web-vue";
import dayjs from "dayjs";
import MarkdownIt from "markdown-it";
import { computed, onMounted, reactive, ref } from "vue";
import { useLoadingStore } from "@/store/loading";
import { getChannels, getMessages } from "../../api/channel";
import { createSession, getModels, sendMessageStream } from "../../api/chat";

const md = new MarkdownIt();
const loadingStore = useLoadingStore();

// ========== 状态定义 ==========
const messages = ref([]);
const channels = ref([]);
const total = ref(0);
const selectedKeys = ref([]);

const filters = reactive({
	channel_id: "",
	keyword: "",
	dateRange: [],
	status: "",
});

const pagination = reactive({
	current: 1,
	pageSize: 10,
	total: 0,
	showTotal: true,
	showPageSize: true,
});

const rowSelection = {
	type: "checkbox",
	showCheckedAll: true,
};

// 详情相关
const detailVisible = ref(false);
const currentMessage = ref(null);

// 总结相关
const summaryVisible = ref(false);
const summaryContent = ref("");

const loading = computed(() => loadingStore.isLoading("message-search"));
const channelsLoading = computed(() => loadingStore.isLoading("channel-list"));
const summaryLoading = computed(() =>
	loadingStore.isLoading("message-summary"),
);

// ========== 初始化 ==========
onMounted(async () => {
	await fetchChannels();
	handleSearch();
});

// ========== 业务逻辑 ==========

// 获取渠道列表
const fetchChannels = async () => {
	try {
		const data = await getChannels({ limit: 100 });
		
		// 过滤渠道：对于 qqbot 类型的渠道，仅保留一个有效的
		const qqbotChannels = data.filter((c) => c.type === "qqbot" && c.is_active);
		const validQqbot = qqbotChannels.length > 0 ? qqbotChannels[0] : null;
		
		channels.value = data.filter((c) => {
			if (c.type === "qqbot") {
				return validQqbot && c.id === validQqbot.id;
			}
			return true;
		});
	} catch (error) {
		console.error("Failed to fetch channels:", error);
	}
};

// 获取消息列表
const fetchMessages = async () => {
	try {
		const params = {
			skip: (pagination.current - 1) * pagination.pageSize,
			limit: pagination.pageSize,
			channel_id: filters.channel_id || undefined,
			keyword: filters.keyword || undefined,
			status: filters.status || undefined,
		};

		if (filters.dateRange && filters.dateRange.length === 2) {
			params.start_date = filters.dateRange[0];
			params.end_date = filters.dateRange[1];
		}

		const { items, total: totalCount } = await getMessages(params);
		messages.value = items;
		pagination.total = totalCount;
		total.value = totalCount;
	} catch (error) {
		console.error("Failed to fetch messages:", error);
	}
};

// 搜索与重置
const handleSearch = () => {
	pagination.current = 1;
	fetchMessages();
};

const handleReset = () => {
	filters.channel_id = "";
	filters.keyword = "";
	filters.dateRange = [];
	filters.status = "";
	handleSearch();
};

// 分页处理
const handlePageChange = (page) => {
	pagination.current = page;
	fetchMessages();
};

const handlePageSizeChange = (pageSize) => {
	pagination.pageSize = pageSize;
	pagination.current = 1;
	fetchMessages();
};

// 详情查看
const handleDetail = (record) => {
	currentMessage.value = record;
	detailVisible.value = true;
};

// 辅助函数
const getChannelName = (id) => {
	const channel = channels.value.find((c) => c.id === id);
	return channel ? channel.name : id;
};

const formatDate = (dateStr) => {
	return dayjs(dateStr).format("YYYY-MM-DD HH:mm:ss");
};

const getStatusColor = (status) => {
	const map = {
		success: "green",
		failed: "red",
		pending: "orange",
	};
	return map[status] || "gray";
};

const renderMarkdown = (text) => {
	return md.render(text || "");
};

// ========== AI 总结逻辑 ==========

const getAIModel = async () => {
	try {
		const models = await getModels();
		if (models && models.length > 0) {
			// 优先选择非 embedding 模型，这里简单取第一个
			// 实际逻辑可能需要根据 model_config 过滤
			return models[0].id;
		}
		return "llama3"; // 默认 fallback
	} catch (_e) {
		return "llama3";
	}
};

const performSummary = async (messagesToSummarize) => {
	if (!messagesToSummarize || messagesToSummarize.length === 0) {
		Message.warning("没有可总结的消息");
		return;
	}

	summaryVisible.value = true;
	summaryContent.value = "";
	loadingStore.startLoading("message-summary");

	try {
		// 1. 准备 Prompt
		const contentText = messagesToSummarize
			.map(
				(msg, index) =>
					`${index + 1}. [${formatDate(msg.created_at)}] ${getChannelName(msg.channel_id)}: ${msg.content}`,
			)
			.join("\n");

		const prompt = `请针对以下 ${messagesToSummarize.length} 条消息进行总结，提取关键信息：\n\n${contentText}`;

		// 2. 创建会话
		const session = await createSession();
		const sessionId = session.id;

		// 3. 获取模型
		const modelId = await getAIModel();

		// 4. 发送请求并流式接收
		await sendMessageStream(sessionId, prompt, modelId, [], (chunk) => {
			summaryContent.value += chunk;
		});
	} catch (error) {
		console.error("Summary failed:", error);
		summaryContent.value += `\n\n(总结生成失败: ${error.message})`;
	} finally {
		loadingStore.stopLoading("message-summary");
	}
};

// 总结选中
const handleSummarySelected = () => {
	const selectedMessages = messages.value.filter((msg) =>
		selectedKeys.value.includes(msg.id),
	);
	performSummary(selectedMessages);
};

// 总结查询结果
const handleSummaryQuery = async () => {
	// 重新获取前50条符合条件的消息
	const params = {
		skip: 0,
		limit: 50,
		channel_id: filters.channel_id || undefined,
		keyword: filters.keyword || undefined,
		status: filters.status || undefined,
	};

	if (filters.dateRange && filters.dateRange.length === 2) {
		params.start_date = filters.dateRange[0];
		params.end_date = filters.dateRange[1];
	}

	try {
		const { items } = await getMessages(params);
		performSummary(items);
	} catch (_error) {
		Message.error("获取查询结果失败");
	}
};
</script>

<style scoped>
.truncate-content {
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  max-width: 400px;
}
.markdown-body {
  font-size: 14px;
  line-height: 1.6;
}
</style>
