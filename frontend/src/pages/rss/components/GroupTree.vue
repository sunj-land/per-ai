<template>
  <div
    ref="containerRef"
    class="group-tree-container flex flex-col h-full bg-gray-50 border-r border-gray-200 shrink-0"
    :style="{ width: `${width}px` }"
  >
    <div class="p-4 border-b border-gray-200 flex justify-between items-center shrink-0">
      <span class="font-bold text-gray-700">分组管理</span>
      <a-button type="text" size="small" @click="handleCreateGroup()">
        <template #icon><icon-plus /></template>
      </a-button>
    </div>

    <div class="flex-1 overflow-y-auto p-2">
      <a-tree
        ref="treeRef"
        v-if="treeData.length > 0"
        :data="treeData"
        :selected-keys="selectedKeys"
        @select="onSelect"
        block-node
        draggable
        @drop="onDrop"
        :virtual-list-props="virtualListProps"
        :default-selected-keys="['all']"
      >
        <template #icon="node">
          <icon-folder v-if="node.isGroup" />
          <icon-subscribe v-else />
        </template>
        <template #title="node">
          <a-dropdown trigger="contextMenu" position="bl" v-if="node.isGroup && node.key !== 'all'">
            <span class="tree-node-title w-full block" style="user-select: none;">{{ node.title }}</span>
            <template #content>
              <a-doption @click="handleEditGroup(node)">
                <template #icon><icon-edit /></template>
                重命名
              </a-doption>
              <a-doption @click="handleCreateGroup(node.key)">
                <template #icon><icon-plus /></template>
                添加子分组
              </a-doption>
              <a-doption @click="handleDeleteGroup(node)" class="text-red-500">
                <template #icon><icon-delete /></template>
                删除
              </a-doption>
            </template>
          </a-dropdown>
          <span v-else class="tree-node-title">{{ node.title }}</span>
        </template>
      </a-tree>
      <div v-else class="flex justify-center items-center h-full text-gray-400">
        加载中...
      </div>
    </div>

    <!-- Resizer handle -->
    <div class="resizer" @mousedown="startResize"></div>

    <!-- Group Modal -->
    <a-modal v-model:visible="modalVisible" :title="isEdit ? '重命名分组' : '创建分组'" @ok="onModalOk" @cancel="modalVisible = false">
      <a-form :model="form" layout="vertical">
        <a-form-item field="name" label="分组名称" :rules="[{ required: true, message: '请输入分组名称' }]">
          <a-input v-model="form.name" placeholder="例如：技术动态" />
        </a-form-item>
      </a-form>
    </a-modal>
  </div>
</template>

<script setup>
import { Message, Modal } from "@arco-design/web-vue";
import { computed, onMounted, onUnmounted, reactive, ref } from "vue";
import {
	createGroup,
	deleteGroup,
	getFeeds,
	getGroupsTree,
	updateGroup,
} from "../../../api/rss";

const props = defineProps({
	modelValue: {
		type: Array,
		default: () => ["all"],
	},
	showFeeds: {
		type: Boolean,
		default: true,
	},
});

const emit = defineEmits(["update:modelValue", "select", "refresh"]);

const width = ref(260);
const isResizing = ref(false);

const treeData = ref([]);
const rawGroups = ref([]);
const rawFeeds = ref([]);

const selectedKeys = computed({
	get: () => props.modelValue,
	set: (val) => emit("update:modelValue", val),
});

// Virtual scroll optimization for large tree (>500 nodes)
const virtualListProps = {
	height: "100%",
};

const modalVisible = ref(false);
const isEdit = ref(false);
const currentEditNode = ref(null);
const currentParentId = ref(null);
const form = reactive({ name: "" });

const startResize = (_e) => {
	isResizing.value = true;
	document.addEventListener("mousemove", handleResize);
	document.addEventListener("mouseup", stopResize);
};

const containerRef = ref(null);

const handleResize = (e) => {
	if (!isResizing.value || !containerRef.value) return;
	const rect = containerRef.value.getBoundingClientRect();
	const newWidth = e.clientX - rect.left;
	if (newWidth >= 200 && newWidth <= 400) {
		width.value = newWidth;
	}
};

const stopResize = () => {
	isResizing.value = false;
	document.removeEventListener("mousemove", handleResize);
	document.removeEventListener("mouseup", stopResize);
};

onUnmounted(() => {
	document.removeEventListener("mousemove", handleResize);
	document.removeEventListener("mouseup", stopResize);
});

// Build tree data combining groups and feeds
const buildTree = (groups, feeds) => {
	const processGroup = (group) => {
		const children = group.children ? group.children.map(processGroup) : [];

		if (props.showFeeds) {
			const groupFeeds = feeds.filter((f) =>
				f.groups?.some((g) => g.id === group.id),
			);
			groupFeeds.forEach((f) => {
				children.push({
					key: `feed_${f.id}`,
					title: f.title,
					isLeaf: true,
					isGroup: false,
					feedId: f.id,
				});
			});
		}

		return {
			key: `group_${group.id}`,
			title: group.name,
			groupId: group.id,
			isGroup: true,
			children,
			isLeaf: children.length === 0,
		};
	};

	const tree = groups.map(processGroup);

	// Add unassigned feeds to root if needed, or just let 'all' handle everything.
	return [
		{
			key: "all",
			title: "全部订阅源",
			isGroup: true,
			children: [],
			isLeaf: true,
		},
		...tree,
	];
};

const loadData = async () => {
	try {
		const [groupsRes, feedsRes] = await Promise.all([
			getGroupsTree({ loading: "rss-groups-tree" }),
			props.showFeeds
				? getFeeds({ loading: "rss-feeds" })
				: Promise.resolve([]),
		]);
		rawGroups.value = groupsRes;
		if (props.showFeeds) {
			rawFeeds.value = feedsRes;
		}
		treeData.value = buildTree(rawGroups.value, rawFeeds.value);
		emit("refresh");
	} catch (_error) {
		Message.error("加载分组数据失败");
	}
};

onMounted(() => {
	loadData();
});

const treeRef = ref(null);

const onSelect = (keys, data) => {
	selectedKeys.value = keys;
	emit("select", keys, data.node);

	if (data.node.isGroup && treeRef.value) {
		// try expand node, but it might toggle instead, or we let tree handle it natively via action-on-node-click
		// we removed action-on-node-click earlier, let's just toggle manually
		const node = treeRef.value.getNode
			? treeRef.value.getNode(data.node.key)
			: null;
		if (node) {
			treeRef.value.expandNode(data.node.key, !node.expanded);
		} else {
			treeRef.value.expandNode(data.node.key); // fallback
		}
	}
};

const onDrop = async ({ dragNode, dropNode, dropPosition }) => {
	if (dragNode.key === "all" || dropNode.key === "all") return;

	try {
		if (dragNode.isGroup) {
			// Move group
			let newParentId = null;
			if (dropPosition === 0 && dropNode.isGroup) {
				newParentId = dropNode.groupId;
			} else if (dropPosition !== 0) {
				// Find parent of dropNode
				const findParent = (nodes, targetKey, parentId = null) => {
					for (const node of nodes) {
						if (node.key === targetKey) return parentId;
						if (node.children) {
							const res = findParent(node.children, targetKey, node.groupId);
							if (res !== undefined) return res;
						}
					}
					return undefined;
				};
				newParentId = findParent(treeData.value, dropNode.key) || null;
			}
			await updateGroup(dragNode.groupId, { parent_id: newParentId });
		} else {
			// Move feed (not supported yet, or requires setFeedGroups)
			Message.info("暂不支持拖拽移动订阅源");
			return;
		}

		Message.success("移动成功");
		loadData();
	} catch (_e) {
		Message.error("移动失败");
	}
};

const handleCreateGroup = (parentId = null) => {
	isEdit.value = false;
	currentParentId.value = parentId
		? parseInt(parentId.replace("group_", ""), 10)
		: null;
	form.name = "";
	modalVisible.value = true;
};

const handleEditGroup = (node) => {
	isEdit.value = true;
	currentEditNode.value = node;
	form.name = node.title;
	modalVisible.value = true;
};

const handleDeleteGroup = (node) => {
	Modal.confirm({
		title: "确认删除分组",
		content: `确定要删除分组 "${node.title}" 吗？`,
		onOk: async () => {
			try {
				await deleteGroup(node.groupId);
				Message.success("删除成功");
				if (selectedKeys.value.includes(node.key)) {
					selectedKeys.value = ["all"];
				}
				loadData();
			} catch (_e) {
				Message.error("删除失败");
			}
		},
	});
};

const onModalOk = async () => {
	if (!form.name) {
		Message.warning("请输入分组名称");
		return;
	}
	try {
		if (isEdit.value) {
			await updateGroup(currentEditNode.value.groupId, { name: form.name });
			Message.success("重命名成功");
		} else {
			await createGroup(form.name, currentParentId.value);
			Message.success("创建成功");
		}
		modalVisible.value = false;
		loadData();
	} catch (_e) {
		Message.error("操作失败");
	}
};

// Expose refresh method
defineExpose({
	refresh: loadData,
});
</script>

<style scoped>
.group-tree-container {
  position: relative;
  transition: width 0.1s ease;
}

.resizer {
  position: absolute;
  top: 0;
  right: -3px;
  width: 6px;
  height: 100%;
  cursor: col-resize;
  z-index: 10;
}

.resizer:hover {
  background-color: var(--color-primary-light-3);
}

.tree-node-title {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
</style>
