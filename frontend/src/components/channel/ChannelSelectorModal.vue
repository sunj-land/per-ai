<!--
 * @Author: Channel Selector Modal
 * @Date: 2026-03-17
 * @Description: 发送消息到渠道的弹窗，支持多选
 -->
<template>
  <a-modal
    v-model:visible="visible"
    title="发送消息到渠道"
    @ok="handleSend"
    @cancel="handleCancel"
    :ok-loading="sending"
    width="500px"
  >
    <a-spin :loading="loading" class="w-full">
      <a-form layout="vertical">
        <a-form-item label="选择渠道" required>
          <a-select
            v-model="selectedChannels"
            :options="channelOptions"
            placeholder="请选择要发送的渠道"
            multiple
            allow-search
            allow-clear
          >
          </a-select>
        </a-form-item>

        <a-form-item label="消息标题 (可选)">
          <a-input v-model="messageTitle" placeholder="请输入消息标题" />
        </a-form-item>

        <a-form-item label="消息内容" required>
          <a-textarea
            v-model="messageContent"
            placeholder="请输入消息内容 (支持 Markdown)"
            :auto-size="{ minRows: 4, maxRows: 10 }"
          />
        </a-form-item>
      </a-form>
    </a-spin>
  </a-modal>
</template>

<script setup>
import { Message } from "@arco-design/web-vue";
import { computed, ref, watch } from "vue";
import { getChannels, sendMessage } from "@/api/channel";

const props = defineProps({
	modelValue: {
		type: Boolean,
		default: false,
	},
	initialTitle: {
		type: String,
		default: "",
	},
	initialContent: {
		type: String,
		default: "",
	},
});

const emit = defineEmits(["update:modelValue", "success"]);

const visible = computed({
	get: () => props.modelValue,
	set: (val) => emit("update:modelValue", val),
});

const loading = ref(false);
const sending = ref(false);
const channelOptions = ref([]);
const selectedChannels = ref([]);
const messageTitle = ref("");
const messageContent = ref("");

// ========== 步骤1：获取渠道列表数据 ==========
/**
 * 获取可用渠道列表
 */
const fetchChannels = async () => {
	loading.value = true;
	try {
		const res = await getChannels({ limit: 100 });
		const channels = res || [];

		// 过滤重复的 qqbot 和 dingtalk 渠道，每种仅保留一个
		const uniqueChannels = [];
		let hasQqbot = false;
		let hasDingtalk = false;
		for (const channel of channels) {
			if (channel.type === "qqbot") {
				if (!hasQqbot) {
					uniqueChannels.push(channel);
					hasQqbot = true;
				}
			} else if (channel.type === "dingtalk") {
				if (!hasDingtalk) {
					uniqueChannels.push(channel);
					hasDingtalk = true;
				}
			} else {
				uniqueChannels.push(channel);
			}
		}

		channelOptions.value = uniqueChannels.map((channel) => ({
			label: `${channel.name} (${channel.type})`,
			value: channel.id,
			type: channel.type,
		}));

		// 默认选中所有 qqbot 类型的渠道
		if (selectedChannels.value.length === 0) {
			selectedChannels.value = uniqueChannels
				.filter((c) => c.type === "qqbot")
				.map((c) => c.id);
		}
	} catch (error) {
		Message.error("获取渠道列表失败");
		console.error(error);
	} finally {
		loading.value = false;
	}
};

watch(
	() => props.modelValue,
	(val) => {
		if (val) {
			selectedChannels.value = [];
			messageTitle.value = props.initialTitle;
			messageContent.value = props.initialContent;
			if (channelOptions.value.length === 0) {
				fetchChannels();
			}
		}
	},
);

// ========== 步骤2：处理发送消息 ==========
/**
 * 处理消息发送
 */
const handleSend = async () => {
	if (selectedChannels.value.length === 0) {
		Message.warning("请至少选择一个渠道");
		return false;
	}

	if (!messageContent.value) {
		Message.warning("请输入消息内容");
		return false;
	}

	sending.value = true;
	let successCount = 0;
	let failCount = 0;

	try {
		// 遍历所有选中的渠道并发送消息
		const promises = selectedChannels.value.map(async (channelId) => {
			try {
				const res = await sendMessage(channelId, {
					title: messageTitle.value,
					content: messageContent.value,
				});
				if (res && res.status === "failed") {
					throw new Error(res.result || "发送到该渠道失败");
				}
				successCount++;
			} catch (error) {
				failCount++;
				console.error(`向渠道 ${channelId} 发送失败:`, error);
			}
		});

		await Promise.all(promises);

		if (failCount === 0) {
			Message.success(`成功推送到 ${successCount} 个渠道`);
			emit("success");
			visible.value = false;
			return true;
		} else if (successCount > 0) {
			Message.warning(
				`部分推送完成: 成功 ${successCount} 个, 失败 ${failCount} 个`,
			);
			emit("success");
			visible.value = false;
			return true;
		} else {
			Message.error("所有渠道推送均失败");
			return false;
		}
	} catch (error) {
		Message.error("发送过程中发生错误");
		console.error(error);
		return false;
	} finally {
		sending.value = false;
	}
};

const handleCancel = () => {
	visible.value = false;
};
</script>

<style scoped>
/* 组件样式 */
</style>
