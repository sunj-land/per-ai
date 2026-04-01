<template>
	<div class="vector-admin-container">
		<a-page-header
			title="向量管理"
			subtitle="查看向量库状态并进行语义检索"
			@back="$router.push('/')"
		/>

		<div class="content-wrapper">
			<a-spin :loading="loadingStore.isLoading('vector-stats')" tip="正在加载向量统计...">
				<div v-if="stats" class="stats-container">
					<a-row :gutter="16" class="mb-4">
						<a-col :xs="24" :sm="12" :md="8">
							<a-card title="集合名称">
								<div class="stat-value">{{ stats.collection_name }}</div>
							</a-card>
						</a-col>
						<a-col :xs="24" :sm="12" :md="8">
							<a-card title="向量总数">
								<div class="stat-value">{{ stats.count }}</div>
							</a-card>
						</a-col>
						<a-col :xs="24" :sm="24" :md="8">
							<a-card title="操作">
								<a-space wrap>
									<a-button type="primary" status="success" @click="fetchStats">
										刷新统计
									</a-button>
									<a-popconfirm
										content="确认重建索引？该操作会清空现有向量并重新构建。"
										@ok="_handleRebuild"
									>
										<a-button type="primary" status="danger" :loading="loadingStore.isLoading('vector-rebuild')">
											重建索引
										</a-button>
									</a-popconfirm>
								</a-space>
							</a-card>
						</a-col>
					</a-row>

					<a-card title="语义搜索" class="mt-4">
						<div class="search-controls">
							<a-input-search
								v-model="searchQuery"
								placeholder="输入文本后自动检索相似片段，支持回车立即搜索"
								allow-clear
								search-button
								@search="_handleSearchNow"
								@press-enter="_handleSearchNow"
								@clear="_clearSearch"
							/>

							<div class="limit-control">
								<div class="limit-title">
									<span>结果数量</span>
									<a-tag color="arcoblue">{{ resultLimit }}</a-tag>
								</div>
								<a-slider v-model="resultLimit" :min="1" :max="50" :step="1" />
							</div>
						</div>

						<div class="search-meta">
							<a-typography-text type="secondary">
								已检索 {{ allSearchResults.length }} 条，当前展示 {{ visibleSearchResults.length }} 条
							</a-typography-text>
							<a-typography-text
								v-if="_searchDurationText"
								type="secondary"
								class="duration-text"
							>
								响应耗时：{{ _searchDurationText }}
							</a-typography-text>
						</div>

						<a-spin :loading="loadingStore.isLoading('vector-search')" tip="语义检索中...">
							<a-empty
								v-if="!searchQuery.trim()"
								description="请输入查询文本开始搜索"
							/>
							<a-empty
								v-else-if="!visibleSearchResults.length"
								description="未找到相似文本片段"
							/>
							<div v-else class="result-wrapper">
								<a-list :bordered="false">
									<a-list-item
										v-for="(item, index) in _pagedSearchResults"
										:key="item.id"
										action-layout="vertical"
										class="result-item"
									>
										<div class="result-header">
											<a-space wrap>
												<a-tag>{{ (currentPage - 1) * pageSize + index + 1 }}</a-tag>
												<a-tag color="green">
													相似度 {{ item.similarity.toFixed(4) }}
												</a-tag>
												<a-tag color="arcoblue">
													距离 {{ Number(item.score ?? 0).toFixed(4) }}
												</a-tag>
												<a-tag v-if="item.metadata?.title" color="gold">
													{{ item.metadata.title }}
												</a-tag>
											</a-space>
										</div>
										<a-typography-paragraph
											:ellipsis="{ rows: 3 }"
											class="result-content"
										>
											{{ item.displayContent }}
										</a-typography-paragraph>
									</a-list-item>
								</a-list>

								<div v-if="visibleSearchResults.length > pageSize" class="pagination">
									<a-pagination
										v-model:current="currentPage"
										:total="visibleSearchResults.length"
										:page-size="pageSize"
										show-total
										size="small"
									/>
								</div>
							</div>
						</a-spin>
					</a-card>

					<a-card title="样本数据（Top 10）" class="mt-4">
						<a-table :data="sampleData" :pagination="false" :scroll="{ x: 1200 }">
							<template #columns>
								<a-table-column
									title="ID"
									data-index="id"
									:width="200"
									ellipsis
									tooltip
								/>
								<template v-for="key in _metadataKeys" :key="key">
									<a-table-column
										:title="key"
										:data-index="`metadata.${key}`"
										:width="150"
										ellipsis
										tooltip
									/>
								</template>
								<a-table-column
									title="文档内容"
									data-index="document"
									:width="400"
									ellipsis
									tooltip
								/>
							</template>
						</a-table>
					</a-card>
				</div>
				<a-empty v-else description="暂无向量统计数据" />
			</a-spin>
		</div>
	</div>
</template>

<script setup>
import { Message } from "@arco-design/web-vue";
import { debounce } from "lodash-es";
import { computed, onMounted, onUnmounted, ref, watch } from "vue";
import { getStats, rebuildIndex, searchVectors } from "@/api/vector";
import { useLoadingStore } from "@/store/loading";

const _loadingStore = useLoadingStore();

const MAX_SEARCH_RESULTS = 50;
const SEARCH_TIMEOUT_MS = 2000;
const pageSize = 10;

const stats = ref(null);

const searchQuery = ref("");
const resultLimit = ref(10);
const allSearchResults = ref([]);
const currentPage = ref(1);
const searchDurationMs = ref(null);

let currentSearchController = null;
let currentSearchRequestId = 0;

const normalizeSimilarity = (distance) => {
	const numericDistance = Number(distance ?? 0);
	if (!Number.isFinite(numericDistance)) {
		return 0;
	}
	return 1 / (1 + Math.max(0, numericDistance));
};

const extractDisplayContent = (content) => {
	const plain = typeof content === "string" ? content.trim() : "";
	if (!plain) {
		return "无可展示文本";
	}
	if (!plain.includes("内容:")) {
		return plain;
	}
	const chunks = plain.split("内容:");
	const body = chunks[chunks.length - 1]?.trim();
	return body || plain;
};

const _searchDurationText = computed(() => {
	if (searchDurationMs.value === null) {
		return "";
	}
	return `${searchDurationMs.value.toFixed(0)}ms`;
});

const visibleSearchResults = computed(() => {
	return allSearchResults.value.slice(0, resultLimit.value);
});

const _pagedSearchResults = computed(() => {
	const start = (currentPage.value - 1) * pageSize;
	return visibleSearchResults.value.slice(start, start + pageSize);
});

const sampleData = computed(() => {
	if (!stats.value || !stats.value.peek) {
		return [];
	}
	const { ids, documents, metadatas } = stats.value.peek;
	if (!ids || ids.length === 0) {
		return [];
	}
	return ids.map((id, index) => ({
		id,
		document: documents[index],
		metadata: metadatas[index] || {},
	}));
});

const _metadataKeys = computed(() => {
	if (!sampleData.value.length) {
		return [];
	}
	const keys = new Set();
	sampleData.value.forEach((item) => {
		Object.keys(item.metadata).forEach((metadataKey) => {
			keys.add(metadataKey);
		});
	});
	return Array.from(keys);
});

const fetchStats = async () => {
	try {
		stats.value = await getStats();
	} catch (error) {
		Message.error(`获取向量统计失败: ${error.message}`);
	}
};

const _handleRebuild = async () => {
	try {
		await rebuildIndex();
		Message.success("重建索引成功");
		fetchStats();
	} catch (error) {
		Message.error(`重建索引失败: ${error.message}`);
	}
};

const runSearch = async (queryText) => {
	const trimmedQuery = queryText.trim();
	currentPage.value = 1;

	if (!trimmedQuery) {
		allSearchResults.value = [];
		searchDurationMs.value = null;
		searchLoading.value = false;
		if (currentSearchController) {
			currentSearchController.abort();
			currentSearchController = null;
		}
		return;
	}

	if (currentSearchController) {
		currentSearchController.abort();
	}
	currentSearchController = new AbortController();
	const requestId = ++currentSearchRequestId;
	const start = performance.now();
	searchLoading.value = true;

	try {
		const results = await searchVectors(trimmedQuery, MAX_SEARCH_RESULTS, {
			timeout: SEARCH_TIMEOUT_MS,
			signal: currentSearchController.signal,
		});
		if (requestId !== currentSearchRequestId) {
			return;
		}
		const formattedResults = (results || [])
			.map((item) => {
				const similarity = normalizeSimilarity(item.score);
				return {
					...item,
					similarity,
					displayContent: extractDisplayContent(item.content),
				};
			})
			.sort((a, b) => b.similarity - a.similarity);
		allSearchResults.value = formattedResults;
		if (formattedResults.length === 0) {
			Message.info("未找到相似文本片段");
		}
	} catch (err) {
		if (err.name === "CanceledError" || err.code === "ERR_CANCELED") {
			return;
		}
		if (err.code === "ECONNABORTED") {
			Message.warning("检索超时，请尝试缩短查询文本后重试");
		} else {
			Message.error(
				`语义检索失败：${err.response?.data?.detail || err.message}`,
			);
		}
		allSearchResults.value = [];
	} finally {
		if (requestId === currentSearchRequestId) {
			searchDurationMs.value = performance.now() - start;
		}
	}
};

const debouncedSearch = debounce((queryText) => {
	void runSearch(queryText);
}, 400);

const _clearSearch = () => {
	searchQuery.value = "";
	debouncedSearch.cancel();
	void runSearch("");
};

const _handleSearchNow = async () => {
	if (!searchQuery.value.trim()) return;

	try {
		const startTime = Date.now();
		// Cancel previous pending search if any
		if (currentSearchController) {
			currentSearchController.abort();
		}
		currentSearchController = new AbortController();
		currentSearchRequestId++;

		const res = await searchVectors(searchQuery.value, resultLimit.value, {
			signal: currentSearchController.signal,
		});

		allSearchResults.value = res.map((item) => ({
			...item,
			similarity: normalizeSimilarity(item.score),
			displayContent: extractDisplayContent(item.document),
		}));
		currentPage.value = 1;
		searchDurationMs.value = Date.now() - startTime;
	} catch (error) {
		if (error.name !== "AbortError" && error.code !== "ERR_CANCELED") {
			Message.error(`搜索失败: ${error.message}`);
			allSearchResults.value = [];
		}
	} finally {
		currentSearchController = null;
	}
};

watch(searchQuery, (value) => {
	debouncedSearch(value);
});

watch(resultLimit, () => {
	currentPage.value = 1;
});

onMounted(() => {
	void fetchStats();
});

onUnmounted(() => {
	debouncedSearch.cancel();
	if (currentSearchController) {
		currentSearchController.abort();
	}
});
</script>

<style scoped>
.vector-admin-container {
	height: 100vh;
	display: flex;
	flex-direction: column;
	background-color: var(--color-bg-1);
}

.content-wrapper {
	flex: 1;
	padding: 20px;
	overflow-y: auto;
}

.stat-value {
	font-size: 24px;
	font-weight: bold;
	color: rgb(var(--primary-6));
}

.search-controls {
	display: grid;
	grid-template-columns: minmax(260px, 1fr) minmax(220px, 320px);
	gap: 16px;
	align-items: center;
}

.limit-control {
	padding: 12px 14px;
	border-radius: 8px;
	background: var(--color-fill-1);
}

.limit-title {
	display: flex;
	align-items: center;
	justify-content: space-between;
	margin-bottom: 8px;
}

.search-meta {
	margin: 12px 0 16px;
	display: flex;
	align-items: center;
	gap: 12px;
	flex-wrap: wrap;
}

.result-wrapper {
	min-height: 120px;
}

.result-item {
	padding-left: 0;
	padding-right: 0;
}

.result-header {
	margin-bottom: 8px;
}

.result-content {
	margin-bottom: 0;
	white-space: pre-wrap;
	word-break: break-word;
}

.pagination {
	margin-top: 8px;
	display: flex;
	justify-content: flex-end;
}

.mb-4 {
	margin-bottom: 16px;
}

.mt-4 {
	margin-top: 16px;
}

@media (max-width: 900px) {
	.search-controls {
		grid-template-columns: 1fr;
	}
}
</style>
