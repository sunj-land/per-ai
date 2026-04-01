<template>
  <div class="forgot-password-container">
    <div class="forgot-password-card">
      <h2 class="title">忘记密码</h2>
      <p class="subtitle">请输入您的注册邮箱，我们将向您发送重置链接。</p>
      
      <a-form :model="form" @submit="handleSubmit" layout="vertical">
        <a-form-item field="email" label="邮箱" :rules="[{ required: true, message: '请输入邮箱' }, { type: 'email', message: '请输入有效的邮箱地址' }]">
          <a-input v-model="form.email" placeholder="请输入您的邮箱" allow-clear />
        </a-form-item>
        
        <a-form-item>
          <a-button type="primary" html-type="submit" long :loading="loading">发送重置链接</a-button>
        </a-form-item>
        
        <div class="actions">
          <router-link to="/login">返回登录</router-link>
        </div>
      </a-form>
      
      <div v-if="message" class="success-message">
        <a-alert type="success">{{ message }}</a-alert>
      </div>
      <div v-if="error" class="error-message">
        <a-alert type="error">{{ error }}</a-alert>
      </div>
    </div>
  </div>
</template>

<script setup>
/*
 * @Author: Project Rules
 * @Date: 2024-03-14
 * @Description: Forgot Password Page
 */
import { reactive, ref } from "vue";
import { forgotPassword } from "../../api/auth";

const form = reactive({
	email: "",
});
const loading = ref(false);
const message = ref("");
const error = ref("");

const _handleSubmit = async ({ errors }) => {
	if (errors) return;

	loading.value = true;
	message.value = "";
	error.value = "";

	try {
		const res = await forgotPassword(form.email);
		message.value = res.message;
	} catch (err) {
		error.value = err.response?.data?.detail || "请求失败，请稍后重试";
	} finally {
		loading.value = false;
	}
};
</script>

<style scoped>
.forgot-password-container {
  display: flex;
  justify-content: center;
  align-items: center;
  min-height: 100vh;
  background-color: var(--color-bg-2);
}

.forgot-password-card {
  width: 100%;
  max-width: 400px;
  padding: 32px;
  background: var(--color-bg-1);
  border-radius: 8px;
  box-shadow: 0 4px 10px rgba(0, 0, 0, 0.1);
}

.title {
  text-align: center;
  margin-bottom: 8px;
  color: var(--color-text-1);
}

.subtitle {
  text-align: center;
  margin-bottom: 24px;
  color: var(--color-text-3);
  font-size: 14px;
}

.actions {
  text-align: center;
  margin-top: 16px;
}

.success-message, .error-message {
  margin-top: 16px;
}
</style>
