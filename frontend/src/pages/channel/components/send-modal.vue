<!--
 * @Author: Message Sender
 * @Date: 2026-03-16
 * @Description: 发送消息弹窗
 -->
<template>
  <a-modal
    v-model:visible="visible"
    title="发送消息"
    @ok="handleSend"
    @cancel="handleCancel"
    :ok-loading="loading"
  >
    <a-form :model="form" layout="vertical">
      <a-form-item field="title" label="标题 (可选)">
        <a-input v-model="form.title" placeholder="请输入消息标题" />
      </a-form-item>

      <a-form-item field="content" label="内容" required>
        <a-textarea
          v-model="form.content"
          placeholder="请输入消息内容 (支持 Markdown)"
          :auto-size="{ minRows: 4, maxRows: 10 }"
        />
      </a-form-item>
    </a-form>
  </a-modal>
</template>

<script setup>
import { Message } from "@arco-design/web-vue";
import { computed, reactive, watch } from "vue";
import { sendMessage } from "@/api/channel";
import { useLoadingStore } from "@/store/loading";

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

const emit = defineEmits(["update:modelValue", "success"]);
const loadingStore = useLoadingStore();

const visible = computed({
	get: () => props.modelValue,
	set: (val) => emit("update:modelValue", val),
});

const _loading = computed(() => loadingStore.isLoading("channel-send"));
const form = reactive({
	title: "",
	content: "",
});

// Reset form when modal opens
watch(
	() => props.modelValue,
	(val) => {
		if (val) {
			form.title = "";
			form.content = "";
		}
	},
);

const _handleSend = async () => {
	if (!form.content) {
		Message.warning("请输入消息内容");
		return;
	}

	try {
		await sendMessage(props.channelId, {
			title: form.title,
			content: form.content,
		}); // Loading handled by 'channel-send'
		Message.success("发送成功");
		emit("success");
		visible.value = false;
	} catch (error) {
		console.error(error);
	}
};

const _handleCancel = () => {
	visible.value = false;
};
</script>
