<template>
  <div class="task-center-container">
    <a-page-header title="任务中心" subtitle="集中管理各类自动化任务" :show-back="false">
      <template #extra>
        <a-button type="primary" @click="openCreateModal">新建任务</a-button>
      </template>
    </a-page-header>

    <a-card class="content-card">
      <a-table :data="tasks" :loading="loadingStore.isLoading('task-list')" row-key="id">
        <template #columns>
          <a-table-column title="任务名称" data-index="name" />
          <a-table-column title="类型" data-index="type">
            <template #cell="{ record }">
              <a-tag color="blue" v-if="record.type === 'script'">Script</a-tag>
              <a-tag color="green" v-else-if="record.type === 'function'">Function</a-tag>
              <a-tag color="orange" v-else-if="record.type === 'webhook'">Webhook</a-tag>
              <a-tag color="purple" v-else-if="record.type === 'ai_dialogue'">AI Dialogue</a-tag>
              <a-tag v-else>{{ record.type }}</a-tag>
            </template>
          </a-table-column>
          <template v-if="true">
            <a-table-column title="调度方式" data-index="schedule_type">
               <template #cell="{ record }">
                 {{ record.schedule_type }} ({{ JSON.stringify(record.schedule_config) }})
               </template>
            </a-table-column>
          </template>
          <a-table-column title="状态" data-index="is_active">
            <template #cell="{ record }">
              <a-switch
                :model-value="record.is_active"
                @change="(val) => handleStatusChange(record, val)"
                :loading="loadingStore.isLoading(`task-status-${record.id}`)"
              />
            </template>
          </a-table-column>
          <a-table-column title="上次运行" data-index="last_run_at">
             <template #cell="{ record }">
               {{ formatDate(record.last_run_at) }}
             </template>
          </a-table-column>
          <a-table-column title="操作">
            <template #cell="{ record }">
              <a-space>
                <a-button size="small" type="primary" @click="handleRun(record)" :loading="loadingStore.isLoading(`task-run-${record.id}`)">立即运行</a-button>
                <a-button size="small" @click="openLogs(record)">日志</a-button>
                <a-button size="small" @click="openEditModal(record)">编辑</a-button>
                <a-popconfirm content="确认删除该任务？" @ok="handleDelete(record)">
                  <a-button size="small" status="danger">删除</a-button>
                </a-popconfirm>
              </a-space>
            </template>
          </a-table-column>
        </template>
      </a-table>
    </a-card>

    <!-- Create/Edit Modal -->
    <a-modal v-model:visible="modalVisible" :title="isEdit ? '编辑任务' : '新建任务'" @ok="handleSave">
      <a-form :model="form" layout="vertical">
        <a-form-item field="name" label="任务名称" required>
          <a-input v-model="form.name" placeholder="请输入任务名称" />
        </a-form-item>
        <a-form-item field="description" label="描述">
          <a-textarea v-model="form.description" placeholder="任务描述" />
        </a-form-item>
        <a-form-item field="type" label="任务类型" required>
          <a-select v-model="form.type" placeholder="选择类型">
            <a-option value="script">脚本 (Script)</a-option>
            <a-option value="function">内部函数 (Function)</a-option>
            <a-option value="webhook">Webhook</a-option>
            <a-option value="ai_dialogue">AI 对话 (AI Dialogue)</a-option>
          </a-select>
        </a-form-item>
        <a-form-item field="payload" label="执行内容" required>
          <a-textarea v-if="form.type === 'ai_dialogue'" v-model="form.payload" placeholder="请输入 AI 提示词 (Prompt)" :auto-size="{minRows: 3, maxRows: 10}" />
          <a-input v-else v-model="form.payload" placeholder="脚本路径 / 函数名 / URL" />
          <template #help>
            <span v-if="form.type === 'script'">Script: 绝对路径</span>
            <span v-else-if="form.type === 'function'">Function: 注册名(如 rss_fetch)</span>
            <span v-else-if="form.type === 'webhook'">Webhook: URL</span>
            <span v-else-if="form.type === 'ai_dialogue'">AI Dialogue: 输入提示词 (Prompt)</span>
          </template>
        </a-form-item>
        <a-form-item field="schedule_type" label="调度类型" required>
          <a-select v-model="form.schedule_type" placeholder="选择调度类型">
            <a-option value="interval">间隔 (Interval)</a-option>
            <a-option value="cron">Cron 表达式</a-option>
            <a-option value="date">特定时间 (Date)</a-option>
          </a-select>
        </a-form-item>
        <a-form-item field="schedule_config" label="调度配置 (JSON)" required>
          <a-textarea v-model="form.schedule_config_str" placeholder='例如: {"minutes": 30} 或 {"cron": "* * * * *"}' />
        </a-form-item>
      </a-form>
    </a-modal>

    <!-- Logs Drawer -->
    <a-drawer v-model:visible="logsVisible" title="任务日志" width="600px" :footer="false">
      <a-list :data="logs" :loading="loadingStore.isLoading('task-logs')">
        <template #item="{ item }">
          <a-list-item>
            <a-list-item-meta
              :title="formatDate(item.created_at)"
              :description="`耗时: ${item.duration ? item.duration.toFixed(2) + 'ms' : '-'}`"
            >
              <template #avatar>
                <a-tag :color="item.status === 'success' ? 'green' : item.status === 'failed' ? 'red' : 'blue'">
                  {{ item.status }}
                </a-tag>
              </template>
            </a-list-item-meta>
            <div class="log-output" v-if="item.output">
              <pre>{{ item.output }}</pre>
            </div>
          </a-list-item>
        </template>
      </a-list>
    </a-drawer>
  </div>
</template>

<script setup>
import { Message } from "@arco-design/web-vue";
import { onMounted, reactive, ref } from "vue";
import {
	createTask,
	deleteTask,
	getTaskLogs,
	getTasks,
	pauseTask,
	resumeTask,
	runTask,
	updateTask,
} from "@/api/task";
import { useLoadingStore } from "../../store/loading";

const loadingStore = useLoadingStore();
const tasks = ref([]);
const modalVisible = ref(false);
const isEdit = ref(false);
const logsVisible = ref(false);
const logs = ref([]);

const form = reactive({
	id: "",
	name: "",
	description: "",
	type: "script",
	payload: "",
	schedule_type: "interval",
	schedule_config_str: '{"minutes": 30}',
});

const formatDate = (dateStr) => {
	if (!dateStr) return "-";
	return new Date(dateStr).toLocaleString();
};

const fetchTasks = async () => {
	try {
		tasks.value = await getTasks();
	} catch (error) {
		console.error(error);
	}
};

const openCreateModal = () => {
	isEdit.value = false;
	Object.assign(form, {
		id: "",
		name: "",
		description: "",
		type: "script",
		payload: "",
		schedule_type: "interval",
		schedule_config_str: '{"minutes": 30}',
	});
	modalVisible.value = true;
};

const openEditModal = (record) => {
	isEdit.value = true;
	Object.assign(form, {
		id: record.id,
		name: record.name,
		description: record.description,
		type: record.type,
		payload: record.payload,
		schedule_type: record.schedule_type,
		schedule_config_str: JSON.stringify(record.schedule_config, null, 2),
	});
	modalVisible.value = true;
};

const handleSave = async () => {
	try {
		const data = {
			name: form.name,
			description: form.description,
			type: form.type,
			payload: form.payload,
			schedule_type: form.schedule_type,
			schedule_config: JSON.parse(form.schedule_config_str),
		};

		if (isEdit.value) {
			await updateTask(form.id, data, { loading: "task-update" });
			Message.success("更新成功");
		} else {
			await createTask(data, { loading: "task-create" });
			Message.success("创建成功");
		}
		modalVisible.value = false;
		fetchTasks();
	} catch (error) {
		Message.error(`保存失败: ${error.message}`);
	} finally {
		loadingStore.stopLoading("task-create");
		loadingStore.stopLoading("task-update");
	}
};

const handleDelete = async (record) => {
	try {
		await deleteTask(record.id, { loading: "task-delete" });
		Message.success("删除成功");
		fetchTasks();
	} catch (error) {
		console.error(error);
	} finally {
		loadingStore.stopLoading("task-delete");
	}
};

const handleStatusChange = async (record, val) => {
	try {
		const loadingKey = `task-status-${record.id}`;
		if (val) {
			await resumeTask(record.id, { loading: loadingKey });
		} else {
			await pauseTask(record.id, { loading: loadingKey });
		}
		record.is_active = val;
		Message.success(val ? "任务已启用" : "任务已暂停");
	} catch (error) {
		console.error(error);
	} finally {
		loadingStore.stopLoading(`task-status-${record.id}`);
	}
};

const handleRun = async (record) => {
	try {
		await runTask(record.id, { loading: `task-run-${record.id}` });
		Message.success("任务已触发");
	} catch (error) {
		console.error(error);
	} finally {
		loadingStore.stopLoading(`task-run-${record.id}`);
	}
};

const openLogs = async (record) => {
	logsVisible.value = true;
	logs.value = [];
	try {
		logs.value = await getTaskLogs(record.id, 20, { loading: "task-logs" });
	} catch (error) {
		console.error(error);
	} finally {
		loadingStore.stopLoading("task-logs");
	}
};

onMounted(() => {
	fetchTasks();
});
</script>

<style scoped>
.task-center-container {
  padding: 20px;
}
.content-card {
  margin-top: 16px;
}
.log-output {
  background: #f5f5f5;
  padding: 8px;
  border-radius: 4px;
  margin-top: 8px;
  max-height: 200px;
  overflow-y: auto;
  font-family: monospace;
  font-size: 12px;
  white-space: pre-wrap;
}
</style>
