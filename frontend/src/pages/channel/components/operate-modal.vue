<!--
 * @Author: Channel Operator
 * @Date: 2026-03-16
 * @Description: Channel 创建/编辑弹窗
 -->
<template>
  <a-modal
    v-model:visible="visible"
    :title="isEdit ? '编辑 Channel' : '创建 Channel'"
    @ok="handleOk"
    @cancel="handleCancel"
    :ok-loading="loading"
  >
    <a-form ref="formRef" :model="form" :rules="rules" layout="vertical">
      <a-form-item field="name" label="名称">
        <a-input v-model="form.name" placeholder="请输入 Channel 名称" />
      </a-form-item>

      <a-form-item field="type" label="类型">
        <a-select v-model="form.type" placeholder="请选择类型" :disabled="isEdit">
          <a-option value="dingtalk">钉钉 (DingTalk)</a-option>
          <a-option value="qqbot">QQ 机器人 (QQBot)</a-option>
          <a-option value="feishu">飞书 (Feishu)</a-option>
          <a-option value="wechat_work">企业微信 (WeCom)</a-option>
          <a-option value="slack">Slack</a-option>
          <a-option value="email">邮件 (Email)</a-option>
          <a-option value="webhook">Webhook</a-option>
        </a-select>
      </a-form-item>

      <a-form-item field="description" label="描述">
        <a-textarea v-model="form.description" placeholder="请输入描述" />
      </a-form-item>

      <a-form-item field="is_active" label="状态">
        <a-switch v-model="form.is_active" checked-text="启用" unchecked-text="禁用" />
      </a-form-item>

      <a-divider orientation="left">配置信息</a-divider>

      <!-- DingTalk Config -->
      <template v-if="form.type === 'dingtalk'">
        <a-form-item field="config.webhook_url" label="Webhook URL" :rules="[{ required: true, message: 'Webhook URL 必填' }]">
          <a-input v-model="form.config.webhook_url" placeholder="https://oapi.dingtalk.com/robot/send?access_token=..." />
        </a-form-item>
        <a-form-item field="config.secret" label="Secret (加签密钥)">
          <a-input v-model="form.config.secret" placeholder="SEC..." />
        </a-form-item>
      </template>

      <!-- WeCom Config -->
      <template v-else-if="form.type === 'wechat_work'">
        <a-form-item field="config.webhook_url" label="Webhook URL" :rules="[{ required: true, message: 'Webhook URL 必填' }]">
          <a-input v-model="form.config.webhook_url" placeholder="https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=..." />
        </a-form-item>
      </template>

      <!-- Feishu Config -->
      <template v-else-if="form.type === 'feishu'">
        <a-form-item field="config.webhook_url" label="Webhook URL" :rules="[{ required: true, message: 'Webhook URL 必填' }]">
          <a-input v-model="form.config.webhook_url" placeholder="https://open.feishu.cn/open-apis/bot/v2/hook/..." />
        </a-form-item>
        <a-form-item field="config.secret" label="Secret (加签密钥)">
          <a-input v-model="form.config.secret" placeholder="Optional" />
        </a-form-item>
      </template>

      <!-- QQBot Config -->
      <template v-else-if="form.type === 'qqbot'">
        <a-form-item field="config.appId" label="App ID" :rules="[{ required: true, message: 'App ID 必填' }]">
          <a-input v-model="form.config.appId" placeholder="QQ Bot App ID" />
        </a-form-item>
        <a-form-item field="config.secret" label="App Secret" :rules="[{ required: true, message: 'App Secret 必填' }]">
          <a-input-password v-model="form.config.secret" placeholder="QQ Bot App Secret" />
        </a-form-item>
        <a-form-item field="config.allowFrom" label="允许发送的 OpenID (逗号分隔)">
          <a-input v-model="form.config.allowFrom" placeholder="OpenID1,OpenID2" />
        </a-form-item>
         <a-form-item field="config.sandbox" label="沙箱模式">
          <a-switch v-model="form.config.sandbox" />
        </a-form-item>
      </template>

      <!-- Generic Config (JSON) -->
      <template v-else>
        <a-form-item field="configJson" label="配置 (JSON)" :rules="[{ validator: validateJson, required: true }]">
          <a-textarea v-model="form.configJson" :auto-size="{ minRows: 4, maxRows: 8 }" placeholder='{"key": "value"}' />
        </a-form-item>
      </template>

    </a-form>
  </a-modal>
</template>

<script setup>
import { Message } from "@arco-design/web-vue";
import { computed, reactive, ref, watch } from "vue";
import { createChannel, updateChannel } from "@/api/channel";
import { useLoadingStore } from "@/store/loading";

const props = defineProps({
	modelValue: {
		type: Boolean,
		default: false,
	},
	channelId: {
		type: String,
		default: "",
	},
	initialData: {
		type: Object,
		default: () => ({}),
	},
});

const emit = defineEmits(["update:modelValue", "success"]);
const loadingStore = useLoadingStore();

const visible = computed({
	get: () => props.modelValue,
	set: (val) => emit("update:modelValue", val),
});

const isEdit = computed(() => !!props.channelId);
const _loading = computed(
	() =>
		loadingStore.isLoading("channel-create") ||
		loadingStore.isLoading("channel-update"),
);
const formRef = ref(null);

const form = reactive({
	name: "",
	type: "dingtalk",
	description: "",
	is_active: true,
	config: {},
	configJson: "{}",
});

const _rules = {
	name: [{ required: true, message: "名称必填" }],
	type: [{ required: true, message: "类型必填" }],
};

// 监听弹窗显示状态，回填或重置表单
watch(
	() => props.modelValue,
	(val) => {
		if (val) {
			if (props.channelId && props.initialData) {
				form.name = props.initialData.name;
				form.type = props.initialData.type;
				form.description = props.initialData.description;
				form.is_active = props.initialData.is_active;

				// Deep copy config
				const config = JSON.parse(
					JSON.stringify(props.initialData.config || {}),
				);

				// Special handling for QQBot allowFrom array -> string
				if (form.type === "qqbot" && Array.isArray(config.allowFrom)) {
					config.allowFrom = config.allowFrom.join(",");
				}

				form.config = config;
				form.configJson = JSON.stringify(config, null, 2);
			} else {
				// Reset form
				form.name = "";
				form.type = "dingtalk";
				form.description = "";
				form.is_active = true;
				form.config = {};
				form.configJson = "{}";
			}
		}
	},
);

// JSON 校验
const _validateJson = (value, callback) => {
	try {
		JSON.parse(value);
		callback();
	} catch (_e) {
		callback("请输入有效的 JSON 格式");
	}
};

const _handleOk = async () => {
	const res = await formRef.value?.validate();
	if (res) return;

	try {
		// Prepare data
		const data = {
			name: form.name,
			type: form.type,
			description: form.description,
			is_active: form.is_active,
			config: {},
		};

		if (["dingtalk", "wechat_work", "feishu"].includes(form.type)) {
			data.config = { ...form.config };
		} else if (form.type === "qqbot") {
			data.config = { ...form.config };
			if (typeof data.config.allowFrom === "string") {
				data.config.allowFrom = data.config.allowFrom
					.split(",")
					.map((s) => s.trim())
					.filter(Boolean);
			}
		} else {
			data.config = JSON.parse(form.configJson);
		}

		if (isEdit.value) {
			await updateChannel(props.channelId, data); // Loading handled by 'channel-update'
			Message.success("更新成功");
		} else {
			await createChannel(data); // Loading handled by 'channel-create'
			Message.success("创建成功");
		}
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
