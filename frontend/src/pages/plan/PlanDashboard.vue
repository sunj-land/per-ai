<script setup>
import { Message } from "@arco-design/web-vue";
import { onMounted, ref } from "vue";
import { useRouter } from "vue-router";
import { useLoadingStore } from "@/store/loading";
import { listPlans } from "../../api/plan";

const router = useRouter();
const loadingStore = useLoadingStore();
const plans = ref([]);

const loadPlans = async () => {
	try {
		const data = await listPlans({ loading: "plan-list" });
		plans.value = data;
	} catch (error) {
		Message.error(
			"Failed to load plans: " +
				(error.response?.data?.detail || error.message),
		);
	} finally {
		loadingStore.stopLoading("plan-list");
	}
};

onMounted(() => {
	loadPlans();
});
</script>

<template>
  <div class="plan-dashboard-container">
    <a-page-header title="My Learning Plans" subtitle="Dashboard" />

    <div style="margin-bottom: 24px;">
      <a-button type="primary" @click="router.push('/plan/create')">Create New Plan</a-button>
    </div>

    <a-list :grid="{ gutter: 16, column: 3 }" :data-source="plans" :loading="loadingStore.isLoading('plan-list')">
      <template #renderItem="{ item }">
        <a-list-item>
          <a-card :title="item.goal" hoverable>
            <template #extra>
              <a-tag color="blue">{{ item.status }}</a-tag>
            </template>
            <p>Deadline: {{ item.deadline }}</p>
            <p>Created: {{ item.created_at }}</p>
            <a-progress :percent="item.progress || 0" />
            <a-button type="link" @click="router.push(`/plans/${item.plan_id}`)">View Details</a-button>
          </a-card>
        </a-list-item>
      </template>
    </a-list>
  </div>
</template>

<style scoped>
.plan-dashboard-container {
  padding: 24px;
  max-width: 1200px;
  margin: 0 auto;
}
</style>
