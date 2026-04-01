<template>
  <div class="chart-card">
    <div ref="chartRef" style="width: 100%; height: 300px;"></div>
  </div>
</template>

<script setup>
import * as echarts from "echarts";
import { nextTick, onMounted, ref, watch } from "vue";

const props = defineProps({
	payload: {
		type: Object,
		required: true,
	},
});

const chartRef = ref(null);
let chartInstance = null;

const initChart = () => {
	if (chartRef.value) {
		chartInstance = echarts.init(chartRef.value);
		chartInstance.setOption(props.payload);
	}
};

onMounted(() => {
	nextTick(() => {
		initChart();
	});
});

watch(
	() => props.payload,
	(newVal) => {
		if (chartInstance) {
			chartInstance.setOption(newVal);
		}
	},
	{ deep: true },
);

// Handle resize if needed
// useResizeObserver(chartRef, () => chartInstance?.resize());
</script>

<style scoped>
.chart-card {
  margin: 12px 0;
  padding: 16px;
  border: 1px solid var(--color-border-2);
  border-radius: 8px;
  background: var(--color-bg-2);
}
</style>
