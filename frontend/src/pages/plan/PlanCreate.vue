<script setup>
import { Message } from "@arco-design/web-vue";
import { ref } from "vue";
import { useRouter } from "vue-router";
import { useLoadingStore } from "@/store/loading";
import { createPlan, generatePlan } from "../../api/plan";

const router = useRouter();
const loadingStore = useLoadingStore();
const goalText = ref("");
const previewData = ref(null);

const handleGenerate = async () => {
	if (!goalText.value) {
		Message.warning("Please enter a learning goal");
		return;
	}

	try {
		const data = await generatePlan(goalText.value);
		previewData.value = data;
		Message.success("Plan generated successfully");
	} catch (error) {
		Message.error(
			`Generation failed: ${error.response?.data?.detail || error.message}`,
		);
	}
};

const handleConfirm = async () => {
	if (!previewData.value) return;

	try {
		const result = await createPlan(previewData.value);
		Message.success("Plan created successfully");
		router.push(`/plans/${result.plan_id}`);
	} catch (error) {
		Message.error(
			`Creation failed: ${error.response?.data?.detail || error.message}`,
		);
	}
};
</script>

<template>
  <div class="plan-create-container">
    <a-page-header title="Create Learning Plan" subtitle="AI-powered planning" @back="router.back()" />

    <a-card class="input-card">
      <a-textarea v-model="goalText" placeholder="Enter your learning goal (e.g., 'Learn Python in 3 months')" :rows="4" />
      <div style="margin-top: 16px; text-align: right;">
        <a-button type="primary" :loading="loadingStore.isLoading('plan-generate')" @click="handleGenerate">Generate Plan</a-button>
      </div>
    </a-card>

    <div v-if="previewData" class="preview-section">
      <a-divider orientation="left">Plan Preview</a-divider>
      <a-descriptions title="Overview" :column="2" bordered>
        <a-descriptions-item label="Goal">{{ previewData.goal }}</a-descriptions-item>
        <a-descriptions-item label="Deadline">{{ previewData.deadline }}</a-descriptions-item>
        <a-descriptions-item label="Est. Hours">{{ previewData.estimated_hours }}</a-descriptions-item>
        <a-descriptions-item label="Difficulty">{{ previewData.difficulty_coef }}</a-descriptions-item>
      </a-descriptions>

      <div class="milestones-preview">
        <h3>Milestones</h3>
        <a-timeline>
          <a-timeline-item v-for="(ms, index) in previewData.milestones" :key="index" :label="ms.deadline">
            <strong>{{ ms.title }}</strong>
            <ul v-if="ms.tasks && ms.tasks.length">
              <li v-for="(task, tIndex) in ms.tasks" :key="tIndex">
                <a-tag color="blue">{{ task.type }}</a-tag> {{ task.title }} ({{ task.estimated_min }} min)
              </li>
            </ul>
          </a-timeline-item>
        </a-timeline>
      </div>

      <div style="margin-top: 24px; text-align: center;">
        <a-button type="primary" size="large" :loading="loadingStore.isLoading('plan-create')" @click="handleConfirm">Confirm & Create Plan</a-button>
      </div>
    </div>
  </div>
</template>

<style scoped>
.plan-create-container {
  padding: 24px;
  max-width: 1000px;
  margin: 0 auto;
}
.input-card {
  margin-bottom: 24px;
}
.preview-section {
  background: #fff;
  padding: 24px;
  border-radius: 4px;
}
.milestones-preview {
  margin-top: 24px;
}
</style>
