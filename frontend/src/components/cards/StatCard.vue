<template>
  <a-card class="stat-card">
    <div class="stat-header">
      <div class="title">{{ title }}</div>
      <a-tag :color="trendColor" size="small">{{ trend }}</a-tag>
    </div>
    <div class="stat-value">{{ value }}</div>
    <div class="stat-footer">
      <div class="footer-label">{{ footerLabel }}</div>
      <div class="footer-value">{{ footerValue }}</div>
    </div>
  </a-card>
</template>

<script setup>
import { computed } from "vue";

const props = defineProps({
	title: { type: String, default: "Total Sales" },
	value: { type: String, default: "$12,450" },
	trend: { type: String, default: "+15.2%" },
	trendType: { type: String, default: "up" }, // up, down, neutral
	footerLabel: { type: String, default: "Last Week" },
	footerValue: { type: String, default: "$10,800" },
});

const _trendColor = computed(() => {
	if (props.trendType === "up") return "green";
	if (props.trendType === "down") return "red";
	return "gray";
});
</script>

<style scoped>
.stat-card { width: 240px; border-radius: 8px; }
.stat-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px; }
.title { color: var(--color-text-3); font-size: 14px; }
.stat-value { font-size: 28px; font-weight: bold; margin-bottom: 16px; color: var(--color-text-1); }
.stat-footer { border-top: 1px solid var(--color-border-2); padding-top: 8px; display: flex; justify-content: space-between; font-size: 12px; color: var(--color-text-3); }
</style>
