<template>
  <div class="block-loading-container" :class="{ 'is-loading': loading }">
    <div v-if="loading" class="loading-overlay">
      <a-spin :size="size" :tip="tip" />
    </div>
    <slot></slot>
  </div>
</template>

<script setup>
defineProps({
	loading: {
		type: Boolean,
		default: false,
	},
	tip: {
		type: String,
		default: "",
	},
	size: {
		type: [Number, String],
		default: 32,
	},
});
</script>

<style scoped>
.block-loading-container {
  position: relative;
  width: 100%;
  height: 100%;
  min-height: 100px; /* Ensure minimum height for spinner visibility */
}

.loading-overlay {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  background-color: rgba(255, 255, 255, 0.6);
  z-index: 10;
  display: flex;
  justify-content: center;
  align-items: center;
  backdrop-filter: blur(1px);
  border-radius: inherit;
}

/* Dark mode support */
@media (prefers-color-scheme: dark) {
  .loading-overlay {
    background-color: rgba(0, 0, 0, 0.5);
  }
}
</style>
