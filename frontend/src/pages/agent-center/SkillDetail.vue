<template>
  <div class="skill-detail h-full flex flex-col relative">
    <div v-if="loading" class="flex justify-center items-center h-full">
      <a-spin dot />
    </div>
    <div v-else-if="error" class="text-center text-red-500 py-10">
      {{ error }}
    </div>
    <div v-else class="flex flex-col h-full">
      <div class="flex justify-between items-center mb-4 px-4 pt-4">
        <h2 class="text-lg font-bold">Documentation</h2>
        <div class="space-x-2">
          <a-button v-if="!isEditing" type="primary" size="small" @click="startEditing">
            <template #icon><icon-edit /></template>
            Edit
          </a-button>
          <template v-else>
            <a-button size="small" @click="cancelEditing">Cancel</a-button>
            <a-button type="primary" size="small" :loading="saving" @click="saveMarkdown">
              <template #icon><icon-save /></template>
              Save
            </a-button>
          </template>
        </div>
      </div>

      <div class="flex-1 overflow-auto px-4 pb-4">
        <div v-if="isEditing" class="h-full">
          <a-textarea
            v-model="markdownContent"
            class="h-full font-mono text-sm"
            style="min-height: 400px; height: 100%;"
            placeholder="Enter markdown content..."
          />
        </div>
        <div v-else class="markdown-body" v-html="renderedMarkdown"></div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { Message } from "@arco-design/web-vue";
import MarkdownIt from "markdown-it";
import { computed, onMounted, ref, watch } from "vue";
import { getSkillMarkdown, updateSkillMarkdown } from "@/api/agent-center";

const props = defineProps({
	skillId: {
		type: String,
		required: true,
	},
});

const emit = defineEmits(["refresh"]);

const md = new MarkdownIt();
const markdownContent = ref("");
const originalContent = ref("");
const loading = ref(true);
const error = ref(null);
const isEditing = ref(false);
const saving = ref(false);

const _renderedMarkdown = computed(() => {
	return md.render(markdownContent.value || "No description available.");
});

const fetchMarkdown = async () => {
	loading.value = true;
	error.value = null;
	try {
		const res = await getSkillMarkdown(props.skillId);
		markdownContent.value = res.markdown || "";
		originalContent.value = res.markdown || "";
	} catch (e) {
		error.value = "Failed to load description.";
		console.error(e);
	} finally {
		loading.value = false;
	}
};

const _startEditing = () => {
	isEditing.value = true;
};

const _cancelEditing = () => {
	markdownContent.value = originalContent.value;
	isEditing.value = false;
};

const _saveMarkdown = async () => {
	saving.value = true;
	try {
		await updateSkillMarkdown(props.skillId, markdownContent.value);
		originalContent.value = markdownContent.value;
		isEditing.value = false;
		Message.success("Documentation updated successfully");
		emit("refresh"); // Notify parent list to refresh descriptions
	} catch (e) {
		Message.error("Failed to save documentation");
		console.error(e);
	} finally {
		saving.value = false;
	}
};

onMounted(() => {
	fetchMarkdown();
});

watch(
	() => props.skillId,
	() => {
		isEditing.value = false;
		fetchMarkdown();
	},
);
</script>

<style>
/* Simple Markdown Styles */
.markdown-body {
  font-family: -apple-system,BlinkMacSystemFont,Segoe UI,Helvetica,Arial,sans-serif,Apple Color Emoji,Segoe UI Emoji;
  font-size: 16px;
  line-height: 1.5;
  word-wrap: break-word;
}
.markdown-body h1, .markdown-body h2 {
  border-bottom: 1px solid #eaecef;
  padding-bottom: .3em;
}
.markdown-body pre {
  background-color: #f6f8fa;
  border-radius: 6px;
  padding: 16px;
  overflow: auto;
}
.markdown-body code {
  background-color: rgba(27,31,35,.05);
  border-radius: 3px;
  padding: .2em .4em;
}
</style>
