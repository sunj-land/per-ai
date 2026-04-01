<template>
  <div v-if="loading" class="global-loading-overlay">
    <div class="loading-content">
      <a-spin :size="48" :tip="tip || 'Loading...'" />
      <div v-if="cancellable" class="cancel-btn">
        <a-button type="text" size="small" @click="handleCancel">
          Cancel
        </a-button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed } from "vue";
import { useLoadingStore } from "@/store/loading";

const loadingStore = useLoadingStore();

const loading = computed(() => loadingStore.globalLoading);
const cancellable = computed(() => loadingStore.requestCount > 0);

const handleCancel = () => {
	loadingStore.cancelAll();
};

const tip = computed(() => {
	// Can be extended to show specific tips based on loading state
	return "Loading...";
});
</script>

<style scoped>
.global-loading-overlay {
  position: fixed;
  top: 0;
  left: 0;
  width: 100vw;
  height: 100vh;
  background-color: rgba(255, 255, 255, 0.8);
  z-index: 9999;
  display: flex;
  justify-content: center;
  align-items: center;
  backdrop-filter: blur(2px);
}

.loading-content {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 16px;
}

.cancel-btn {
  margin-top: 16px;
}

/* Dark mode support */
:deep(.arco-spin-tip) {
  color: var(--color-text-1);
}

@media (prefers-color-scheme: dark) {
  .global-loading-overlay {
    background-color: rgba(0, 0, 0, 0.7);
  }
}
</style>
