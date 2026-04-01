<template>
  <div class="flex h-full bg-white">
    <!-- 左侧分组侧边栏 -->
    <GroupTree
      v-model="selectedGroupKeys"
      :show-feeds="false"
      @select="_handleGroupSelect"
      @refresh="loadGroups"
      ref="groupTreeRef"
    />

    <!-- 右侧内容区域 -->
    <div class="flex-1 flex flex-col h-full overflow-hidden relative">
      <div class="p-4 sm:p-6 flex-1 overflow-auto">
        <a-page-header title="RSS 订阅源管理" :show-back="false" class="mb-4 px-0">
          <template #extra>
            <a-space wrap>
              <a-upload :custom-request="_handleImportOpml" :show-file-list="false" accept=".opml,.xml">
                <template #upload-button>
                  <a-button>
                    <template #icon><icon-upload /></template>
                    导入 OPML
                  </a-button>
                </template>
              </a-upload>
              <a-button v-if="selectedKeys.length > 0" status="danger" @click="_handleBatchDelete">
                <template #icon><icon-delete /></template>
                批量删除 ({{ selectedKeys.length }})
              </a-button>
               <a-button v-if="selectedKeys.length > 0" @click="_openBatchGroupModal">
                <template #icon><icon-folder /></template>
                批量分组
              </a-button>
              <a-button status="warning" @click="_openCleanupModal">
                <template #icon><icon-brush /></template>
                数据清理
              </a-button>
              <a-button @click="_handleAutoClassify">
                <template #icon><icon-robot /></template>
                智能分类
              </a-button>
              <a-button @click="_handleRefreshAll" :loading="loadingStore.isLoading('rss-refresh')">
                <template #icon><icon-refresh /></template>
                刷新所有
              </a-button>
              <a-button type="primary" @click="_openAddModal">
                <template #icon><icon-plus /></template>
                添加订阅源
              </a-button>
            </a-space>
          </template>
        </a-page-header>

        <a-card :bordered="false" class="rounded-lg shadow-sm">
          <a-table
            :data="filteredFeeds"
            :pagination="false"
            :loading="loadingStore.isLoading('rss-feeds')"
            :row-selection="_rowSelection"
            v-model:selectedKeys="selectedKeys"
            row-key="id"
            :scroll="{ x: 'max-content' }"
          >
            <template #columns>
              <a-table-column title="ID" data-index="id" :width="80" />
              <a-table-column title="标题" data-index="title" :width="300">
                <template #cell="{ record }">
                  <div class="flex flex-col">
                    <a-typography-text bold>{{ record.title || '未获取标题' }}</a-typography-text>
                    <a-typography-text type="secondary" class="text-xs truncate" :style="{ maxWidth: '280px' }">
                      {{ record.description }}
                    </a-typography-text>
                  </div>
                </template>
              </a-table-column>
              <a-table-column title="分组" :width="200">
                <template #cell="{ record }">
                  <a-space wrap size="mini">
                    <a-tag v-for="group in record.groups" :key="group.id" color="arcoblue" size="small">
                      {{ group.name }}
                    </a-tag>
                    <span v-if="!record.groups || record.groups.length === 0" class="text-gray-300">-</span>
                  </a-space>
                </template>
              </a-table-column>
              <a-table-column title="URL" data-index="url" ellipsis tooltip :width="200" />
              <a-table-column title="状态" :width="120">
                <template #cell="{ record }">
                  <a-space direction="vertical" size="mini">
                    <a-tag v-if="record.is_active" color="green" size="small" bordered>
                      <template #icon><icon-check-circle /></template>
                      启用
                    </a-tag>
                    <a-tag v-else color="gray" size="small" bordered>
                      <template #icon><icon-close-circle /></template>
                      停用
                    </a-tag>

                    <a-popover v-if="record.last_fetch_status === 'error'" position="bottom">
                      <a-tag color="red" size="small" class="cursor-pointer" bordered>
                        <template #icon><icon-exclamation-circle /></template>
                        抓取失败
                      </a-tag>
                      <template #content>
                        <div class="max-w-xs text-red-500 text-xs">{{ record.error_message }}</div>
                      </template>
                    </a-popover>
                    <a-tag v-else-if="record.last_fetch_status === 'success'" color="blue" size="small" bordered>
                      <template #icon><icon-check /></template>
                      正常
                    </a-tag>
                    <a-tag v-else color="orange" size="small" bordered>
                      <template #icon><icon-loading /></template>
                      Pending
                    </a-tag>
                  </a-space>
                </template>
              </a-table-column>
              <a-table-column title="文章数" data-index="articles_count" :width="100" align="center">
                <template #cell="{ record }">
                  <a-badge :count="record.articles_count" :max-count="999" :offset="[10, -2]">
                    <icon-book class="text-gray-400 text-lg" />
                  </a-badge>
                </template>
              </a-table-column>
              <a-table-column title="最后更新" data-index="last_fetched_at" :width="180">
                <template #cell="{ record }">
                  <a-tooltip :content="record.last_fetched_at ? new Date(record.last_fetched_at).toLocaleString() : '从未更新'">
                    <span class="text-gray-500 text-sm">
                      {{ record.last_fetched_at ? dayjs(record.last_fetched_at).fromNow() : '-' }}
                    </span>
                  </a-tooltip>
                </template>
              </a-table-column>
              <a-table-column title="操作" :width="180" fixed="right" align="center">
                <template #cell="{ record }">
                  <a-space>
                    <a-tooltip content="查看文章">
                      <a-button type="text" shape="circle" size="small" @click="$router.push(`/rss/articles?feed_id=${record.id}`)">
                        <icon-eye />
                      </a-button>
                    </a-tooltip>
                    <a-tooltip content="刷新">
                      <a-button type="text" shape="circle" size="small" @click="_handleRefreshSingle(record)" :loading="loadingStore.isLoading(`rss-refresh-single-${record.id}`)">
                        <icon-sync />
                      </a-button>
                    </a-tooltip>
                    <a-dropdown trigger="hover">
                      <a-button type="text" shape="circle" size="small">
                        <icon-more />
                      </a-button>
                      <template #content>
                        <a-doption @click="_openEditModal(record)">
                          <template #icon><icon-edit /></template>
                          编辑
                        </a-doption>
                        <a-doption @click="_handleToggleActive(record)">
                          <template #icon><icon-stop v-if="record.is_active" /><icon-play-arrow v-else /></template>
                          {{ record.is_active ? '停用' : '启用' }}
                        </a-doption>
                        <a-doption @click="_handleDelete(record)" class="text-red-500">
                          <template #icon><icon-delete /></template>
                          删除
                        </a-doption>
                      </template>
                    </a-dropdown>
                  </a-space>
                </template>
              </a-table-column>
            </template>
          </a-table>
        </a-card>
      </div>
    </div>

    <!-- 添加/编辑 订阅源弹窗 -->
    <a-modal v-model:visible="modalVisible" :title="isEdit ? '编辑订阅源' : '添加订阅源'" @ok="_handleModalOk" @cancel="_handleModalCancel">
      <a-form :model="form" ref="_formRef" layout="vertical">
        <a-form-item field="url" label="RSS URL" :rules="[{ required: true, message: '请输入 RSS 地址' }]">
          <a-input v-model="form.url" placeholder="https://example.com/rss.xml" allow-clear>
            <template #prefix>
              <icon-link />
            </template>
          </a-input>
        </a-form-item>
        <template v-if="isEdit">
          <a-form-item field="title" label="标题">
            <a-input v-model="form.title" placeholder="可选，留空则使用源标题" />
          </a-form-item>
          <a-form-item field="group_ids" label="分组">
             <a-tree-select
              v-model="form.group_ids"
              :data="groupTreeData"
              placeholder="选择分组"
              multiple
              allow-clear
              :field-names="{key: 'key', title: 'title', children: 'children'}"
            />
          </a-form-item>
          <a-form-item field="is_active" label="状态">
            <a-switch v-model="form.is_active" type="round">
              <template #checked>启用</template>
              <template #unchecked>停用</template>
            </a-switch>
          </a-form-item>
           <a-form-item field="is_whitelisted" label="清理白名单">
             <a-checkbox v-model="form.is_whitelisted">
               设为白名单 (数据清理时保留)
             </a-checkbox>
          </a-form-item>
        </template>
        <template v-else>
           <a-form-item field="group_ids" label="分组">
             <a-tree-select
              v-model="form.group_ids"
              :data="groupTreeData"
              placeholder="选择分组"
              multiple
              allow-clear
               :field-names="{key: 'key', title: 'title', children: 'children'}"
            />
          </a-form-item>
        </template>
      </a-form>
    </a-modal>

    <!-- 分组管理弹窗 (Moved to GroupTree.vue, this duplicate can be removed or kept if triggered from elsewhere, but we removed the logic earlier. Let's remove the whole modal) -->
    <!-- 批量设置分组弹窗 -->
     <a-modal v-model:visible="batchGroupModalVisible" title="批量设置分组" @ok="_handleBatchGroupOk" @cancel="batchGroupModalVisible = false">
      <a-form :model="batchGroupForm" layout="vertical">
        <div class="mb-4 text-gray-600">
          已选择 {{ selectedKeys.length }} 个订阅源
        </div>
        <a-form-item field="group_ids" label="选择分组">
           <a-tree-select
              v-model="batchGroupForm.group_ids"
              :data="groupTreeData"
              placeholder="选择分组"
              multiple
              allow-clear
               :field-names="{key: 'key', title: 'title', children: 'children'}"
            />
        </a-form-item>
      </a-form>
    </a-modal>

    <!-- 数据清理弹窗 -->
    <a-modal v-model:visible="cleanupModalVisible" title="数据清理" width="800px" :footer="false">
      <div class="mb-4">
        <a-alert type="warning">
          以下订阅源文章数量少于 3 篇，建议清理。勾选 "白名单" 可防止误删。
        </a-alert>
        <div class="mt-4 flex justify-between">
           <a-button status="danger" @click="_handleExecuteCleanup" :disabled="cleanupSelectedKeys.length === 0">
             清理选中 ({{ cleanupSelectedKeys.length }})
           </a-button>
           <a-button @click="_loadCleanupCandidates">
             <template #icon><icon-refresh /></template>
             刷新列表
           </a-button>
        </div>
      </div>
      <a-table
        :data="cleanupCandidates"
        :pagination="false"
        :loading="loadingStore.isLoading('rss-cleanup-candidates')"
        v-model:selectedKeys="cleanupSelectedKeys"
        row-key="id"
        :row-selection="{ type: 'checkbox', showCheckedAll: true }"
        :scroll="{ y: 400 }"
      >
        <template #columns>
           <a-table-column title="标题" data-index="title" />
           <a-table-column title="文章数" data-index="articles_count" :width="100" />
           <a-table-column title="白名单" :width="100">
             <template #cell="{ record }">
               <a-switch size="small" v-model="record.is_whitelisted" @change="(val) => _handleToggleWhitelist(record, val)" />
             </template>
           </a-table-column>
        </template>
      </a-table>
    </a-modal>

  </div>
</template>

<script setup>
import { Message, Modal } from "@arco-design/web-vue";
import dayjs from "dayjs";
import relativeTime from "dayjs/plugin/relativeTime";
import { computed, onMounted, reactive, ref } from "vue";
import GroupTree from "./components/GroupTree.vue";
import {
	addFeed,
	autoClassifyFeeds,
	batchDeleteFeeds,
	deleteFeed,
	executeCleanup,
	getCleanupCandidates,
	getFeeds,
	getGroupsTree,
	importOpml,
	refreshFeed,
	refreshFeeds,
	setFeedGroups,
	updateFeed,
} from "../../api/rss";
import { useLoadingStore } from "../../store/loading";
import "dayjs/locale/zh-cn";

dayjs.extend(relativeTime);
dayjs.locale("zh-cn");

// 状态定义
const loadingStore = useLoadingStore();
const feeds = ref([]);
const _groups = ref([]); // 原始分组数据
const groupTreeData = ref([]); // 树形结构数据
const groupTreeRef = ref(null);
const modalVisible = ref(false);
const isEdit = ref(false);
const currentId = ref(null);
const _formRef = ref(null);
const selectedKeys = ref([]);
const selectedGroupKeys = ref(["all"]); // 选中的分组ID
const _rowSelection = {
	type: "checkbox",
	showCheckedAll: true,
	onlyCurrent: false,
};

// 分组弹窗
const _groupModalVisible = ref(false);
const _isGroupEdit = ref(false);
const _currentGroupId = ref(null);
const _groupForm = reactive({
	name: "",
	parent_id: null,
});

// 批量分组弹窗
const batchGroupModalVisible = ref(false);
const batchGroupForm = reactive({
	group_ids: [],
});

// 清理弹窗
const cleanupModalVisible = ref(false);
const cleanupCandidates = ref([]);
const cleanupSelectedKeys = ref([]);

const form = reactive({
	url: "",
	title: "",
	group_ids: [],
	is_active: true,
	is_whitelisted: false,
});

/**
 * 转换分组数据为 Tree 组件需要的格式
 */
const transformGroupToTree = (groups) => {
	return groups.map((g) => ({
		key: g.id,
		title: g.name,
		children: g.children ? transformGroupToTree(g.children) : [],
		isLeaf: !g.children || g.children.length === 0,
	}));
};

/**
 * 加载所有分组树
 */
const loadGroups = async () => {
	try {
		const tree = await getGroupsTree({ loading: "rss-groups" });
		// 添加 "全部" 节点
		groupTreeData.value = [
			{ key: "all", title: "全部订阅源", children: [] },
			...transformGroupToTree(tree),
		];
	} catch (_error) {
		Message.error("加载分组失败");
	} finally {
		loadingStore.stopLoading("rss-groups");
	}
};

/**
 * 加载所有订阅源列表
 */
const loadFeeds = async () => {
	try {
		feeds.value = await getFeeds({ loading: "rss-feeds" });
		if (groupTreeRef.value) {
			groupTreeRef.value.refresh();
		}
	} catch (_error) {
		Message.error("加载订阅源失败");
	} finally {
		loadingStore.stopLoading("rss-feeds");
	}
};

// 计算属性：根据选中分组过滤订阅源
const filteredFeeds = computed(() => {
	if (
		!selectedGroupKeys.value ||
		!selectedGroupKeys.value.length ||
		selectedGroupKeys.value.includes("all")
	) {
		return feeds.value;
	}
	let groupId = selectedGroupKeys.value[0];
	if (typeof groupId === "string" && groupId.startsWith("group_")) {
		groupId = parseInt(groupId.replace("group_", ""), 10);
	}
	return feeds.value.filter((feed) => {
		// 检查 feed 是否属于该分组 (feed.groups 包含该 ID)
		return feed.groups?.some((g) => g.id === groupId);
	});
});

const _handleGroupSelect = (keys, _node) => {
	selectedGroupKeys.value = keys;
};

// ================== 分组管理逻辑 ==================
// Removed duplicate group management, now handled by GroupTree

// ================== 批量分组逻辑 ==================

const _openBatchGroupModal = () => {
	batchGroupForm.group_ids = [];
	batchGroupModalVisible.value = true;
};

const _handleBatchGroupOk = async () => {
	try {
		const promises = selectedKeys.value.map((feedId) =>
			setFeedGroups(feedId, batchGroupForm.group_ids),
		);
		await Promise.all(promises);
		Message.success("批量设置分组成功");
		batchGroupModalVisible.value = false;
		loadFeeds();
		selectedKeys.value = [];
	} catch (_error) {
		Message.error("部分操作失败");
	}
};

// ================== 清理逻辑 ==================

const _openCleanupModal = () => {
	cleanupModalVisible.value = true;
	_loadCleanupCandidates();
};

const _loadCleanupCandidates = async () => {
	try {
		cleanupCandidates.value = await getCleanupCandidates(3);
		// 默认选中非白名单的
		cleanupSelectedKeys.value = cleanupCandidates.value
			.filter((f) => !f.is_whitelisted)
			.map((f) => f.id);
	} catch (_error) {
		Message.error("加载清理列表失败");
	}
};

const _handleToggleWhitelist = async (record, val) => {
	try {
		await updateFeed(record.id, { is_whitelisted: val });
		Message.success(val ? "已加入白名单" : "已移除白名单");
	} catch (_error) {
		Message.error("操作失败");
		record.is_whitelisted = !val; // revert
	}
};

const _handleExecuteCleanup = async () => {
	try {
		await executeCleanup(cleanupSelectedKeys.value);
		Message.success(`成功清理 ${cleanupSelectedKeys.value.length} 个订阅源`);
		_loadCleanupCandidates();
		loadFeeds(); // refresh main list
	} catch (_error) {
		Message.error("清理失败");
	}
};

// ================== 现有逻辑适配 ==================

const _handleImportOpml = async (option) => {
	const { fileItem } = option;
	const reader = new FileReader();
	reader.onload = async (e) => {
		const content = e.target.result;
		try {
			const res = await importOpml(content);
			Message.success(res.message || "导入成功");
			loadFeeds();
		} catch (_err) {
			Message.error("导入失败");
		}
	};
	reader.readAsText(fileItem.file);
};

const _handleBatchDelete = () => {
	Modal.confirm({
		title: "确认批量删除",
		content: `确定要删除选中的 ${selectedKeys.value.length} 个订阅源吗？`,
		onOk: async () => {
			try {
				await batchDeleteFeeds(selectedKeys.value);
				Message.success("批量删除成功");
				selectedKeys.value = [];
				loadFeeds();
			} catch (_error) {
				Message.error("批量删除失败");
			}
		},
	});
};

const _openAddModal = () => {
	isEdit.value = false;
	currentId.value = null;
	form.url = "";
	form.title = "";
	form.group_ids = [];
	form.is_active = true;
	form.is_whitelisted = false;
	modalVisible.value = true;
};

const _openEditModal = (record) => {
	isEdit.value = true;
	currentId.value = record.id;
	form.url = record.url;
	form.title = record.title;
	form.group_ids = record.groups ? record.groups.map((g) => g.id) : [];
	form.is_active = record.is_active;
	form.is_whitelisted = record.is_whitelisted;
	modalVisible.value = true;
};

const _handleModalOk = async () => {
	if (!form.url) {
		Message.warning("请输入 RSS 地址");
		return false;
	}

	try {
		if (isEdit.value) {
			await updateFeed(currentId.value, { ...form });
			Message.success("更新成功");
		} else {
			await addFeed({ ...form });
			Message.success("添加成功，正在后台抓取...");
		}
		modalVisible.value = false;
		loadFeeds();
	} catch (_error) {
		Message.error(isEdit.value ? "更新失败" : "添加失败");
		return false;
	}
};

const _handleModalCancel = () => {
	modalVisible.value = false;
};

const _handleToggleActive = async (record) => {
	try {
		await updateFeed(record.id, { is_active: !record.is_active });
		Message.success(record.is_active ? "已停用" : "已启用");
		loadFeeds();
	} catch (_error) {
		Message.error("操作失败");
	}
};

const _handleDelete = (record) => {
	Modal.confirm({
		title: "确认删除",
		content: `确定要删除订阅源 "${record.title || record.url}" 吗？相关的文章也将被删除。`,
		okText: "删除",
		okButtonProps: { status: "danger" },
		onOk: async () => {
			try {
				await deleteFeed(record.id);
				Message.success("删除成功");
				loadFeeds();
			} catch (_error) {
				Message.error("删除失败");
			}
		},
	});
};

const _handleRefreshAll = async () => {
	try {
		await refreshFeeds({ loading: "rss-refresh" });
		Message.success("全量刷新任务已启动");
		setTimeout(loadFeeds, 1000);
	} catch (_error) {
		Message.error("刷新失败");
	} finally {
		loadingStore.stopLoading("rss-refresh");
	}
};

const _handleRefreshSingle = async (record) => {
	try {
		await refreshFeed(record.id, {
			loading: `rss-refresh-single-${record.id}`,
		});
		Message.success("刷新任务已启动");
		setTimeout(loadFeeds, 1000);
	} catch (_error) {
		Message.error("刷新失败");
	} finally {
		loadingStore.stopLoading(`rss-refresh-single-${record.id}`);
	}
};

const _handleAutoClassify = async () => {
	try {
		// Message.loading({ content: "正在智能分类...", id: "auto_classify", duration: 0 });
		loadingStore.startLoading("auto_classify");
		const res = await autoClassifyFeeds({ loading: "auto_classify" });
		Message.success({
			content: `分类完成，已处理 ${res.count} 个订阅源`,
			id: "auto_classify",
		});
		loadGroups();
		loadFeeds();
	} catch (_error) {
		Message.error({ content: "分类失败", id: "auto_classify" });
	} finally {
		loadingStore.stopLoading("auto_classify");
	}
};

onMounted(() => {
	loadFeeds();
	loadGroups();
	selectedGroupKeys.value = ["all"];
});
</script>

<style scoped>
:deep(.arco-tree-node-title-text) {
    font-size: 14px;
}
</style>
