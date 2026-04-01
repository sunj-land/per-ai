<template>
  <div class="rss-quality-panel">
    <a-row :gutter="16">
      <a-col :span="24" :xl="12">
        <a-card title="评分规则配置" class="panel-card">
          <a-space direction="vertical" fill size="large">
            <a-input
              v-model="configForm.name"
              placeholder="请输入评分规则名称"
            />

            <div
              v-for="dimension in dimensionDefinitions"
              :key="dimension.key"
              class="weight-row"
            >
              <div class="weight-header">
                <div>
                  <div class="weight-title">{{ dimension.label }}</div>
                  <div class="weight-desc">{{ dimension.description }}</div>
                </div>
                <a-tag color="arcoblue">
                  {{ formatPercent(configForm.weights[dimension.key]) }}
                </a-tag>
              </div>
              <div class="weight-control">
                <a-slider
                  v-model="configForm.weights[dimension.key]"
                  :min="0"
                  :max="1"
                  :step="0.01"
                />
                <a-input-number
                  v-model="configForm.weights[dimension.key]"
                  :min="0"
                  :max="1"
                  :step="0.01"
                  mode="button"
                />
              </div>
            </div>

            <a-divider>评分阈值</a-divider>

            <a-row :gutter="12">
              <a-col :span="8">
                <a-input-number
                  v-model="configForm.thresholds.excellent"
                  :min="0"
                  :max="100"
                  placeholder="优秀阈值"
                  class="full-width"
                />
              </a-col>
              <a-col :span="8">
                <a-input-number
                  v-model="configForm.thresholds.good"
                  :min="0"
                  :max="100"
                  placeholder="良好阈值"
                  class="full-width"
                />
              </a-col>
              <a-col :span="8">
                <a-input-number
                  v-model="configForm.thresholds.review"
                  :min="0"
                  :max="100"
                  placeholder="复核阈值"
                  class="full-width"
                />
              </a-col>
            </a-row>

            <a-divider>算法参数</a-divider>

            <a-row :gutter="12">
              <a-col :span="12">
                <a-input-number
                  v-model="configForm.settings.originality.comparison_window"
                  :min="5"
                  :max="100"
                  class="full-width"
                  placeholder="重复检测样本窗口"
                />
              </a-col>
              <a-col :span="12">
                <a-input-number
                  v-model="configForm.settings.timeliness.fresh_hours"
                  :min="1"
                  :max="240"
                  class="full-width"
                  placeholder="高时效窗口(小时)"
                />
              </a-col>
            </a-row>

            <a-space>
              <a-button type="primary" :loading="configLoading" @click="handleSaveConfig">
                保存规则
              </a-button>
              <a-button @click="handleRestoreDefault">恢复默认</a-button>
            </a-space>
          </a-space>
        </a-card>
      </a-col>

      <a-col :span="24" :xl="12">
        <a-card title="批量评分任务" class="panel-card">
          <a-space direction="vertical" fill size="large">
            <a-select
              v-model="scoreForm.feedId"
              allow-clear
              placeholder="选择 RSS 订阅源"
            >
              <a-option
                v-for="feed in feeds"
                :key="feed.id"
                :value="feed.id"
              >
                {{ feed.title || feed.url }}
              </a-option>
            </a-select>

            <a-textarea
              v-model="scoreForm.articleIdsText"
              :auto-size="{ minRows: 3, maxRows: 5 }"
              placeholder="输入文章 ID，多个请用逗号分隔；为空时按订阅源批量评分"
            />

            <a-row :gutter="12">
              <a-col :span="12">
                <a-input-number
                  v-model="scoreForm.limit"
                  :min="1"
                  :max="200"
                  class="full-width"
                  placeholder="批量数量"
                />
              </a-col>
              <a-col :span="12">
                <a-input-number
                  v-model="scoreForm.concurrency"
                  :min="1"
                  :max="20"
                  class="full-width"
                  placeholder="并发数"
                />
              </a-col>
            </a-row>

            <a-space>
              <a-button type="primary" :loading="scoreLoading" @click="handleScore">
                开始评分
              </a-button>
              <a-button @click="fetchResults">刷新结果</a-button>
              <a-button @click="fetchLogs">刷新日志</a-button>
            </a-space>

            <a-row v-if="latestSummary" :gutter="12">
              <a-col :span="8">
                <a-statistic title="批量总数" :value="latestSummary.total" />
              </a-col>
              <a-col :span="8">
                <a-statistic title="成功数" :value="latestSummary.success" />
              </a-col>
              <a-col :span="8">
                <a-statistic title="平均分" :value="latestSummary.averageScore" />
              </a-col>
            </a-row>
          </a-space>
        </a-card>

        <a-card title="评分日志" class="panel-card logs-card">
          <a-empty v-if="logs.length === 0" description="暂无评分日志" />
          <a-space v-else direction="vertical" fill>
            <div
              v-for="log in logs"
              :key="log.id"
              class="log-item"
            >
              <div class="log-meta">
                <a-tag :color="getLogColor(log.level)">{{ log.level }}</a-tag>
                <span>{{ formatDate(log.createdAt) }}</span>
              </div>
              <div class="log-message">{{ log.message }}</div>
            </div>
          </a-space>
        </a-card>
      </a-col>
    </a-row>

    <a-card title="评分结果筛选" class="panel-card">
      <a-space wrap size="medium">
        <a-input-number
          v-model="filterForm.minScore"
          :min="0"
          :max="100"
          placeholder="最低分"
        />
        <a-input-number
          v-model="filterForm.maxScore"
          :min="0"
          :max="100"
          placeholder="最高分"
        />
        <a-select
          v-model="filterForm.feedId"
          allow-clear
          placeholder="按订阅源筛选"
          style="width: 240px;"
        >
          <a-option
            v-for="feed in feeds"
            :key="feed.id"
            :value="feed.id"
          >
            {{ feed.title || feed.url }}
          </a-option>
        </a-select>
        <a-input
          v-model="filterForm.batchId"
          allow-clear
          placeholder="按批次 ID 筛选"
          style="width: 240px;"
        />
        <a-button type="primary" :loading="resultLoading" @click="fetchResults">
          查询结果
        </a-button>
      </a-space>

      <a-table
        :data="results"
        :loading="resultLoading"
        :pagination="{ pageSize: 8 }"
        row-key="id"
        class="result-table"
      >
        <template #columns>
          <a-table-column title="文章" :width="320">
            <template #cell="{ record }">
              <div class="article-cell">
                <div class="article-title">{{ record.articleTitle }}</div>
                <div class="article-subtitle">{{ record.feedTitle || '未绑定订阅源' }}</div>
              </div>
            </template>
          </a-table-column>
          <a-table-column title="综合评分" data-index="overallScore" :width="120" />
          <a-table-column title="等级" :width="110">
            <template #cell="{ record }">
              <a-tag :color="getGradeColor(record.grade)">{{ record.grade }}</a-tag>
            </template>
          </a-table-column>
          <a-table-column title="原创性" :width="110">
            <template #cell="{ record }">{{ record.dimensions.originality }}</template>
          </a-table-column>
          <a-table-column title="信息价值" :width="110">
            <template #cell="{ record }">{{ record.dimensions.information_value }}</template>
          </a-table-column>
          <a-table-column title="写作质量" :width="110">
            <template #cell="{ record }">{{ record.dimensions.writing_quality }}</template>
          </a-table-column>
          <a-table-column title="互动潜力" :width="110">
            <template #cell="{ record }">{{ record.dimensions.interaction_potential }}</template>
          </a-table-column>
          <a-table-column title="时效性" :width="100">
            <template #cell="{ record }">{{ record.dimensions.timeliness }}</template>
          </a-table-column>
          <a-table-column title="操作" :width="100" fixed="right">
            <template #cell="{ record }">
              <a-button type="text" @click="openResultDetail(record)">查看报告</a-button>
            </template>
          </a-table-column>
        </template>
      </a-table>
    </a-card>

    <a-drawer
      v-model:visible="detailVisible"
      title="详细评分报告"
      width="640px"
      unmount-on-close
    >
      <div v-if="selectedResult" class="detail-content">
        <a-descriptions :column="1" bordered>
          <a-descriptions-item label="文章标题">
            {{ selectedResult.articleTitle }}
          </a-descriptions-item>
          <a-descriptions-item label="综合评分">
            {{ selectedResult.overallScore }}
          </a-descriptions-item>
          <a-descriptions-item label="等级">
            {{ selectedResult.grade }}
          </a-descriptions-item>
          <a-descriptions-item label="批次">
            {{ selectedResult.batchId }}
          </a-descriptions-item>
        </a-descriptions>

        <div
          v-for="dimension in dimensionDefinitions"
          :key="dimension.key"
          class="detail-dimension"
        >
          <div class="detail-title">
            <span>{{ dimension.label }}</span>
            <span>{{ selectedResult.report.dimensions[dimension.key].score }}</span>
          </div>
          <a-progress
            :percent="selectedResult.report.dimensions[dimension.key].score"
            :show-text="false"
          />
          <div class="detail-reasons">
            {{ selectedResult.report.dimensions[dimension.key].reasons.join('；') }}
          </div>
        </div>
      </div>
    </a-drawer>
  </div>
</template>

<script setup>
import { Message } from "@arco-design/web-vue";
import { computed, onMounted, reactive, ref } from "vue";
import {
	getDefaultRssQualityConfig,
	getRssQualityConfig,
	getRssQualityLogs,
	getRssQualityResults,
	scoreRssArticles,
	updateRssQualityConfig,
} from "@/api/agent-center";
import { getFeeds } from "@/api/rss";
import { useLoadingStore } from "@/store/loading";

const dimensionDefinitions = [
	{
		key: "originality",
		label: "内容原创性",
		description: "检测重复率与近似文本相似度",
	},
	{
		key: "information_value",
		label: "信息价值度",
		description: "分析关键词权重与行业相关性",
	},
	{
		key: "writing_quality",
		label: "写作质量",
		description: "评估语法错误率与段落结构合理性",
	},
	{
		key: "interaction_potential",
		label: "用户互动潜力",
		description: "预测标题吸引力与话题热度",
	},
	{
		key: "timeliness",
		label: "时效性",
		description: "衡量发布时间与内容新鲜度",
	},
];

const loadingStore = useLoadingStore();
const feeds = ref([]);
const results = ref([]);
const logs = ref([]);
const latestSummary = ref(null);
const latestBatchId = ref("");
const detailVisible = ref(false);
const selectedResult = ref(null);

const configForm = reactive(createDefaultConfig());
const scoreForm = reactive({
	feedId: undefined,
	articleIdsText: "",
	limit: 20,
	concurrency: 5,
});
const filterForm = reactive({
	minScore: undefined,
	maxScore: undefined,
	feedId: undefined,
	batchId: "",
});

const configLoading = computed(
	() =>
		loadingStore.isLoading("rss-quality-config") ||
		loadingStore.isLoading("rss-quality-config-save"),
);
const scoreLoading = computed(() =>
	loadingStore.isLoading("rss-quality-score"),
);
const resultLoading = computed(() =>
	loadingStore.isLoading("rss-quality-results"),
);

function createDefaultConfig() {
	return {
		name: "",
		weights: {
			originality: 0.24,
			information_value: 0.24,
			writing_quality: 0.18,
			interaction_potential: 0.17,
			timeliness: 0.17,
		},
		thresholds: {
			excellent: 85,
			good: 70,
			review: 55,
		},
		settings: {
			originality: {
				comparison_window: 25,
			},
			timeliness: {
				fresh_hours: 48,
			},
		},
	};
}

function applyConfig(config) {
	configForm.name = config.name || "";
	configForm.weights = normalizeWeights({ ...config.weights });
	configForm.thresholds = { ...config.thresholds };
	configForm.settings = {
		originality: {
			comparison_window: config.settings?.originality?.comparison_window ?? 25,
		},
		timeliness: {
			fresh_hours: config.settings?.timeliness?.fresh_hours ?? 48,
		},
	};
}

function normalizeWeights(weights) {
	const values = Object.values(weights).map((value) => Number(value) || 0);
	const total = values.reduce((sum, value) => sum + Math.max(value, 0), 0);
	if (!total) {
		return createDefaultConfig().weights;
	}
	return Object.fromEntries(
		Object.entries(weights).map(([key, value]) => [
			key,
			Number((Math.max(Number(value) || 0, 0) / total).toFixed(4)),
		]),
	);
}

function buildScorePayload() {
	const articleIds = scoreForm.articleIdsText
		.split(/[,，\s]+/)
		.map((item) => Number(item.trim()))
		.filter((item) => Number.isInteger(item) && item > 0);
	return {
		feed_id: scoreForm.feedId,
		article_ids: articleIds,
		limit: scoreForm.limit,
		concurrency: scoreForm.concurrency,
		weights: normalizeWeights({ ...configForm.weights }),
		thresholds: { ...configForm.thresholds },
		settings: {
			originality: {
				comparison_window: configForm.settings.originality.comparison_window,
			},
			timeliness: {
				fresh_hours: configForm.settings.timeliness.fresh_hours,
			},
		},
	};
}

async function fetchConfig() {
	const config = await getRssQualityConfig();
	applyConfig(config);
}

async function fetchFeedsData() {
	feeds.value = await getFeeds({ loading: false });
}

async function fetchResults() {
	const params = {
		min_score: filterForm.minScore,
		max_score: filterForm.maxScore,
		feed_id: filterForm.feedId,
		batch_id: filterForm.batchId || undefined,
		limit: 50,
	};
	results.value = await getRssQualityResults(params);
}

async function fetchLogs() {
	logs.value = await getRssQualityLogs({
		batch_id: latestBatchId.value || undefined,
		limit: 20,
	});
}

async function handleSaveConfig() {
	try {
		const payload = {
			name: configForm.name,
			weights: normalizeWeights({ ...configForm.weights }),
			thresholds: { ...configForm.thresholds },
			settings: {
				originality: {
					comparison_window: configForm.settings.originality.comparison_window,
				},
				timeliness: {
					fresh_hours: configForm.settings.timeliness.fresh_hours,
				},
			},
		};
		const updated = await updateRssQualityConfig(payload);
		applyConfig(updated);
		Message.success("评分规则已保存");
	} catch (error) {
		Message.error(error.message || "保存评分规则失败");
	}
}

async function handleRestoreDefault() {
	try {
		const config = await getDefaultRssQualityConfig({ loading: false });
		applyConfig(config);
		Message.success("已恢复默认配置，请保存后生效");
	} catch (error) {
		Message.error(error.message || "恢复默认配置失败");
	}
}

async function handleScore() {
	try {
		const response = await scoreRssArticles(buildScorePayload());
		latestSummary.value = response.summary;
		latestBatchId.value = response.batchId;
		filterForm.batchId = response.batchId;
		await Promise.all([fetchResults(), fetchLogs()]);
		Message.success("批量评分完成");
	} catch (error) {
		Message.error(error.message || "批量评分失败");
	}
}

function formatPercent(value) {
	return `${Math.round((Number(value) || 0) * 100)}%`;
}

function formatDate(value) {
	if (!value) {
		return "";
	}
	return new Date(value).toLocaleString();
}

function getGradeColor(grade) {
	if (grade === "excellent") {
		return "green";
	}
	if (grade === "good") {
		return "arcoblue";
	}
	if (grade === "review") {
		return "orange";
	}
	return "red";
}

function getLogColor(level) {
	if (level === "error") {
		return "red";
	}
	if (level === "warning") {
		return "orange";
	}
	return "arcoblue";
}

function openResultDetail(record) {
	selectedResult.value = record;
	detailVisible.value = true;
}

onMounted(async () => {
	try {
		await Promise.all([fetchConfig(), fetchFeedsData(), fetchResults()]);
	} catch (error) {
		Message.error(error.message || "初始化 RSS 评分面板失败");
	}
});
</script>

<style scoped>
.rss-quality-panel {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.panel-card {
  margin-bottom: 16px;
}

.weight-row {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.weight-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
}

.weight-title {
  font-size: 14px;
  font-weight: 600;
}

.weight-desc {
  color: var(--color-text-3);
  font-size: 12px;
}

.weight-control {
  display: grid;
  grid-template-columns: 1fr 120px;
  gap: 12px;
  align-items: center;
}

.full-width {
  width: 100%;
}

.logs-card {
  max-height: 360px;
  overflow: auto;
}

.log-item {
  border: 1px solid var(--color-border-2);
  border-radius: 8px;
  padding: 12px;
}

.log-meta {
  display: flex;
  justify-content: space-between;
  margin-bottom: 8px;
  color: var(--color-text-3);
  font-size: 12px;
}

.log-message {
  color: var(--color-text-1);
}

.result-table {
  margin-top: 16px;
}

.article-cell {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.article-title {
  font-weight: 600;
}

.article-subtitle {
  color: var(--color-text-3);
  font-size: 12px;
}

.detail-content {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.detail-dimension {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.detail-title {
  display: flex;
  justify-content: space-between;
  font-weight: 600;
}

.detail-reasons {
  color: var(--color-text-2);
  line-height: 1.6;
}
</style>
