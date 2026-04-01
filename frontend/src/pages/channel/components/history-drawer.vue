<!--
 * @Author: Message History
 * @Date: 2026-03-16
 * @Description: 消息历史抽屉
 -->
<template>
  <a-drawer
    v-model:visible="visible"
    title="消息历史"
    width="600px"
    @cancel="handleCancel"
    :footer="false"
  >
    <a-table
      :data="data"
      :loading="loading"
      :pagination="pagination"
      @page-change="handlePageChange"
      row-key="id"
      :scroll="{ x: 600 }"
    >
      <template #columns>
        <a-table-column title="内容" data-index="content" :width="200">
          <template #cell="{ record }">
            <a-typography-paragraph
              :ellipsis="{
                rows: 2,
                showTooltip: true,
                expandable: true,
              }"
            >
              {{ record.content }}
            </a-typography-paragraph>
          </template>
        </a-table-column>
        
        <a-table-column title="状态" data-index="status" :width="100">
          <template #cell="{ record }">
            <a-tag :color="getStatusColor(record.status)">
              {{ record.status }}
            </a-tag>
          </template>
        </a-table-column>

        <a-table-column title="结果" data-index="result" :width="150">
          <template #cell="{ record }">
             <a-typography-paragraph
              v-if="record.result"
              :ellipsis="{
                rows: 1,
                showTooltip: true,
              }"
              code
            >
              {{ record.result }}
            </a-typography-paragraph>
            <span v-else>-</span>
          </template>
        </a-table-column>

        <a-table-column title="时间" data-index="created_at" :width="180">
          <template #cell="{ record }">
            {{ new Date(record.created_at).toLocaleString() }}
          </template>
        </a-table-column>
      </template>
    </a-table>
  </a-drawer>
</template>

<script setup>
import { computed, reactive, ref, watch } from "vue";
import { getChannelMessages } from "@/api/channel";

const props = defineProps({
	modelValue: {
		type: Boolean,
		default: false,
	},
	channelId: {
		type: String,
		required: true,
	},
});

const emit = defineEmits(["update:modelValue"]);

const visible = computed({
	get: () => props.modelValue,
	set: (val) => emit("update:modelValue", val),
});

const loading = ref(false);
const data = ref([]);
const pagination = reactive({
	current: 1,
	pageSize: 20,
	total: 0, // Note: Backend currently doesn't return total count for pagination, infinite scroll might be better or simple prev/next
	showTotal: true,
});

// Since backend API: get_channel_messages(skip, limit) -> List[ChannelMessage]
// It does NOT return total count.
// So we can't fully support numbered pagination unless we add a count API or change the return format.
// For now, let's assume a large total or just fetch by page.
// If the backend returns less than limit, we know we reached the end.

const fetchData = async () => {
	if (!props.channelId) return;

	loading.value = true;
	try {
		const skip = (pagination.current - 1) * pagination.pageSize;
		const res = await getChannelMessages(props.channelId, {
			skip,
			limit: pagination.pageSize,
		});
		data.value = res;
		// Mock total for now to allow next page if full page returned
		if (res.length === pagination.pageSize) {
			pagination.total = skip + pagination.pageSize + 1; // Allow next
		} else {
			pagination.total = skip + res.length;
		}
	} catch (error) {
		console.error(error);
	} finally {
		loading.value = false;
	}
};

watch(
	() => props.modelValue,
	(val) => {
		if (val) {
			pagination.current = 1;
			fetchData();
		}
	},
);

const _handlePageChange = (page) => {
	pagination.current = page;
	fetchData();
};

const _handleCancel = () => {
	visible.value = false;
};

const _getStatusColor = (status) => {
	switch (status) {
		case "success":
			return "green";
		case "failed":
			return "red";
		case "pending":
			return "orange";
		default:
			return "gray";
	}
};
</script>
