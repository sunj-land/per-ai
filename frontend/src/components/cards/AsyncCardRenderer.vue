<template>
  <div class="async-card-renderer">
    <component :is="localComponent" v-if="localComponent" v-bind="params" />
    <DynamicCardPreview v-else-if="dynamicCode" :code="dynamicCode" :component-props="params" />
    <div v-else-if="error" class="error">
      <a-empty :description="error" />
    </div>
    <div v-else class="loading">
      <a-skeleton animation>
        <a-skeleton-line :rows="3" />
      </a-skeleton>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, ref, watch } from "vue";
import { getCard, getVersions } from "@/api/card-center";
import cards from "./registry";

const props = defineProps({
	id: { type: [Number, String], required: true },
	params: { type: Object, default: () => ({}) },
});

const localComponent = computed(() => {
	if (typeof props.id === "string" && cards[props.id]) {
		return cards[props.id];
	}
	// Also try PascalCase if kebab-case provided
	if (typeof props.id === "string") {
		const pascal = props.id
			.replace(/(-\w)/g, (m) => m[1].toUpperCase())
			.replace(/^\w/, (c) => c.toUpperCase());
		if (cards[pascal]) return cards[pascal];
	}
	return null;
});

const dynamicCode = ref(null);
const error = ref(null);

const loadDynamicCard = async () => {
	if (localComponent.value) return;

	error.value = null;
	dynamicCode.value = null;

	try {
		// If ID is numeric, fetch from API
		if (/^\d+$/.test(String(props.id))) {
			const card = await getCard(props.id);
			if (!card) throw new Error("Card not found");

			const versions = await getVersions(props.id);
			// Get the version matching card.version
			const version = versions.find((v) => v.version === card.version);

			if (version?.code) {
				dynamicCode.value = version.code;
			} else {
				throw new Error("No code found for this card version");
			}
		} else {
			// If string and not local, it's an error (unless we support name lookup API later)
			throw new Error(`Component '${props.id}' not found locally or remotely.`);
		}
	} catch (e) {
		console.error("Failed to load card:", e);
		error.value = e.message || "Failed to load card";
	}
};

onMounted(loadDynamicCard);
watch(() => props.id, loadDynamicCard);
</script>

<style scoped>
.async-card-renderer {
  margin: 8px 0;
}
</style>
