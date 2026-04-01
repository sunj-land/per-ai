<template>
  <div class="skill-list-container h-full flex flex-col gap-4">
    <div class="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-3">
      <div class="flex flex-col md:flex-row gap-2 w-full lg:w-auto">
        <a-input-search v-model="searchQuery" placeholder="搜索 Skill" class="w-full md:w-72" allow-clear />
        <a-select v-model="selectedTag" placeholder="标签过滤" allow-clear class="w-full md:w-40">
          <a-option v-for="tag in availableTags" :key="tag" :value="tag">{{ tag }}</a-option>
        </a-select>
      </div>
      <div class="flex flex-wrap gap-2">
        <a-button @click="handleSync" :loading="loadingStore.isLoading('skill-sync')"><template #icon><icon-sync /></template>同步本地</a-button>
        <a-button @click="handleSearchHub" :loading="loadingStore.isLoading('skill-hub-search')"><template #icon><icon-refresh /></template>搜索Hub</a-button>
        <a-button type="primary" @click="showCreateModal"><template #icon><icon-plus /></template>创建Skill</a-button>
        <a-button @click="showInstallModal"><template #icon><icon-download /></template>安装Skill</a-button>
      </div>
    </div>

    <a-alert v-if="installProgress.visible" type="info" :title="installProgress.title" :description="installProgress.lastMessage" closable @close="handleCloseProgress" />

    <a-tabs type="rounded" default-active-key="installed">
      <a-tab-pane key="installed" title="已安装">
        <a-table :data="filteredSkills" :loading="loadingStore.isLoading('skill-list')" :pagination="{ pageSize: 10, showTotal: true, showJumper: true, showPageSize: true }" class="flex-1 overflow-hidden">
          <template #columns>
            <a-table-column title="名称" data-index="name">
              <template #cell="{ record }">
                <span v-html="highlightText(record.name)"></span>
              </template>
            </a-table-column>
            <a-table-column title="版本" data-index="version" :width="120" />
            <a-table-column title="描述" data-index="description">
              <template #cell="{ record }">
                <span class="truncate block max-w-xs" :title="record.description" v-html="highlightText(record.description || '')"></span>
              </template>
            </a-table-column>
            <a-table-column title="状态" data-index="install_status" :width="120">
              <template #cell="{ record }">
                <a-tag :color="record.install_status === 'installed' ? 'green' : 'orange'">{{ record.install_status }}</a-tag>
              </template>
            </a-table-column>
            <a-table-column title="操作" :width="220">
              <template #cell="{ record }">
                <a-space>
                  <a-button type="text" size="small" @click="openDetail(record)"><template #icon><icon-edit /></template>编辑</a-button>
                  <a-button type="text" status="warning" size="small" @click="handleUpgrade(record)"><template #icon><icon-refresh /></template>更新</a-button>
                  <a-button type="text" status="danger" size="small" @click="handleUninstall(record)"><template #icon><icon-delete /></template>卸载</a-button>
                </a-space>
              </template>
            </a-table-column>
          </template>
        </a-table>
      </a-tab-pane>

      <a-tab-pane key="hub" title="Hub结果">
        <a-table :data="filteredHubSkills" :loading="loadingStore.isLoading('skill-hub-search')" :pagination="{ pageSize: 10, showTotal: true }">
          <template #columns>
            <a-table-column title="名称" data-index="name" />
            <a-table-column title="版本" data-index="version" :width="140" />
            <a-table-column title="标签" :width="200">
              <template #cell="{ record }">
                <a-space>
                  <a-tag v-for="tag in record.tags || []" :key="`${record.name}-${tag}`">{{ tag }}</a-tag>
                </a-space>
              </template>
            </a-table-column>
            <a-table-column title="描述" data-index="description" />
            <a-table-column title="操作" :width="120">
              <template #cell="{ record }">
                <a-button type="primary" size="small" @click="handleInstallFromHub(record)">安装</a-button>
              </template>
            </a-table-column>
          </template>
        </a-table>
      </a-tab-pane>

      <a-tab-pane key="records" title="安装记录">
        <a-table :data="installRecords" :loading="loadingStore.isLoading('skill-records')" :pagination="{ pageSize: 10, showTotal: true }">
          <template #columns>
            <a-table-column title="任务ID" data-index="task_id" />
            <a-table-column title="Skill" data-index="skill_name" />
            <a-table-column title="版本" data-index="target_version" />
            <a-table-column title="操作" data-index="operation" :width="120" />
            <a-table-column title="状态" :width="120">
              <template #cell="{ record }">
                <a-tag :color="record.status === 'success' ? 'green' : record.status === 'failed' ? 'red' : 'blue'">
                  {{ record.status }}
                </a-tag>
              </template>
            </a-table-column>
            <a-table-column title="结果" data-index="result_message" />
          </template>
        </a-table>
      </a-tab-pane>
    </a-tabs>

    <a-modal v-model:visible="createModalVisible" title="创建 Skill" @ok="handleCreate" :ok-loading="loadingStore.isLoading('skill-create')">
      <a-form :model="createForm" ref="createFormRef">
        <a-form-item field="name" label="Skill 名称" :rules="[{ required: true, message: '请输入名称' }]">
          <a-input v-model="createForm.name" placeholder="my-awesome-skill" />
        </a-form-item>
        <a-form-item field="description" label="描述" :rules="[{ required: true, message: '请输入描述' }]">
          <a-textarea v-model="createForm.description" placeholder="请输入描述" />
        </a-form-item>
      </a-form>
    </a-modal>

    <a-modal v-model:visible="installModalVisible" title="安装 Skill" @ok="handleInstall" :ok-loading="loadingStore.isLoading('skill-install')">
      <a-form :model="installForm">
        <a-form-item field="name" label="Skill 名称">
          <a-input v-model="installForm.name" placeholder="例如 weather" />
        </a-form-item>
        <a-form-item field="version" label="版本">
          <a-input v-model="installForm.version" placeholder="留空默认最新版本" />
        </a-form-item>
        <a-form-item field="url" label="URL 安装">
          <a-input v-model="installForm.url" placeholder="https://example.com/my_skill.py" />
        </a-form-item>
      </a-form>
    </a-modal>

    <a-drawer
      v-model:visible="drawerVisible"
      width="80%"
      :title="currentSkill ? `${currentSkill.name} 详情` : 'Skill 详情'"
      :footer="false"
      unmount-on-close
    >
      <SkillDetail v-if="currentSkill" :skill-id="currentSkill.id" @refresh="fetchSkills" />
    </a-drawer>
  </div>
</template>

<script setup>
import { Message } from "@arco-design/web-vue";
import { computed, onBeforeUnmount, onMounted, reactive, ref } from "vue";
import {
	createSkill,
	getInstallRecords,
	getSkillList,
	installSkillByUrl,
	installSkillFromHub,
	searchSkillHub,
	streamInstallProgress,
	syncSkills,
	uninstallSkill,
	upgradeSkill,
} from "@/api/agent-center";
import { useLoadingStore } from "@/store/loading";
import SkillDetail from "./SkillDetail.vue";

const loadingStore = useLoadingStore();

const skills = ref([]);
const hubSkills = ref([]);
const installRecords = ref([]);
const searchQuery = ref("");
const selectedTag = ref("");

const installModalVisible = ref(false);
const createModalVisible = ref(false);
const createFormRef = ref(null);

const drawerVisible = ref(false);
const currentSkill = ref(null);
const eventSource = ref(null);

const installProgress = reactive({
	visible: false,
	title: "",
	lastMessage: "",
});

const installForm = reactive({ name: "", version: "", url: "" });
const createForm = reactive({ name: "", description: "" });

const filteredSkills = computed(() => {
	const query = (searchQuery.value || "").toLowerCase();
	return skills.value.filter((skill) => {
		const textMatched =
			!query ||
			skill.name.toLowerCase().includes(query) ||
			skill.description?.toLowerCase().includes(query);
		const tagMatched =
			!selectedTag.value || (skill.tags || []).includes(selectedTag.value);
		return textMatched && tagMatched;
	});
});

const filteredHubSkills = computed(() => {
	const query = searchQuery.value.toLowerCase();
	return hubSkills.value.filter((skill) => {
		const textMatched =
			!query ||
			skill.name.toLowerCase().includes(query) ||
			skill.description?.toLowerCase().includes(query);
		const tagMatched =
			!selectedTag.value || (skill.tags || []).includes(selectedTag.value);
		return textMatched && tagMatched;
	});
});

const availableTags = computed(() => {
	const tags = new Set();
	[...skills.value, ...hubSkills.value].forEach((skill) => {
		(skill.tags || []).forEach((tag) => {
			tags.add(tag);
		});
	});
	return [...tags];
});

const fetchSkills = async () => {
	try {
		const res = await getSkillList();
		skills.value = res;
	} catch (err) {
		Message.error(`获取 Skill 列表失败: ${err.message}`);
	}
};

const handleSync = async () => {
	try {
		await syncSkills();
		Message.success("同步成功");
		fetchSkills();
	} catch (err) {
		Message.error(`同步失败: ${err.message}`);
	}
};

const handleSearchHub = async () => {
	try {
		const res = await searchSkillHub();
		hubSkills.value = res;
		Message.success("搜索完成");
	} catch (err) {
		Message.error(`搜索 Hub 失败: ${err.message}`);
	}
};

const fetchInstallRecords = async () => {
	try {
		const res = await getInstallRecords();
		installRecords.value = res;
	} catch (err) {
		Message.error(`获取安装记录失败: ${err.message}`);
	}
};

const highlightText = (value) => {
	if (!value) return "";
	if (!searchQuery.value) return value;
	const keyword = searchQuery.value.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
	return String(value).replace(
		new RegExp(`(${keyword})`, "ig"),
		"<mark>$1</mark>",
	);
};

const showCreateModal = () => {
	createForm.name = "";
	createForm.description = "";
	createModalVisible.value = true;
};

const handleCreate = async () => {
	const errors = await createFormRef.value.validate();
	if (errors) return;

	try {
		await createSkill(createForm);
		Message.success("创建成功");
		createModalVisible.value = false;
		fetchSkills();
	} catch (err) {
		Message.error(`创建失败: ${err.message}`);
	}
};

const showInstallModal = () => {
	installForm.name = "";
	installForm.version = "";
	installForm.url = "";
	installModalVisible.value = true;
};

const connectInstallStream = (taskId, title) => {
	if (eventSource.value) {
		eventSource.value.close();
	}
	installProgress.visible = true;
	installProgress.title = title;
	installProgress.lastMessage = "安装任务开始";
	eventSource.value = streamInstallProgress(
		taskId,
		(event) => {
			installProgress.lastMessage = `[${event.progress}%] ${event.message}`;
			if (event.status === "success") {
				Message.success("Skill 安装完成");
				fetchSkills();
				fetchInstallRecords();
				eventSource.value?.close();
			}
			if (event.status === "failed") {
				Message.error(event.message || "Skill 安装失败");
				eventSource.value?.close();
			}
		},
		() => {
			installProgress.lastMessage = "进度连接异常，可重试";
		},
	);
};

const handleInstall = async () => {
	try {
		if (installForm.url) {
			await installSkillByUrl(installForm.url);
		} else {
			await installSkillFromHub(installForm.name, installForm.version);
		}
		// Note: installation might be async, we'll listen to SSE for progress
		// But the initial request is done
		Message.success("安装任务已提交");
		installModalVisible.value = false;
		// Start listening for progress or just refresh records
		fetchInstallRecords();
	} catch (err) {
		Message.error(`安装请求失败: ${err.message}`);
	}
};

const handleInstallFromHub = async (record) => {
	try {
		const result = await installSkillFromHub(record.name, record.version);
		connectInstallStream(result.task_id, `${record.name}@${record.version}`);
	} catch (error) {
		console.error(error);
		Message.error("安装失败");
	}
};

const handleUninstall = async (record) => {
	try {
		await uninstallSkill(record.id);
		Message.success("卸载成功");
		fetchSkills();
		fetchInstallRecords();
	} catch (error) {
		console.error(error);
		Message.error("卸载失败");
	}
};

const handleUpgrade = async (record) => {
	try {
		const result = await upgradeSkill(record.id, null);
		connectInstallStream(result.task_id, `${record.name} 更新任务`);
	} catch (error) {
		console.error(error);
		Message.error("更新失败");
	}
};

const handleCloseProgress = () => {
	installProgress.visible = false;
};

const openDetail = (skill) => {
	currentSkill.value = skill;
	drawerVisible.value = true;
};

onMounted(() => {
	fetchSkills();
	fetchInstallRecords();
	handleSearchHub();
});

onBeforeUnmount(() => {
	eventSource.value?.close();
});
</script>
