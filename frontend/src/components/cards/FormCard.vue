<template>
  <a-card class="form-card" :title="title">
    <a-form :model="formData" layout="vertical" @submit="handleSubmit">
      <a-form-item v-for="field in fields" :key="field.name" :field="field.name" :label="field.label">
        <a-input v-if="field.type === 'text'" v-model="formData[field.name]" :placeholder="field.placeholder" />
        <a-textarea v-else-if="field.type === 'textarea'" v-model="formData[field.name]" :placeholder="field.placeholder" />
        <a-select v-else-if="field.type === 'select'" v-model="formData[field.name]" :options="field.options" :placeholder="field.placeholder" />
        <a-date-picker v-else-if="field.type === 'date'" v-model="formData[field.name]" style="width: 100%" />
      </a-form-item>
      <a-form-item>
        <a-button type="primary" html-type="submit" long :loading="loading">Submit</a-button>
      </a-form-item>
    </a-form>
  </a-card>
</template>

<script setup>
import { Message } from "@arco-design/web-vue";
import { reactive, ref } from "vue";

const _props = defineProps({
	title: { type: String, default: "Contact Us" },
	fields: {
		type: Array,
		default: () => [
			{ name: "name", label: "Name", type: "text", placeholder: "Your name" },
			{
				name: "email",
				label: "Email",
				type: "text",
				placeholder: "Your email",
			},
			{
				name: "type",
				label: "Type",
				type: "select",
				options: ["Support", "Sales", "Other"],
				placeholder: "Select type",
			},
			{
				name: "message",
				label: "Message",
				type: "textarea",
				placeholder: "How can we help?",
			},
		],
	},
});

const _formData = reactive({});
const loading = ref(false);

const _handleSubmit = ({ values, errors }) => {
	if (errors) return;
	loading.value = true;
	// Simulate API call
	setTimeout(() => {
		loading.value = false;
		Message.success("Submitted successfully!");
		console.log("Form Data:", values);
	}, 1000);
};
</script>

<style scoped>
.form-card { width: 100%; max-width: 400px; border-radius: 8px; }
</style>
