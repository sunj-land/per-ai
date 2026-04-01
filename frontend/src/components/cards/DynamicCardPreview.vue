<template>
  <div class="dynamic-card-preview">
    <component :is="dynamicComponent" v-if="dynamicComponent" v-bind="componentProps" />
    <div v-else-if="error" class="error">
      <p>Component Load Error:</p>
      <pre>{{ error }}</pre>
    </div>
    <div v-else class="loading">Loading Preview...</div>
  </div>
</template>

<script setup>
import * as ArcoVue from "@arco-design/web-vue";
import { debounce } from "lodash-es";
import * as Vue from "vue";
import { onUnmounted, ref, shallowRef, watch } from "vue";
import { loadModule } from "vue3-sfc-loader";

const props = defineProps({
	code: { type: String, required: true },
	componentProps: { type: Object, default: () => ({}) },
});

const dynamicComponent = shallowRef(null);
const error = ref(null);
const styleElements = ref([]);
let latestLoadId = 0;

const removeStyles = () => {
	styleElements.value.forEach((el) => {
		if (el.parentNode) el.parentNode.removeChild(el);
	});
	styleElements.value = [];
};

const load = async () => {
	if (!props.code) return;

	const myLoadId = ++latestLoadId;
	error.value = null;

	try {
		const currentLoadStyles = [];

		const options = {
			moduleCache: {
				vue: Vue,
				"@arco-design/web-vue": ArcoVue,
			},
			async getFile(url) {
				if (url.endsWith(".vue")) return props.code;
				return Promise.reject(new Error(`File not found: ${url}`));
			},
			addStyle(textContent) {
				const style = document.createElement("style");
				style.textContent = textContent;
				const ref = document.head.getElementsByTagName("style")[0] || null;
				document.head.insertBefore(style, ref);
				currentLoadStyles.push(style);
			},
		};

		// Use unique path to bypass cache and force reload
		const component = await loadModule(`/component-${myLoadId}.vue`, options);

		// If a newer load has started, discard this result and cleanup styles we just added
		if (myLoadId !== latestLoadId) {
			currentLoadStyles.forEach((el) => {
				if (el.parentNode) el.parentNode.removeChild(el);
			});
			return;
		}

		// Load successful: remove old styles and update to new component
		removeStyles();
		styleElements.value = currentLoadStyles;
		dynamicComponent.value = component;
	} catch (e) {
		if (myLoadId === latestLoadId) {
			console.error("Failed to load component:", e);
			error.value = e.message;
		}
	}
};

const debouncedLoad = debounce(load, 500);

watch(() => props.code, debouncedLoad, { immediate: true });

onUnmounted(() => {
	removeStyles();
});
</script>

<style scoped>
.dynamic-card-preview {
  min-height: 100px;
  border: 1px dashed #e5e6eb;
  padding: 16px;
  border-radius: 4px;
}
.error {
  color: #f53f3f;
  background: #fff0f0;
  padding: 10px;
  border-radius: 4px;
  font-size: 12px;
  white-space: pre-wrap;
}
.loading {
  color: #86909c;
  text-align: center;
  padding: 20px;
}
</style>
