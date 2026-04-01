<template>
  <div class="flex h-full bg-white">
    <!-- 左侧分组侧边栏 -->
    <GroupTree
      v-model="selectedKeys"
      @select="handleTreeSelect"
    />

    <!-- 右侧文章列表 -->
    <div class="flex-1 flex flex-col h-full overflow-hidden p-4 sm:p-6 relative">
      <a-page-header title="文章列表" :show-back="false" class="mb-4 px-0 shrink-0">
      <template #extra>
        <a-space>
          <a-input-search
            v-model="searchQuery"
            :style="{width:'320px'}"
            placeholder="搜索文章 (语义搜索)..."
            allow-clear
            search-button
            @search="handleSearch"
            @press-enter="handleSearch"
            @clear="clearSearch"
          />

          <a-popover trigger="click" position="bottom">
            <a-button>
              <template #icon><icon-experiment /></template>
            </a-button>
            <template #content>
              <div style="width: 250px; padding: 10px;">
                <div class="mb-2 font-bold">搜索设置</div>
                <div class="flex justify-between mb-1">
                   <span>返回数量</span>
                   <span>{{ searchLimit }}</span>
                </div>
                <a-slider v-model="searchLimit" :min="1" :max="50" :step="1" />
              </div>
            </template>
          </a-popover>

          <a-input-number
            v-model="scoreFilter.minScore"
            :min="0"
            :max="100"
            :style="{ width: '110px' }"
            placeholder="最低分"
          />
          <a-input-number
            v-model="scoreFilter.maxScore"
            :min="0"
            :max="100"
            :style="{ width: '110px' }"
            placeholder="最高分"
          />
          <a-button @click="clearScoreFilter">
            清空评分筛选
          </a-button>
          <a-select
            v-model="sortMode"
            :style="{ width: '170px' }"
            placeholder="排序方式"
          >
            <a-option value="published_desc">按发布时间</a-option>
            <a-option value="score_desc">按评分从高到低</a-option>
            <a-option value="score_asc">按评分从低到高</a-option>
          </a-select>
          <a-select
            v-model="gradeFilter"
            allow-clear
            :style="{ width: '150px' }"
            placeholder="按等级筛选"
          >
            <a-option value="excellent">excellent</a-option>
            <a-option value="good">good</a-option>
            <a-option value="review">review</a-option>
            <a-option value="low">low</a-option>
          </a-select>
          <a-button
            :type="showOnlyUnscored ? 'primary' : 'default'"
            @click="toggleOnlyUnscored"
          >
            只看未评分
          </a-button>
          <a-button
            type="primary"
            :loading="loadingStore.isLoading('rss-quality-score')"
            @click="handleScoreCurrentList"
          >
            <template #icon><icon-star /></template>
            评分当前列表
          </a-button>
          <a-button
            :loading="loadingStore.isLoading('rss-quality-score')"
            @click="handleScoreUnscoredArticles"
          >
            <template #icon><icon-star /></template>
            仅评分未评分文章
          </a-button>
          <a-button @click="refreshVisibleScores">
            <template #icon><icon-sync /></template>
            刷新评分
          </a-button>

          <a-button @click="handleRefresh">
            <template #icon><icon-refresh /></template>
            刷新
          </a-button>
          <a-button @click="handleExportScores">
            <template #icon><icon-download /></template>
            导出
          </a-button>
          <a-button @click="openBatchHistory">
            <template #icon><icon-history /></template>
            批次历史
          </a-button>
          <a-button @click="$router.push('/rss/feeds')">
            <template #icon><icon-settings /></template>
            管理订阅源
          </a-button>
        </a-space>
      </template>
    </a-page-header>

    <a-card :bordered="false" class="rounded-lg shadow-sm flex-1 overflow-auto">
      <!-- Search Results View -->
      <div v-if="isSearching">
         <div class="flex justify-between items-center mb-4 px-4">
            <a-typography-title :heading="6" class="m-0">
               搜索结果: "{{ searchQuery }}" ({{ searchResults.length }})
            </a-typography-title>
            <a-button type="text" size="small" @click="clearSearch">
               <template #icon><icon-close /></template>
               返回列表
            </a-button>
         </div>

         <a-list :loading="loadingStore.isLoading('vector-search')" :bordered="false">
            <a-list-item v-for="item in searchResults" :key="item.id"
               action-layout="vertical"
               class="hover:bg-gray-50 cursor-pointer transition-colors duration-200"
               @click="$router.push(`/rss/articles/${item.metadata.article_id}`)"
            >
               <a-list-item-meta>
                  <template #title>
                     <div class="flex justify-between items-start">
                        <a-typography-text bold class="text-base">{{ item.metadata.title || '无标题' }}</a-typography-text>
                        <a-tag color="arcoblue" size="small" title="相似度距离 (越小越好)">
                           Score: {{ (item.score).toFixed(4) }}
                        </a-tag>
                     </div>
                  </template>
                  <template #description>
                     <a-typography-paragraph type="secondary" :ellipsis="{ rows: 3 }" class="mt-1 mb-0">
                        {{ item.content }}
                     </a-typography-paragraph>
                  </template>
               </a-list-item-meta>
               <template #actions>
                  <a-space size="medium" class="mt-2">
                     <span class="text-gray-400 text-sm" v-if="item.metadata.published_at">
                        <icon-clock-circle class="mr-1" />
                        {{ dayjs(item.metadata.published_at).fromNow() }}
                     </span>
                     <a-tag v-if="item.metadata.keywords" size="small" color="gray" bordered>
                        <template #icon><icon-tag /></template>
                        {{ item.metadata.keywords.split(',')[0] }}
                     </a-tag>

                     <a-button type="text" size="small" @click.stop="openSendModal(item.metadata)" class="ml-auto" :loading="sendModalVisible && currentArticleForSend?.id === item.metadata?.id">
                        <template #icon><icon-send /></template>
                        发送
                     </a-button>
                  </a-space>
               </template>
            </a-list-item>
            <template #empty>
               <a-empty description="未找到相关结果" />
            </template>
         </a-list>
      </div>

      <!-- Regular Article List -->
      <div v-else>
      <div class="mb-4 px-4 flex flex-wrap items-center gap-3">
        <a-tag color="arcoblue">已加载 {{ articles.length }} 篇</a-tag>
        <a-tag color="purple">当前展示 {{ displayedArticles.length }} 篇</a-tag>
        <a-tag color="green">已评分 {{ scoredArticleCount }} 篇</a-tag>
        <a-tag v-if="showOnlyUnscored" color="red">仅看未评分</a-tag>
        <a-tag v-if="gradeFilter" color="cyan">等级 {{ gradeFilter }}</a-tag>
        <a-tag v-if="quickScoreFilterLabel" color="magenta">{{ quickScoreFilterLabel }}</a-tag>
        <a-tag v-if="scoreFilterLabel" color="orange">{{ scoreFilterLabel }}</a-tag>
        <a-typography-text v-if="scoredAverage !== null" type="secondary">
          当前已评分文章平均分 {{ scoredAverage }}
        </a-typography-text>
        <a-space size="small">
          <a-button size="mini" @click="applyQuickScoreFilter('all')">全部</a-button>
          <a-button size="mini" @click="applyQuickScoreFilter('high')">80+</a-button>
          <a-button size="mini" @click="applyQuickScoreFilter('excellent')">90+</a-button>
        </a-space>
      </div>
      <a-list :loading="loadingStore.isLoading('rss-articles')" :bordered="false">
        <a-list-item
          v-for="article in displayedArticles"
          :key="article.id"
          action-layout="vertical"
          class="hover:bg-gray-50 cursor-pointer transition-colors duration-200"
          @click="$router.push(`/rss/articles/${article.id}`)"
        >
          <a-list-item-meta>
            <template #title>
              <div class="flex items-center justify-between gap-3">
                <a-typography-text bold class="text-base">{{ article.title }}</a-typography-text>
                <a-space v-if="getArticleScore(article.id)" size="small">
                  <a-tag :color="getScoreTagColor(getArticleScore(article.id).grade)" size="small">
                    {{ getArticleScore(article.id).grade }}
                  </a-tag>
                  <a-tag color="green" size="small">
                    质量分 {{ formatScore(getArticleScore(article.id).overallScore) }}
                  </a-tag>
                </a-space>
              </div>
            </template>
            <template #description>
              <a-typography-paragraph
                type="secondary"
                :ellipsis="{ rows: 2 }"
                class="mt-1 mb-0"
              >
                {{ article.summary || '暂无摘要' }}
              </a-typography-paragraph>
            </template>
            <template #avatar>
              <a-avatar
                :style="{ backgroundColor: getAvatarColor(article.feed_title || 'R') }"
                size="large"
              >
                {{ (article.feed_title || 'R')[0].toUpperCase() }}
              </a-avatar>
            </template>
          </a-list-item-meta>

          <template #actions>
            <a-space size="medium" class="mt-2">
              <a-tag size="small" bordered color="arcoblue">
                <template #icon><icon-book /></template>
                {{ article.feed_title }}
              </a-tag>

              <span class="text-gray-400 text-sm flex items-center">
                <icon-clock-circle class="mr-1" />
                {{ dayjs(article.published_at).fromNow() }}
              </span>

              <a-tag v-if="article.author" size="small" color="gray" bordered>
                <template #icon><icon-user /></template>
                {{ article.author }}
              </a-tag>

              <a-tag v-if="article.category" size="small" color="orangered" bordered>
                <template #icon><icon-tag /></template>
                {{ article.category }}
              </a-tag>

              <a-button
                type="text"
                size="small"
                @click.stop="handleScoreArticle(article)"
                :loading="loadingStore.isLoading('rss-quality-score')"
              >
                <template #icon><icon-star /></template>
                {{ getArticleScore(article.id) ? '重新评分' : '评分' }}
              </a-button>
              <a-button
                v-if="getArticleScore(article.id)"
                type="text"
                size="small"
                @click.stop="openScoreDetail(article.id)"
              >
                <template #icon><icon-file /></template>
                评分报告
              </a-button>

              <a-button type="text" size="small" @click.stop="openSendModal(article)" class="ml-auto" :loading="sendModalVisible && currentArticleForSend?.id === article.id">
                <template #icon><icon-send /></template>
                发送
              </a-button>
            </a-space>
          </template>
        </a-list-item>

        <template #empty>
          <a-empty description="暂无文章" />
        </template>
      </a-list>

      <!-- 骨架屏加载状态 -->
      <div v-if="loadingStore.isLoading('rss-articles-more')" class="mt-4 space-y-4 px-4">
        <div v-for="i in 3" :key="i">
          <a-skeleton animation>
            <a-space direction="vertical" :style="{width:'100%'}" size="medium">
              <a-space align="start" size="medium">
                <a-skeleton-shape shape="circle" size="large" />
                <a-space direction="vertical" size="small">
                  <a-skeleton-line :rows="1" :widths="['300px']" />
                  <a-skeleton-line :rows="2" :widths="['100%', '80%']" />
                </a-space>
              </a-space>
              <a-space class="ml-12">
                 <a-skeleton-line :rows="1" :widths="['100px']" />
                 <a-skeleton-line :rows="1" :widths="['150px']" />
              </a-space>
            </a-space>
          </a-skeleton>
          <a-divider v-if="i < 3" />
        </div>
      </div>

      <!-- 无限滚动触发哨兵 -->
      <div ref="bottomSentinel" class="h-4 w-full"></div>

      <div class="mt-6 flex justify-center pb-4" v-if="articles.length > 0 && !hasMore">
        <a-typography-text type="secondary" class="text-xs">没有更多文章了</a-typography-text>
      </div>
      </div>
    </a-card>
    </div>

    <!-- Send to Channel Modal -->
    <ChannelSelectorModal
      v-model="sendModalVisible"
      :initial-title="currentArticleForSend?.title || ''"
      :initial-content="sendModalContent"
    />

    <a-drawer
      v-model:visible="scoreDetailVisible"
      width="640px"
      title="文章质量评分报告"
      unmount-on-close
    >
      <div v-if="currentScoreDetail" class="score-detail">
        <a-descriptions :column="1" bordered>
          <a-descriptions-item label="文章标题">
            {{ currentScoreDetail.articleTitle }}
          </a-descriptions-item>
          <a-descriptions-item label="综合评分">
            {{ formatScore(currentScoreDetail.overallScore) }}
          </a-descriptions-item>
          <a-descriptions-item label="等级">
            {{ currentScoreDetail.grade }}
          </a-descriptions-item>
          <a-descriptions-item label="批次">
            {{ currentScoreDetail.batchId }}
          </a-descriptions-item>
        </a-descriptions>

        <div
          v-for="dimension in scoreDimensions"
          :key="dimension.key"
          class="score-dimension"
        >
          <div class="score-dimension-header">
            <span>{{ dimension.label }}</span>
            <span>{{ formatScore(currentScoreDetail.report.dimensions[dimension.key].score) }}</span>
          </div>
          <a-progress
            :percent="currentScoreDetail.report.dimensions[dimension.key].score"
            :show-text="false"
          />
          <div class="score-dimension-reason">
            {{ currentScoreDetail.report.dimensions[dimension.key].reasons.join('；') }}
          </div>
        </div>
      </div>
    </a-drawer>

    <a-drawer
      v-model:visible="batchHistoryVisible"
      width="720px"
      title="评分批次历史"
      unmount-on-close
    >
      <div class="batch-history">
        <a-spin :loading="loadingStore.isLoading('rss-quality-batch-history')">
          <div v-if="batchHistory.length === 0" class="py-8 text-center">
            <a-typography-text type="secondary">暂无批次记录</a-typography-text>
          </div>
          <a-table
            v-else
            :columns="batchHistoryColumns"
            :data="batchHistory"
            :pagination="{ pageSize: 10 }"
            size="small"
            stripe
          >
            <template #batchId="{ record }">
              <a-tag color="arcoblue">{{ record.batchId }}</a-tag>
            </template>
            <template #successCount="{ record }">
              <span class="font-bold text-green-600">{{ record.successCount }}</span>
            </template>
            <template #averageScore="{ record }">
              {{ record.averageScore != null ? formatScore(record.averageScore) : '-' }}
            </template>
            <template #createdAt="{ record }">
              {{ dayjs(record.createdAt).format('YYYY-MM-DD HH:mm:ss') }}
            </template>
            <template #actions="{ record }">
              <a-button
                type="text"
                size="small"
                @click="openBatchDetail(record.batchId)"
              >
                查看详情
              </a-button>
            </template>
          </a-table>
        </a-spin>
      </div>
    </a-drawer>
  </div>
</template>

<script setup>
import dayjs from "dayjs";
import relativeTime from "dayjs/plugin/relativeTime";
import { computed, onMounted, onUnmounted, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import ChannelSelectorModal from "@/components/channel/ChannelSelectorModal.vue";
import { getRssQualityResults, scoreRssArticles } from "../../api/agent-center";
import { getArticles } from "../../api/rss";
import { searchVectors } from "../../api/vector";
import { useLoadingStore } from "../../store/loading";
import GroupTree from "./components/GroupTree.vue";
import "dayjs/locale/zh-cn";
import { Message } from "@arco-design/web-vue";

dayjs.extend(relativeTime);
dayjs.locale("zh-cn");

const route = useRoute();
const router = useRouter();
const loadingStore = useLoadingStore();
// 响应式状态
const articles = ref([]); // 文章列表数据
const page = ref(0); // 当前页码
const pageSize = 20; // 每页文章数量
const hasMore = ref(true); // 是否还有更多数据
const bottomSentinel = ref(null);
let observer = null;
const articleScoreMap = ref({});
const scoreDetailVisible = ref(false);
const currentScoreDetail = ref(null);
const scoreFilter = ref({
	minScore: undefined,
	maxScore: undefined,
});
const sortMode = ref("published_desc");
const quickScorePreset = ref("all");
const gradeFilter = ref(undefined);
const showOnlyUnscored = ref(false);
const batchHistoryVisible = ref(false);
const batchHistory = ref([]);
const batchHistoryColumns = [
	{ title: "批次ID", slotName: "batchId", width: 160 },
	{ title: "成功数", slotName: "successCount", width: 80 },
	{ title: "平均分", slotName: "averageScore", width: 90 },
	{ title: "时间", slotName: "createdAt" },
	{ title: "操作", slotName: "actions", width: 100 },
];

// 树选择状态
const selectedKeys = ref(["all"]);
const currentFilter = ref({ type: "all", id: null });
const scoreDimensions = [
	{ key: "originality", label: "内容原创性" },
	{ key: "information_value", label: "信息价值度" },
	{ key: "writing_quality", label: "写作质量" },
	{ key: "interaction_potential", label: "用户互动潜力" },
	{ key: "timeliness", label: "时效性" },
];

const handleTreeSelect = (keys, node) => {
	if (keys.length === 0) return;

	if (node.key === "all") {
		currentFilter.value = { type: "all", id: null };
		// Clear feed_id from URL if any
		if (route.query.feed_id) {
			router.replace({ query: {} });
		}
	} else if (node.isGroup) {
		currentFilter.value = { type: "group", id: node.groupId };
		if (route.query.feed_id) {
			router.replace({ query: {} });
		}
	} else {
		currentFilter.value = { type: "feed", id: node.feedId };
		router.replace({ query: { feed_id: node.feedId } });
	}

	loadArticles(true);
};

// Search State
const searchQuery = ref("");
const searchLimit = ref(10);
const isSearching = ref(false);
const searchResults = ref([]);

// Send Message State
const sendModalVisible = ref(false);
const currentArticleForSend = ref(null);
const sendModalContent = computed(() => {
	if (!currentArticleForSend.value) return "";
	const article = currentArticleForSend.value;
	// If it's a vector search result, link might be missing or different, but article list has link
	const link = article.link || "";
	const summary = article.summary || article.content || "";
	return `[${article.title || article.metadata?.title}](${link})\n\n${summary}`;
});

const openSendModal = (article) => {
	currentArticleForSend.value = article;
	sendModalVisible.value = true;
};

const getArticleScore = (articleId) => {
	return articleScoreMap.value[articleId] || null;
};

const formatScore = (score) => {
	return Number(score || 0).toFixed(1);
};

const getScoreTagColor = (grade) => {
	if (grade === "excellent") return "green";
	if (grade === "good") return "arcoblue";
	if (grade === "review") return "orange";
	return "gray";
};

const scoreFilterLabel = computed(() => {
	const { minScore, maxScore } = scoreFilter.value;
	if (minScore === undefined && maxScore === undefined) {
		return "";
	}
	if (minScore !== undefined && maxScore !== undefined) {
		return `评分区间 ${minScore}-${maxScore}`;
	}
	if (minScore !== undefined) {
		return `评分不低于 ${minScore}`;
	}
	return `评分不高于 ${maxScore}`;
});

const quickScoreFilterLabel = computed(() => {
	if (quickScorePreset.value === "high") {
		return "快捷筛选 80+";
	}
	if (quickScorePreset.value === "excellent") {
		return "快捷筛选 90+";
	}
	return "";
});

const filteredArticles = computed(() => {
	const { minScore, maxScore } = scoreFilter.value;
	return articles.value.filter((article) => {
		const articleScore = getArticleScore(article.id);
		const score = articleScore?.overallScore;
		const grade = articleScore?.grade;
		if (showOnlyUnscored.value) {
			return !articleScore;
		}
		if (gradeFilter.value) {
			if (!grade || grade !== gradeFilter.value) {
				return false;
			}
		}
		if ((minScore !== undefined || maxScore !== undefined) && !articleScore) {
			return false;
		}
		if (minScore !== undefined && score < minScore) {
			return false;
		}
		if (maxScore !== undefined && score > maxScore) {
			return false;
		}
		return true;
	});
});

const displayedArticles = computed(() => {
	const sortedArticles = [...filteredArticles.value];
	if (sortMode.value === "score_desc") {
		return sortedArticles.sort((left, right) => {
			const leftScore = getArticleScore(left.id)?.overallScore ?? -1;
			const rightScore = getArticleScore(right.id)?.overallScore ?? -1;
			return rightScore - leftScore;
		});
	}
	if (sortMode.value === "score_asc") {
		return sortedArticles.sort((left, right) => {
			const leftScore = getArticleScore(left.id)?.overallScore ?? 101;
			const rightScore = getArticleScore(right.id)?.overallScore ?? 101;
			return leftScore - rightScore;
		});
	}
	return sortedArticles.sort((left, right) => {
		return (
			new Date(right.published_at || 0).getTime() -
			new Date(left.published_at || 0).getTime()
		);
	});
});

const scoredArticleCount = computed(() => {
	return articles.value.filter((article) => getArticleScore(article.id)).length;
});

const scoredAverage = computed(() => {
	const scoredArticles = articles.value
		.map((article) => getArticleScore(article.id)?.overallScore)
		.filter((score) => score !== undefined && score !== null);
	if (scoredArticles.length === 0) {
		return null;
	}
	return formatScore(
		scoredArticles.reduce((sum, score) => sum + score, 0) /
			scoredArticles.length,
	);
});

const applyScoreResults = (results = []) => {
	if (!Array.isArray(results) || results.length === 0) {
		return;
	}
	const nextMap = { ...articleScoreMap.value };
	for (const result of results) {
		if (!result?.articleId) continue;
		if (!nextMap[result.articleId]) {
			nextMap[result.articleId] = result;
			continue;
		}
		const currentCreatedAt = new Date(
			nextMap[result.articleId].createdAt || 0,
		).getTime();
		const nextCreatedAt = new Date(result.createdAt || 0).getTime();
		if (nextCreatedAt >= currentCreatedAt) {
			nextMap[result.articleId] = result;
		}
	}
	articleScoreMap.value = nextMap;
};

const refreshVisibleScores = async (targetArticles = articles.value) => {
	const targetIds = targetArticles
		.map((article) => article?.id)
		.filter((id) => Number.isInteger(id));
	if (targetIds.length === 0) {
		return;
	}
	try {
		const params = {
			limit: Math.max(targetIds.length * 3, 50),
		};
		if (currentFilter.value.type === "feed") {
			params.feed_id = currentFilter.value.id;
		}
		const results = await getRssQualityResults(params, {
			loading: false,
			silent: true,
		});
		applyScoreResults(
			results.filter((item) => targetIds.includes(item.articleId)),
		);
	} catch (error) {
		console.error("refresh rss quality scores failed", error);
	}
};

const openScoreDetail = (articleId) => {
	const result = getArticleScore(articleId);
	if (!result?.report?.dimensions) {
		Message.info("当前文章暂无评分报告");
		return;
	}
	currentScoreDetail.value = result;
	scoreDetailVisible.value = true;
};

const handleScoreArticle = async (article) => {
	try {
		const response = await scoreRssArticles({
			article_ids: [article.id],
			limit: 1,
			concurrency: 1,
		});
		applyScoreResults(response.results);
		Message.success(`《${article.title}》评分完成`);
	} catch (error) {
		Message.error(error.message || "文章评分失败");
	}
};

const handleScoreCurrentList = async () => {
	const targetIds = articles.value.map((article) => article.id);
	if (targetIds.length === 0) {
		Message.info("当前列表暂无可评分文章");
		return;
	}
	try {
		const response = await scoreRssArticles({
			article_ids: targetIds,
			limit: targetIds.length,
			concurrency: Math.min(targetIds.length, 5),
		});
		applyScoreResults(response.results);
		Message.success(
			`批量评分完成：成功 ${response.summary?.success || 0} 篇，平均分 ${response.summary?.averageScore || 0}`,
		);
	} catch (error) {
		Message.error(error.message || "批量评分失败");
	}
};

const handleScoreUnscoredArticles = async () => {
	const targetIds = articles.value
		.filter((article) => !getArticleScore(article.id))
		.map((article) => article.id);
	if (targetIds.length === 0) {
		Message.info("当前列表未评分文章已全部处理");
		return;
	}
	try {
		const response = await scoreRssArticles({
			article_ids: targetIds,
			limit: targetIds.length,
			concurrency: Math.min(targetIds.length, 5),
		});
		applyScoreResults(response.results);
		Message.success(
			`未评分文章处理完成：成功 ${response.summary?.success || 0} 篇`,
		);
	} catch (error) {
		Message.error(error.message || "未评分文章批量评分失败");
	}
};

const handleExportScores = () => {
	const scoredArticles = articles.value.filter((article) => {
		return getArticleScore(article.id);
	});
	if (scoredArticles.length === 0) {
		Message.warning("当前列表暂无已评分文章可供导出");
		return;
	}
	const headers = [
		"文章ID",
		"文章标题",
		"订阅源",
		"发布时间",
		"综合评分",
		"等级",
		"内容原创性",
		"信息价值度",
		"写作质量",
		"用户互动潜力",
		"时效性",
		"评分批次",
		"评分时间",
	];
	const rows = scoredArticles.map((article) => {
		const score = getArticleScore(article.id);
		return [
			article.id,
			`"${(article.title || "").replace(/"/g, '""')}"`,
			`"${(article.feed_title || "").replace(/"/g, '""')}"`,
			article.published_at || "",
			score?.overallScore ?? "",
			score?.grade ?? "",
			score?.report?.dimensions?.originality?.score ?? "",
			score?.report?.dimensions?.information_value?.score ?? "",
			score?.report?.dimensions?.writing_quality?.score ?? "",
			score?.report?.dimensions?.interaction_potential?.score ?? "",
			score?.report?.dimensions?.timeliness?.score ?? "",
			score?.batchId ?? "",
			score?.createdAt ?? "",
		];
	});
	const csvContent =
		"\ufeff" + [headers.join(","), ...rows.map((r) => r.join(","))].join("\n");
	const blob = new Blob([csvContent], { type: "text/csv;charset=utf-8;" });
	const url = URL.createObjectURL(blob);
	const link = document.createElement("a");
	link.href = url;
	link.download = `rss_quality_scores_${dayjs().format("YYYYMMDD_HHmmss")}.csv`;
	document.body.appendChild(link);
	link.click();
	document.body.removeChild(link);
	URL.revokeObjectURL(url);
	Message.success(`已导出 ${scoredArticles.length} 篇评分记录`);
};

const openBatchHistory = async () => {
	batchHistoryVisible.value = true;
	try {
		const results = await getRssQualityResults(
			{ limit: 200 },
			{
				loading: true,
				loadingKey: "rss-quality-batch-history",
			},
		);
		const batchMap = {};
		for (const item of results) {
			if (!item?.batchId) continue;
			if (!batchMap[item.batchId]) {
				batchMap[item.batchId] = {
					batchId: item.batchId,
					successCount: 0,
					totalScore: 0,
					createdAt: item.createdAt,
				};
			}
			batchMap[item.batchId].successCount++;
			batchMap[item.batchId].totalScore += Number(item.overallScore || 0);
			if (
				new Date(item.createdAt || 0).getTime() >
				new Date(batchMap[item.batchId].createdAt || 0).getTime()
			) {
				batchMap[item.batchId].createdAt = item.createdAt;
			}
		}
		batchHistory.value = Object.values(batchMap)
			.map((b) => ({
				...b,
				averageScore: b.successCount > 0 ? b.totalScore / b.successCount : null,
			}))
			.sort(
				(a, b) =>
					new Date(b.createdAt).getTime() - new Date(a.createdAt).getTime(),
			);
	} catch (error) {
		console.error("load batch history failed", error);
		Message.error("加载批次历史失败");
	}
};

const openBatchDetail = async (batchId) => {
	try {
		const results = await getRssQualityResults({
			limit: 200,
			batch_id: batchId,
		});
		const batchResults = results.filter((r) => r.batchId === batchId);
		if (batchResults.length === 0) {
			Message.warning("该批次暂无评分详情");
			return;
		}
		batchHistoryVisible.value = false;
		applyScoreResults(batchResults);
		Message.info(`已加载批次 ${batchId} 的 ${batchResults.length} 条评分记录`);
	} catch (error) {
		Message.error("加载批次详情失败");
	}
};

const clearScoreFilter = () => {
	scoreFilter.value = {
		minScore: undefined,
		maxScore: undefined,
	};
	quickScorePreset.value = "all";
	gradeFilter.value = undefined;
	showOnlyUnscored.value = false;
};

const applyQuickScoreFilter = (preset) => {
	quickScorePreset.value = preset;
	if (preset === "high") {
		scoreFilter.value = {
			minScore: 80,
			maxScore: undefined,
		};
		return;
	}
	if (preset === "excellent") {
		scoreFilter.value = {
			minScore: 90,
			maxScore: undefined,
		};
		return;
	}
	scoreFilter.value = {
		minScore: undefined,
		maxScore: undefined,
	};
};

const toggleOnlyUnscored = () => {
	showOnlyUnscored.value = !showOnlyUnscored.value;
	if (showOnlyUnscored.value) {
		gradeFilter.value = undefined;
		scoreFilter.value = {
			minScore: undefined,
			maxScore: undefined,
		};
		quickScorePreset.value = "all";
	}
};

// Search Handler
const handleSearch = async () => {
	if (!searchQuery.value.trim()) {
		isSearching.value = false;
		searchResults.value = [];
		return;
	}

	isSearching.value = true;

	try {
		const results = await searchVectors(searchQuery.value, searchLimit.value);
		searchResults.value = results;
		const articleIds = results
			.map((item) => Number(item?.metadata?.article_id))
			.filter((id) => Number.isInteger(id));
		if (articleIds.length > 0) {
			await refreshVisibleScores(articleIds.map((id) => ({ id })));
		}
		if (results.length === 0) {
			Message.info("未找到相关文章");
		}
	} catch (error) {
		Message.error(`搜索失败: ${error.response?.data?.detail || error.message}`);
		console.error(error);
	}
};

const clearSearch = () => {
	searchQuery.value = "";
	isSearching.value = false;
	searchResults.value = [];
};

/**
 * 加载文章列表
 *
 * @param {boolean} reset - 是否重置列表（例如切换订阅源或刷新时）
 */
const loadArticles = async (reset = false) => {
	const isLoading =
		loadingStore.isLoading("rss-articles") ||
		loadingStore.isLoading("rss-articles-more");
	if (isLoading && !reset) return;

	if (reset) {
		page.value = 0;
		articles.value = [];
		hasMore.value = true;
		articleScoreMap.value = {};
	}

	try {
		const params = {
			offset: page.value * pageSize,
			limit: pageSize,
		};

		// 优先使用当前过滤状态，如果没有则尝试从路由获取（初始加载时）
		if (currentFilter.value.type === "feed") {
			params.feed_id = currentFilter.value.id;
		} else if (currentFilter.value.type === "group") {
			params.group_id = currentFilter.value.id;
		} else if (route.query.feed_id) {
			params.feed_id = route.query.feed_id;
		}

		const loadingKey = reset ? "rss-articles" : "rss-articles-more";
		const newArticles = await getArticles(params, { loading: loadingKey });

		// 如果返回的文章数量小于每页数量，说明没有更多数据了
		if (newArticles.length < pageSize) {
			hasMore.value = false;
		}

		if (reset) {
			articles.value = newArticles;
		} else {
			articles.value = [...articles.value, ...newArticles];
		}

		if (newArticles.length > 0) {
			page.value++;
		}
		await refreshVisibleScores(reset ? newArticles : articles.value);
	} catch (error) {
		Message.error("加载文章列表失败");
		console.error(error);
	}
};

/**
 * 加载更多按钮点击事件
 */
const loadMore = () => {
	if (hasMore.value) {
		loadArticles(false);
	}
};

const handleRefresh = () => {
	loadArticles(true);
};

/**
 * 根据字符串生成头像背景色
 */
const getAvatarColor = (str) => {
	if (!str) return "#165DFF";
	let hash = 0;
	for (let i = 0; i < str.length; i++) {
		hash = str.charCodeAt(i) + ((hash << 5) - hash);
	}
	const c = (hash & 0x00ffffff).toString(16).toUpperCase();
	return `#${"00000".substring(0, 6 - c.length)}${c}`;
};

// 初始化 IntersectionObserver
const initObserver = () => {
	if (observer) observer.disconnect();

	observer = new IntersectionObserver(
		(entries) => {
			if (
				entries[0].isIntersecting &&
				hasMore.value &&
				!loadingStore.isLoading("rss-articles-more") &&
				!loadingStore.isLoading("rss-articles")
			) {
				loadMore();
			}
		},
		{
			rootMargin: "200px", // 提前 200px 触发加载
			threshold: 0.1,
		},
	);

	if (bottomSentinel.value) {
		observer.observe(bottomSentinel.value);
	}
};

// 组件挂载时初始化加载
onMounted(() => {
	loadArticles(true);
	initObserver();
});

onUnmounted(() => {
	if (observer) {
		observer.disconnect();
	}
});

// 监听 Sentinel 元素的变化
watch(bottomSentinel, (el) => {
	if (el && observer) {
		observer.disconnect();
		observer.observe(el);
	}
});

// 监听 feed_id 变化，重新加载文章
watch(
	() => route.query.feed_id,
	() => {
		loadArticles(true);
	},
);
</script>

<style scoped>
:deep(.arco-list-item) {
    padding: 16px;
    border-radius: 8px;
    border: 1px solid var(--color-border-2);
    margin-bottom: 12px;
}
:deep(.arco-list-item:hover) {
    background-color: var(--color-fill-2);
}
.score-detail {
	display: flex;
	flex-direction: column;
	gap: 16px;
}
:deep(.score-dimension) {
	display: flex;
	flex-direction: column;
	gap: 8px;
}
.score-dimension-header {
	display: flex;
	justify-content: space-between;
	font-weight: 600;
}
.score-dimension-reason {
	color: var(--color-text-2);
	font-size: 13px;
}
</style>
