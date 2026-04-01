<template>
  <div class="message-actions">
    <a-space size="medium">
      <a-tooltip content="复制">
        <a-button type="text" shape="circle" size="small" @click="handleCopy">
          <template #icon><icon-copy /></template>
        </a-button>
      </a-tooltip>
      <a-tooltip content="重新生成" v-if="isAssistant">
        <a-button type="text" shape="circle" size="small" @click="$emit('regenerate')">
          <template #icon><icon-refresh /></template>
        </a-button>
      </a-tooltip>
      <a-tooltip content="朗读" v-if="isAssistant">
        <a-button type="text" shape="circle" size="small" @click="handleTTS">
          <template #icon><icon-sound /></template>
        </a-button>
      </a-tooltip>
      <a-tooltip content="赞同" v-if="isAssistant">
        <a-button type="text" shape="circle" size="small" @click="handleFeedback('like')" :class="{ active: feedback === 'like' }">
          <template #icon><icon-thumb-up /></template>
        </a-button>
      </a-tooltip>
      <a-tooltip content="反对" v-if="isAssistant">
        <a-button type="text" shape="circle" size="small" @click="handleFeedback('dislike')" :class="{ active: feedback === 'dislike' }">
          <template #icon><icon-thumb-down /></template>
        </a-button>
      </a-tooltip>
      <a-tooltip content="分享" v-if="isAssistant">
        <a-button type="text" shape="circle" size="small" @click="handleShare">
          <template #icon><icon-share-alt /></template>
        </a-button>
      </a-tooltip>
      <a-dropdown trigger="click" v-if="isAssistant">
        <a-button type="text" shape="circle" size="small">
          <template #icon><icon-more /></template>
        </a-button>
        <template #content>
          <a-doption @click="handleFavorite">
            <template #icon><icon-star /></template>
            收藏
          </a-doption>
        </template>
      </a-dropdown>
    </a-space>
  </div>
</template>

<script setup>
import { Message } from "@arco-design/web-vue";
import { useClipboard } from "@vueuse/core";
import { ref } from "vue";

const props = defineProps({
	content: {
		type: String,
		required: true,
	},
	isAssistant: {
		type: Boolean,
		default: false,
	},
	messageId: {
		type: [String, Number],
		required: true,
	},
});

const emit = defineEmits(["regenerate", "feedback", "share", "favorite"]);

const { copy, isSupported } = useClipboard();
const feedback = ref(null); // 'like' | 'dislike' | null

const _handleCopy = async () => {
	if (!isSupported.value) {
		Message.error("您的浏览器不支持剪贴板API");
		return;
	}
	await copy(props.content);
	Message.success("已复制到剪贴板");
};

const _handleTTS = () => {
	Message.info("语音播报功能开发中");
};

const _handleFeedback = (type) => {
	if (feedback.value === type) {
		feedback.value = null; // 取消
	} else {
		feedback.value = type;
	}
	emit("feedback", { messageId: props.messageId, type: feedback.value });
	if (feedback.value) {
		Message.success(type === "like" ? "感谢您的反馈" : "已记录您的反馈");
	}
};

const _handleShare = () => {
	emit("share", props.messageId);
};

const _handleFavorite = () => {
	emit("favorite", props.messageId);
};
</script>

<style scoped>
.message-actions {
  margin-top: 8px;
  display: flex;
  align-items: center;
  color: var(--color-text-3);
  opacity: 0.8;
  transition: opacity 0.2s;
}

.message-wrapper:hover .message-actions {
  opacity: 1;
}

.message-actions :deep(.arco-btn-text) {
  color: var(--color-text-3);
}

.message-actions :deep(.arco-btn-text:hover) {
  background-color: var(--color-fill-2);
  color: var(--color-text-1);
}

.message-actions :deep(.arco-btn-text.active) {
  color: rgb(var(--primary-6));
}
</style>
