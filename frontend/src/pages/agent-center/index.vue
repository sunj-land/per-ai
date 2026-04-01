<template>
  <div class="agent-center-container p-6">
    <div class="mb-6">
      <h1 class="text-2xl font-bold text-gray-800 dark:text-gray-100">Agent & Skill Center</h1>
      <p class="text-gray-500 mt-2">Manage and explore available AI agents and skills.</p>
    </div>
    
    <a-tabs default-active-key="agents" type="rounded">
      <a-tab-pane key="agents" title="Agents">
        <AgentList />
      </a-tab-pane>
      <a-tab-pane key="skills" title="Skills">
        <SkillList />
      </a-tab-pane>
      <a-tab-pane key="rss-quality" title="RSS质量评分">
        <RssQualityPanel />
      </a-tab-pane>
    </a-tabs>
  </div>
</template>

<script setup>
import AgentList from "./AgentList.vue";
import RssQualityPanel from "./RssQualityPanel.vue";
import SkillList from "./SkillList.vue";
</script>

<style scoped>
.agent-center-container {
  min-height: 100vh;
  background-color: var(--color-bg-1);
}
</style>
