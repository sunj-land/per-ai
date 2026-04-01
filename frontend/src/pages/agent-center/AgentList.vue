<template>
  <div class="agent-list-container h-full flex flex-col">
    <div class="flex justify-between items-center mb-4">
      <a-input-search
        v-model="searchQuery"
        placeholder="Search agents..."
        class="w-64"
        allow-clear
      />
      <div class="flex gap-2">
        <a-button @click="handleSync" :loading="syncing">
          <template #icon><icon-sync /></template>
          Sync Local
        </a-button>
        <a-button @click="fetchAgents" :loading="loading">
          <template #icon><icon-refresh /></template>
          Refresh
        </a-button>
      </div>
    </div>

    <SkeletonLoading :loading="loading" :rows="8" class="flex-1 overflow-hidden">
      <div v-if="filteredAgents.length === 0" class="text-center py-10 text-gray-500 flex-1 h-full flex items-center justify-center">
         No agents found.
      </div>

      <div v-else class="flex-1 overflow-y-auto pr-2 h-full">
        <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6 p-1">
          <a-card
            v-for="agent in paginatedAgents"
            :key="agent.id"
            class="cursor-pointer hover:shadow-lg transition-shadow duration-300 transform hover:-translate-y-1"
            @click="openDetail(agent)"
          >
            <template #title>
              <div class="flex items-center justify-between">
                <span class="font-bold text-lg truncate pr-2" :title="agent.name">{{ agent.name }}</span>
                <a-tag :color="agent.status === 'active' ? 'green' : 'gray'" size="small">
                  {{ agent.status }}
                </a-tag>
              </div>
            </template>
            <div class="text-gray-600 dark:text-gray-400 mb-4 h-12 line-clamp-2 text-sm">
              {{ agent.description || 'No description provided.' }}
            </div>
            <div class="flex justify-between items-center mt-2">
              <a-tag size="small" color="blue">{{ agent.type }}</a-tag>
              <span class="text-xs text-gray-400">ID: {{ agent.id }}</span>
            </div>
          </a-card>
        </div>
      </div>
    </SkeletonLoading>

    <div class="mt-4 flex justify-end" v-if="filteredAgents.length > 0 && !loading">
       <a-pagination
         v-model:current="currentPage"
         v-model:page-size="pageSize"
         :total="filteredAgents.length"
         show-total
         show-jumper
         show-page-size
         :page-size-options="[8, 12, 24, 48]"
       />
    </div>

    <a-drawer
      v-model:visible="drawerVisible"
      width="80%"
      :title="currentAgent ? `${currentAgent.name} Workflow` : 'Agent Detail'"
      :footer="false"
      unmount-on-close
    >
      <AgentDetail v-if="currentAgent" :agent-id="currentAgent.id" />
    </a-drawer>
  </div>
</template>

<script setup>
import { Message } from "@arco-design/web-vue";
import { computed, onMounted, ref } from "vue";
import { getAgentList, syncAgents } from "@/api/agent-center";
import { useLoadingStore } from "@/store/loading";
import SkeletonLoading from "@/components/loading/SkeletonLoading.vue";
import AgentDetail from "./AgentDetail.vue";

const loadingStore = useLoadingStore();
const agents = ref([]);
const loading = computed(() => loadingStore.isLoading("agent-list"));
const syncing = computed(() => loadingStore.isLoading("agent-sync"));
const drawerVisible = ref(false);
const currentAgent = ref(null);
const searchQuery = ref("");

// Pagination
const currentPage = ref(1);
const pageSize = ref(12);

const filteredAgents = computed(() => {
	if (!searchQuery.value) return agents.value;
	const query = searchQuery.value.toLowerCase();
	return agents.value.filter(
		(agent) =>
			agent.name.toLowerCase().includes(query) ||
			agent.description?.toLowerCase().includes(query) ||
			agent.type?.toLowerCase().includes(query),
	);
});

const paginatedAgents = computed(() => {
	const start = (currentPage.value - 1) * pageSize.value;
	const end = start + pageSize.value;
	return filteredAgents.value.slice(start, end);
});

const fetchAgents = async () => {
	// loading handled by store via 'agent-list'
	try {
		const res = await getAgentList();
		agents.value = res || [];
	} catch (error) {
		console.error(error);
	} finally {
		// loading handled by store
	}
};

const handleSync = async () => {
	// loading handled by store via 'agent-sync'
	try {
		await syncAgents({ loading: "agent-sync" });
		Message.success("Sync successful");
		fetchAgents();
	} catch (error) {
		console.error(error);
	} finally {
		// loading handled by store
	}
};

const openDetail = (agent) => {
	currentAgent.value = agent;
	drawerVisible.value = true;
};

onMounted(() => {
	fetchAgents();
});
</script>
