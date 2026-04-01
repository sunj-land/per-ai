<template>
  <div class="login-container">
    <div class="login-card">
      <div class="header">
        <h2 class="title">系统登录</h2>
        <p class="subtitle">欢迎回来，请登录您的账号</p>
      </div>

      <a-form :model="form" @submit="handleSubmit" layout="vertical">
        <a-form-item field="username" label="用户名" :rules="[{ required: true, message: '请输入用户名' }]">
          <a-input v-model="form.username" placeholder="请输入用户名" allow-clear>
            <template #prefix>
              <icon-user />
            </template>
          </a-input>
        </a-form-item>

        <a-form-item field="password" label="密码" :rules="[{ required: true, message: '请输入密码' }]">
          <a-input-password v-model="form.password" placeholder="请输入密码" allow-clear>
            <template #prefix>
              <icon-lock />
            </template>
          </a-input-password>
        </a-form-item>

        <div class="form-actions">
          <a-checkbox v-model="form.rememberMe">记住我</a-checkbox>
          <router-link to="/auth/forgot-password" class="forgot-password-link">忘记密码？</router-link>
        </div>

        <a-form-item>
          <a-button type="primary" html-type="submit" long :loading="authStore.loading">登录</a-button>
        </a-form-item>
      </a-form>
      
      <div v-if="authStore.error" class="error-message">
        <a-alert type="error">{{ authStore.error }}</a-alert>
      </div>
    </div>
  </div>
</template>

<script setup>
/*
 * @Author: Project Rules
 * @Date: 2024-03-14
 * @Description: Enhanced Login Page
 */

import { Message } from "@arco-design/web-vue";
import { reactive } from "vue";
import { useRouter } from "vue-router";
import { useAuthStore } from "../../store/auth";

const router = useRouter();
const authStore = useAuthStore();

const form = reactive({
	username: "admin",
	password: "Admin@123456",
	rememberMe: true,
});

/**
 * 处理登录表单提交
 * @param {Object} context - 提交上下文
 * @param {Object} context.errors - 表单校验错误信息
 * @returns {Promise<void>}
 */
const handleSubmit = async ({ errors }) => {
	if (errors) return;

	try {
		await authStore.login(form.username, form.password);
		Message.success("登录成功");
		router.push("/");
	} catch (_error) {
		// Error is handled in store and displayed via authStore.error
	}
};
</script>

<style scoped>
.login-container {
  display: flex;
  justify-content: center;
  align-items: center;
  min-height: 100vh;
  background-color: var(--color-bg-2);
  background-image: radial-gradient(#e5e7eb 1px, transparent 1px);
  background-size: 20px 20px;
}

.login-card {
  width: 100%;
  max-width: 400px;
  padding: 40px;
  background: var(--color-bg-1);
  border-radius: 12px;
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.05);
  border: 1px solid var(--color-border-2);
}

.header {
  text-align: center;
  margin-bottom: 32px;
}

.title {
  margin: 0;
  font-size: 24px;
  font-weight: 600;
  color: var(--color-text-1);
}

.subtitle {
  margin-top: 8px;
  color: var(--color-text-3);
  font-size: 14px;
}

.form-actions {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 24px;
}

.forgot-password-link {
  color: rgb(var(--primary-6));
  text-decoration: none;
  font-size: 14px;
}

.forgot-password-link:hover {
  color: rgb(var(--primary-5));
}

.error-message {
  margin-top: 16px;
}
</style>
