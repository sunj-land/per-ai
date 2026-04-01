<!--
 * @Author: Channel Management
 * @Date: 2026-03-16
 * @Description: Channel 管理主页面
 -->
<template>
  <div class="channel-container">
    <a-card title="Channel 管理" :bordered="false">
      <template #extra>
        <a-button type="primary" @click="handleCreate">
          <template #icon><icon-plus /></template>
          创建 Channel
        </a-button>
      </template>

      <BlockLoading :loading="loading" tip="Loading Channels...">
      <a-table
        :data="data"
        :loading="loading"
        :pagination="false"
        row-key="id"
      >
        <template #columns>
          <a-table-column title="名称" data-index="name" />
          <a-table-column title="类型" data-index="type">
             <template #cell="{ record }">
              <a-tag color="arcoblue">{{ record.type }}</a-tag>
            </template>
          </a-table-column>
          <a-table-column title="描述" data-index="description" ellipsis />
          <a-table-column title="状态" data-index="is_active">
            <template #cell="{ record }">
              <a-switch
                v-model="record.is_active"
                @change="(val) => handleStatusChange(record, val)"
                :loading="record.statusLoading"
              />
            </template>
          </a-table-column>
          <a-table-column title="创建时间" data-index="created_at">
             <template #cell="{ record }">
              {{ new Date(record.created_at).toLocaleString() }}
            </template>
          </a-table-column>
          <a-table-column title="操作" :width="280">
            <template #cell="{ record }">
              <a-space>
                <a-button type="text" size="small" @click="handleEdit(record)">
                  <template #icon><icon-edit /></template>
                  编辑
                </a-button>
                <a-button type="text" size="small" @click="handleSend(record)">
                  <template #icon><icon-send /></template>
                  发送
                </a-button>
                <a-button type="text" size="small" @click="handleHistory(record)">
                  <template #icon><icon-history /></template>
                  历史
                </a-button>
                <a-popconfirm content="确认删除该 Channel 吗？" @ok="handleDelete(record)">
                  <a-button type="text" status="danger" size="small">
                    <template #icon><icon-delete /></template>
                    删除
                  </a-button>
                </a-popconfirm>
              </a-space>
            </template>
          </a-table-column>
        </template>
      </a-table>
      </BlockLoading>
    </a-card>

    <!-- Components -->
    <operate-modal
      v-model="operateVisible"
      :channel-id="currentId"
      :initial-data="currentData"
      @success="fetchData"
    />

    <send-modal
      v-model="sendVisible"
      :channel-id="currentId"
      @success="fetchData"
    />

    <history-drawer
      v-model="historyVisible"
      :channel-id="currentId"
    />
  </div>
</template>

<script setup>
import { Message } from "@arco-design/web-vue";
import { computed, onMounted, ref } from "vue";
import { deleteChannel, getChannels, updateChannel } from "@/api/channel";
import { useLoadingStore } from "@/store/loading";
import BlockLoading from "@/components/loading/BlockLoading.vue";
import OperateModal from "./components/operate-modal.vue";
import SendModal from "./components/send-modal.vue";
import HistoryDrawer from "./components/history-drawer.vue";

const loadingStore = useLoadingStore();
const loading = computed(() => loadingStore.isLoading("channel-list"));
const data = ref([]);

// Modal states
const operateVisible = ref(false);
const sendVisible = ref(false);
const historyVisible = ref(false);

const currentId = ref("");
const currentData = ref({});

const fetchData = async () => {
	// loading handled by store via 'channel-list'
	try {
		const res = await getChannels();
		data.value = res;
	} catch (error) {
		console.error(error);
	} finally {
		// loading handled by store
	}
};

const handleCreate = () => {
	currentId.value = "";
	currentData.value = {};
	operateVisible.value = true;
};

const handleEdit = (record) => {
	currentId.value = record.id;
	currentData.value = { ...record };
	operateVisible.value = true;
};

const handleDelete = async (record) => {
	try {
		await deleteChannel(record.id);
		Message.success("删除成功");
		fetchData();
	} catch (error) {
		console.error(error);
	}
};

const handleStatusChange = async (record, val) => {
	record.statusLoading = true;
	try {
		// Suppress global loading, handle locally
		await updateChannel(record.id, { is_active: val }, { loading: false });
		Message.success(`已${val ? "启用" : "禁用"}`);
	} catch (error) {
		record.is_active = !val; // revert
		console.error(error);
	} finally {
		record.statusLoading = false;
	}
};

const handleSend = (record) => {
	currentId.value = record.id;
	sendVisible.value = true;
};

const handleHistory = (record) => {
	currentId.value = record.id;
	historyVisible.value = true;
};

onMounted(() => {
	fetchData();
});
</script>

<style scoped>
.channel-container {
  padding: 20px;
}
</style>
