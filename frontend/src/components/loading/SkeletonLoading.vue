<template>
  <div class="skeleton-loading-container">
    <div v-if="loading" class="skeleton-wrapper">
      <a-skeleton :animation="animated" :loading="loading">
        <a-space direction="vertical" :style="{width: '100%'}" size="large">
          <a-skeleton-line :rows="rows" :widths="widths" />
        </a-space>
      </a-skeleton>
    </div>
    <div v-else class="content-wrapper">
      <slot></slot>
    </div>
  </div>
</template>

<script setup>
import { computed } from "vue";

const props = defineProps({
	loading: {
		type: Boolean,
		default: false,
	},
	rows: {
		type: Number,
		default: 3,
	},
	animated: {
		type: Boolean,
		default: true,
	},
	fullWidth: {
		type: Boolean,
		default: true,
	},
});

const widths = computed(() => {
	if (props.fullWidth) {
		return Array(props.rows).fill("100%");
	}
	// Generate random widths for more natural look if not full width
	return Array(props.rows)
		.fill(0)
		.map((_, i) => {
			if (i === props.rows - 1) return "60%";
			return `${85 + Math.random() * 15}%`;
		});
});
</script>

<style scoped>
.skeleton-loading-container {
  width: 100%;
}

.skeleton-wrapper {
  padding: 16px;
}
</style>
