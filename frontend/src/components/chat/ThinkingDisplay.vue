<template>
  <div class="thinking-display">
    <div class="thinking-header" @click="toggleExpand">
      <span class="icon">
        <icon-mind-mapping />
      </span>
      <span class="title">思维过程</span>
      <span class="status" :class="{ completed: completed }">
        {{ completed ? "已完成" : "推理中" }}
      </span>
      <span class="toggle-icon">
        <icon-down v-if="isExpanded" />
        <icon-right v-else />
      </span>
    </div>
    <div v-show="isExpanded" class="thinking-content">
      <div class="markdown-body" v-html="renderedContent"></div>
    </div>
  </div>
</template>

<script setup>
import MarkdownIt from "markdown-it";
import { computed, ref, watch } from "vue";

const props = defineProps({
	content: {
		type: String,
		required: true,
	},
	autoCollapse: {
		type: Boolean,
		default: false,
	},
	completed: {
		type: Boolean,
		default: false,
	},
});

const isExpanded = ref(true);
const md = new MarkdownIt({
	html: true,
	linkify: true,
	breaks: true,
});

const toggleExpand = () => {
	isExpanded.value = !isExpanded.value;
};

watch(
	() => props.autoCollapse,
	(newVal) => {
		if (newVal) {
			isExpanded.value = false;
		}
	},
	{ immediate: true },
);

const renderedContent = computed(() => {
	return md.render(props.content || "");
});
</script>

<style scoped>
.thinking-display {
  border: 1px solid var(--color-border-2);
  border-radius: 8px;
  margin-bottom: 12px;
  background-color: var(--color-fill-1);
  overflow: hidden;
}

.thinking-header {
  display: flex;
  align-items: center;
  padding: 8px 12px;
  cursor: pointer;
  background-color: var(--color-fill-2);
  user-select: none;
  transition: background-color 0.2s;
}

.thinking-header:hover {
  background-color: var(--color-fill-3);
}

.icon {
  display: flex;
  align-items: center;
  margin-right: 8px;
  color: rgb(var(--primary-6));
}

.title {
  font-size: 13px;
  font-weight: 500;
  color: var(--color-text-2);
  flex: 1;
}

.toggle-icon {
  display: flex;
  align-items: center;
  color: var(--color-text-3);
}

.status {
  margin-right: 8px;
  padding: 2px 8px;
  border-radius: 999px;
  font-size: 12px;
  line-height: 18px;
  color: rgb(var(--arcoblue-6));
  background-color: rgb(var(--arcoblue-1));
}

.status.completed {
  color: rgb(var(--green-6));
  background-color: rgb(var(--green-1));
}

.thinking-content {
  padding: 12px;
  font-size: 13px;
  color: var(--color-text-3);
  background-color: var(--color-bg-2);
  border-top: 1px solid var(--color-border-2);
}

.markdown-body {
  /* Basic markdown styling for thinking block */
  line-height: 1.6;
}
.markdown-body :deep(p) {
  margin-bottom: 0.8em;
}
.markdown-body :deep(pre) {
  background-color: var(--color-fill-3);
  padding: 8px;
  border-radius: 4px;
  overflow-x: auto;
  font-family: monospace;
}
.markdown-body :deep(code) {
  font-family: monospace;
  background-color: var(--color-fill-3);
  padding: 2px 4px;
  border-radius: 3px;
}
</style>
