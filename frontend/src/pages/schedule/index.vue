<template>
  <div class="h-full flex flex-col p-4">
    <div class="flex justify-between items-center mb-4">
      <div class="flex items-center gap-4">
        <h1 class="text-2xl font-bold">日程管理</h1>
        <a-radio-group v-model="viewType" type="button">
          <a-radio value="calendar">日历视图</a-radio>
          <a-radio value="list">列表视图</a-radio>
        </a-radio-group>
      </div>
      <a-button type="primary" @click="openCreateModal">
        <template #icon><icon-plus /></template>
        新建日程
      </a-button>
    </div>

    <div class="flex-1 overflow-hidden bg-white rounded-lg shadow p-4">
      <div v-if="viewType === 'calendar'" class="h-full">
        <a-calendar
          v-model="currentDate"
          :events="calendarEvents"
          @change="onDateChange"
          @select="onDateSelect"
        >
          <template #month="{ date }">
            <div v-if="getEventsForDate(date).length > 0" class="calendar-events">
              <div
                v-for="event in getEventsForDate(date)"
                :key="event.id"
                class="calendar-event-item"
                :class="`priority-${event.priority}`"
                @click.stop="openEditModal(event)"
              >
                {{ event.title }}
              </div>
            </div>
          </template>
        </a-calendar>
      </div>

      <div v-else class="h-full overflow-auto">
        <a-table
          :data="scheduleList"
          :loading="loading"
          :pagination="{
            total: total,
            current: page,
            pageSize: pageSize,
            showTotal: true,
            showPageSize: true
          }"
          @page-change="onPageChange"
          @page-size-change="onPageSizeChange"
        >
          <template #columns>
            <a-table-column title="标题" data-index="title"></a-table-column>
            <a-table-column title="开始时间" data-index="start_time">
              <template #cell="{ record }">
                {{ formatDate(record.start_time) }}
              </template>
            </a-table-column>
            <a-table-column title="结束时间" data-index="end_time">
              <template #cell="{ record }">
                {{ formatDate(record.end_time) }}
              </template>
            </a-table-column>
            <a-table-column title="优先级" data-index="priority">
              <template #cell="{ record }">
                <a-tag :color="getPriorityColor(record.priority)">
                  {{ getPriorityLabel(record.priority) }}
                </a-tag>
              </template>
            </a-table-column>
            <a-table-column title="操作">
              <template #cell="{ record }">
                <a-button type="text" size="small" @click="openEditModal(record)">编辑</a-button>
                <a-popconfirm content="确认删除该日程吗？" @ok="handleDelete(record.id)">
                  <a-button type="text" status="danger" size="small">删除</a-button>
                </a-popconfirm>
              </template>
            </a-table-column>
          </template>
        </a-table>
      </div>
    </div>

    <a-modal v-model:visible="modalVisible" :title="modalTitle" @cancel="closeModal" :footer="false">
      <ScheduleForm
        v-if="modalVisible"
        :initial-data="currentSchedule"
        @submit="handleSave"
        @cancel="closeModal"
      />
    </a-modal>
  </div>
</template>

<script setup>
import { Message } from "@arco-design/web-vue";
import dayjs from "dayjs";
import { computed, onMounted, ref, watch } from "vue";
import ScheduleForm from "./components/ScheduleForm.vue";
import {
	createSchedule,
	deleteSchedule,
	getSchedules,
	updateSchedule,
} from "../../api/schedule";

const viewType = ref("calendar");
const currentDate = ref(new Date());
const scheduleList = ref([]);
const loading = ref(false);
const total = ref(0);
const page = ref(1);
const pageSize = ref(10);

const modalVisible = ref(false);
const currentSchedule = ref(null);
const modalTitle = computed(() =>
	currentSchedule.value ? "编辑日程" : "新建日程",
);

const calendarEvents = computed(() => {
	// Map scheduleList to events format if needed by a-calendar
	// But standard a-calendar doesn't have events prop, we use slots
	return [];
});

const loadSchedules = async () => {
	loading.value = true;
	try {
		let params = {};
		if (viewType.value === "list") {
			params = {
				limit: pageSize.value,
				offset: (page.value - 1) * pageSize.value,
			};
		} else {
			// Load for current month
			const start = dayjs(currentDate.value).startOf("month").toISOString();
			const end = dayjs(currentDate.value).endOf("month").toISOString();
			params = {
				start_time: start,
				end_time: end,
				limit: 1000, // Load all for calendar
			};
		}

		const res = await getSchedules(params);
		if (Array.isArray(res)) {
			scheduleList.value = res;
			// If backend returns list, we assume total is length if not paginated
			// Wait, backend api returns list directly.
			// I need to update backend to support pagination metadata if I want real pagination.
			// For now, let's assume simple list.
			total.value = res.length;
		}
	} catch (error) {
		console.error(error);
		Message.error("加载日程失败");
	} finally {
		loading.value = false;
	}
};

onMounted(() => {
	loadSchedules();
});

watch([viewType, currentDate, page, pageSize], () => {
	loadSchedules();
});

const onDateChange = (date) => {
	currentDate.value = date;
};

const onDateSelect = (date) => {
	currentDate.value = date;
};

const getEventsForDate = (date) => {
	const dateStr = dayjs(date).format("YYYY-MM-DD");
	return scheduleList.value.filter(
		(s) => dayjs(s.start_time).format("YYYY-MM-DD") === dateStr,
	);
};

const formatDate = (date) => {
	return date ? dayjs(date).format("YYYY-MM-DD HH:mm") : "-";
};

const getPriorityColor = (priority) => {
	const map = {
		high: "red",
		medium: "orange",
		low: "green",
	};
	return map[priority] || "gray";
};

const getPriorityLabel = (priority) => {
	const map = {
		high: "高",
		medium: "中",
		low: "低",
	};
	return map[priority] || "普通";
};

const openCreateModal = () => {
	currentSchedule.value = null;
	modalVisible.value = true;
};

const openEditModal = (schedule) => {
	currentSchedule.value = JSON.parse(JSON.stringify(schedule));
	modalVisible.value = true;
};

const closeModal = () => {
	modalVisible.value = false;
	currentSchedule.value = null;
};

const handleSave = async (formData) => {
	try {
		if (currentSchedule.value?.id) {
			await updateSchedule(currentSchedule.value.id, formData);
			Message.success("更新成功");
		} else {
			await createSchedule(formData);
			Message.success("创建成功");
		}
		closeModal();
		loadSchedules();
	} catch (error) {
		console.error(error);
		Message.error("保存失败");
	}
};

const handleDelete = async (id) => {
	try {
		await deleteSchedule(id);
		Message.success("删除成功");
		loadSchedules();
	} catch (error) {
		console.error(error);
		Message.error("删除失败");
	}
};

const onPageChange = (current) => {
	page.value = current;
};

const onPageSizeChange = (size) => {
	pageSize.value = size;
	page.value = 1;
};
</script>

<style scoped>
.calendar-events {
  display: flex;
  flex-direction: column;
  gap: 2px;
  max-height: 80px;
  overflow-y: auto;
}

.calendar-event-item {
  font-size: 12px;
  padding: 2px 4px;
  border-radius: 2px;
  cursor: pointer;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  background-color: var(--color-fill-2);
}

.priority-high {
  background-color: rgba(var(--red-6), 0.1);
  color: rgb(var(--red-6));
  border-left: 2px solid rgb(var(--red-6));
}

.priority-medium {
  background-color: rgba(var(--orange-6), 0.1);
  color: rgb(var(--orange-6));
  border-left: 2px solid rgb(var(--orange-6));
}

.priority-low {
  background-color: rgba(var(--green-6), 0.1);
  color: rgb(var(--green-6));
  border-left: 2px solid rgb(var(--green-6));
}
</style>
