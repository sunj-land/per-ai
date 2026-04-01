<template>
  <div class="table-card">
    <a-table :data="payload.data" :columns="payload.columns" :pagination="false" />
  </div>
</template>

<script setup>
defineProps({
	payload: {
		type: Object,
		required: true,
	},
});
</script>

<style scoped>
.table-card {
  margin: 12px 0;
  border: 1px solid var(--color-border-2);
  border-radius: 8px;
  overflow: hidden;
}
</style>
