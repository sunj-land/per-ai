<template>
  <a-form :model="form" ref="formRef" @submit="handleSubmit">
    <a-form-item field="title" label="标题" :rules="[{ required: true, message: '请输入日程标题' }]">
      <a-input v-model="form.title" placeholder="请输入日程标题" />
    </a-form-item>

    <a-form-item field="description" label="描述">
      <a-textarea v-model="form.description" placeholder="请输入日程描述" />
    </a-form-item>

    <a-form-item field="start_time" label="开始时间" :rules="[{ required: true, message: '请选择开始时间' }]">
      <a-date-picker show-time v-model="form.start_time" style="width: 100%" />
    </a-form-item>

    <a-form-item field="end_time" label="结束时间">
      <a-date-picker show-time v-model="form.end_time" style="width: 100%" />
    </a-form-item>

    <a-form-item field="due_time" label="到期时间">
      <a-date-picker show-time v-model="form.due_time" style="width: 100%" />
    </a-form-item>

    <a-form-item field="priority" label="优先级">
      <a-select v-model="form.priority" placeholder="请选择优先级">
        <a-option value="high">高</a-option>
        <a-option value="medium">中</a-option>
        <a-option value="low">低</a-option>
      </a-select>
    </a-form-item>

    <a-form-item field="location" label="地点">
      <a-input v-model="form.location" placeholder="请输入地点" />
    </a-form-item>

    <a-form-item field="is_all_day" label="全天">
      <a-switch v-model="form.is_all_day" />
    </a-form-item>

    <a-form-item label="提醒">
      <div class="space-y-2 w-full">
        <div v-for="(reminder, index) in form.reminders" :key="index" class="flex gap-2 items-center">
          <a-date-picker show-time v-model="reminder.remind_at" placeholder="提醒时间" style="flex: 1" />
          <a-select v-model="reminder.type" placeholder="方式" style="width: 120px">
            <a-option value="notification">应用通知</a-option>
            <a-option value="email">邮件</a-option>
            <a-option value="sms">短信</a-option>
          </a-select>
          <a-tag v-if="reminder.status" :color="reminder.status === 'sent' ? 'green' : (reminder.status === 'failed' ? 'red' : 'gray')">
            {{ reminder.status === 'sent' ? '已发送' : (reminder.status === 'failed' ? '失败' : '待发送') }}
          </a-tag>
          <a-button type="text" status="danger" @click="removeReminder(index)">
            <icon-delete />
          </a-button>
        </div>
        <a-button type="dashed" long @click="addReminder">
          <template #icon><icon-plus /></template>
          添加提醒
        </a-button>
      </div>
    </a-form-item>

    <a-form-item>
      <a-space>
        <a-button html-type="submit" type="primary">保存</a-button>
        <a-button @click="$emit('cancel')">取消</a-button>
      </a-space>
    </a-form-item>
  </a-form>
</template>

<script setup>
import dayjs from "dayjs";
import { reactive, watch } from "vue";

const props = defineProps({
	initialData: {
		type: Object,
		default: () => ({
			title: "",
			description: "",
			start_time: "",
			end_time: "",
			due_time: "",
			priority: "medium",
			location: "",
			is_all_day: false,
			reminders: [],
		}),
	},
});

const emit = defineEmits(["submit", "cancel"]);

const form = reactive({
	title: "",
	description: "",
	start_time: "",
	end_time: "",
	due_time: "",
	priority: "medium",
	location: "",
	is_all_day: false,
	reminders: [],
});

watch(
	() => props.initialData,
	(newVal) => {
		if (newVal) {
			Object.assign(form, {
				...newVal,
				start_time: newVal.start_time
					? dayjs(newVal.start_time).format("YYYY-MM-DD HH:mm:ss")
					: "",
				end_time: newVal.end_time
					? dayjs(newVal.end_time).format("YYYY-MM-DD HH:mm:ss")
					: "",
				due_time: newVal.due_time
					? dayjs(newVal.due_time).format("YYYY-MM-DD HH:mm:ss")
					: "",
				reminders: newVal.reminders
					? newVal.reminders.map((r) => ({
							...r,
							remind_at: dayjs(r.remind_at).format("YYYY-MM-DD HH:mm:ss"),
						}))
					: [],
			});
		}
	},
	{ immediate: true },
);

const addReminder = () => {
	form.reminders.push({
		remind_at: "",
		type: "notification",
		message_template: "",
	});
};

const removeReminder = (index) => {
	form.reminders.splice(index, 1);
};

const handleSubmit = async ({ errors, values }) => {
	if (!errors) {
		const submitData = { ...form };
		// 后端需要 ISO 格式的 datetime 字符串，否则如果为空字符串会导致 422 校验失败
		submitData.start_time = submitData.start_time ? dayjs(submitData.start_time).toISOString() : null;
		submitData.end_time = submitData.end_time ? dayjs(submitData.end_time).toISOString() : null;
		submitData.due_time = submitData.due_time ? dayjs(submitData.due_time).toISOString() : null;
		
		if (submitData.reminders && submitData.reminders.length > 0) {
			submitData.reminders = submitData.reminders.map(r => ({
				...r,
				remind_at: r.remind_at ? dayjs(r.remind_at).toISOString() : null
			}));
		}

		emit("submit", submitData);
	}
};
</script>
