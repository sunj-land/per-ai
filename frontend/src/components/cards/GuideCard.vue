<template>
  <a-card class="guide-card" title="Step Guide">
    <a-steps direction="vertical" :current="currentStep">
      <a-step v-for="(step, index) in steps" :key="index" :title="step.title" :description="step.description" />
    </a-steps>
    <div class="actions">
      <a-button @click="prev" :disabled="currentStep <= 0">Previous</a-button>
      <a-button type="primary" @click="next" :disabled="currentStep >= steps.length - 1">Next</a-button>
    </div>
  </a-card>
</template>

<script setup>
import { ref } from "vue";

const props = defineProps({
	steps: {
		type: Array,
		default: () => [
			{ title: "Step 1", description: "Download the installer." },
			{ title: "Step 2", description: "Run the setup wizard." },
			{ title: "Step 3", description: "Launch the application." },
		],
	},
});

const currentStep = ref(0);

const _next = () => {
	if (currentStep.value < props.steps.length - 1) {
		currentStep.value++;
	}
};

const _prev = () => {
	if (currentStep.value > 0) {
		currentStep.value--;
	}
};
</script>

<style scoped>
.guide-card { width: 100%; max-width: 400px; border-radius: 8px; }
.actions { margin-top: 24px; display: flex; justify-content: flex-end; gap: 12px; }
</style>
