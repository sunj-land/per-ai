<template>
  <div class="flex flex-col h-full bg-white dark:bg-gray-800 rounded-xl overflow-hidden border border-gray-100 dark:border-gray-700 shadow-sm transition-all duration-300">
    <div class="flex items-center justify-between px-4 py-2 bg-gray-50/50 dark:bg-gray-800/50 border-b border-gray-100 dark:border-gray-700 z-10">
      <div class="flex items-center gap-3">
        <!-- Save status -->
        <div class="text-xs flex items-center gap-1.5 transition-opacity duration-300" :class="saving ? 'text-blue-500 opacity-100' : 'text-gray-400 opacity-70'">
          <template v-if="saving">
            <icon-loading spin /> <span>保存中...</span>
          </template>
          <template v-else>
            <icon-check-circle-fill class="text-green-500" /> <span>已保存</span>
          </template>
        </div>
      </div>
    </div>

    <div class="flex-1 relative bg-white dark:bg-gray-800 h-full overflow-hidden">
      <!-- MdEditor-v3 Component -->
      <MdEditor
        v-model="content"
        @onChange="handleInput"
        @onSave="handleSave"
        :theme="isDarkMode ? 'dark' : 'light'"
        class="h-full w-full custom-md-editor"
        placeholder="记录你的思考、摘要或灵感..."
        preview-theme="github"
        :preview="false"
        :toolbars="[
          'bold',
          'underline',
          'italic',
          '-',
          'title',
          'strikeThrough',
          'sub',
          'sup',
          'quote',
          'unorderedList',
          'orderedList',
          'task',
          '-',
          'codeRow',
          'code',
          'link',
          'image',
          'table',
          '-',
          'revoke',
          'next',
          '=',
          'pageFullscreen',
          'fullscreen',
          'preview',
          'htmlPreview',
          'catalog'
        ]"
      />
    </div>
  </div>
</template>

<script setup>
import { useDebounceFn } from "@vueuse/core";
import { computed, ref, watch } from "vue";
import { MdEditor } from 'md-editor-v3';
import 'md-editor-v3/lib/style.css';

const props = defineProps({
	initialContent: String,
	saving: Boolean,
});

const emit = defineEmits(["update:content", "save"]);

const content = ref(props.initialContent || "");

// Check if system/user is in dark mode (basic detection)
const isDarkMode = computed(() => {
    return document.body.hasAttribute('arco-theme') && document.body.getAttribute('arco-theme') === 'dark';
});

watch(
	() => props.initialContent,
	(newVal) => {
		if (newVal !== content.value && !props.saving) {
			content.value = newVal || "";
		}
	},
);

const debouncedSave = useDebounceFn(() => {
	emit("save", content.value);
}, 1000);

const handleInput = (val) => {
	emit("update:content", val);
	debouncedSave();
};

const handleSave = (val) => {
    emit("save", val);
};
</script>

<style scoped>
/* Customize MdEditor styles to match the theme */
.custom-md-editor {
    border: none !important;
    height: 100% !important;
}

:deep(.md-editor-toolbar-wrapper) {
    padding: 4px 8px;
}

:deep(.md-editor-content) {
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, "Noto Sans", sans-serif;
}
</style>
