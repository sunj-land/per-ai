<template>
  <div class="app-layout">
    <GlobalLoading />
    <Sidebar v-if="!isLoginPage" />
    <div class="main-content">
      <router-view />
    </div>
  </div>
</template>

<script setup>
import { computed } from "vue";
import { useRoute } from "vue-router";
import GlobalLoading from "./components/loading/GlobalLoading.vue";
import Sidebar from "./components/layout/Sidebar.vue";

const route = useRoute();
const isLoginPage = computed(() => {
	return ["/login", "/auth/forgot-password", "/auth/reset-password"].includes(
		route.path,
	);
});
</script>

<style scoped>
.app-layout {
  display: flex;
  height: 100vh;
  width: 100vw;
  overflow: hidden;
  background-color: var(--color-bg-1);
}

.main-content {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  position: relative;
}
</style>
