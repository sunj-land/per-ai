<template>
  <div class="reset-password-container">
    <div class="reset-password-card">
      <h2 class="title">重置密码</h2>
      
      <a-form :model="form" @submit="handleSubmit" layout="vertical">
        <a-form-item field="newPassword" label="新密码" :rules="rules.newPassword">
          <a-input-password v-model="form.newPassword" placeholder="请输入新密码" allow-clear />
        </a-form-item>
        
        <a-form-item field="confirmPassword" label="确认新密码" :rules="rules.confirmPassword">
          <a-input-password v-model="form.confirmPassword" placeholder="请再次输入新密码" allow-clear />
        </a-form-item>
        
        <a-form-item>
          <a-button type="primary" html-type="submit" long :loading="loading">重置密码</a-button>
        </a-form-item>
      </a-form>
      
      <div v-if="message" class="success-message">
        <a-alert type="success">
          {{ message }}
          <template #action>
            <router-link to="/login">立即登录</router-link>
          </template>
        </a-alert>
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
 * @Description: Reset Password Page
 */
import { reactive, ref } from "vue";
import { useRoute, useRouter } from "vue-router";
import { resetPassword } from "../../api/auth";

const route = useRoute();
const router = useRouter();
const token = route.query.token;

const form = reactive({
	newPassword: "",
	confirmPassword: "",
});
const loading = ref(false);
const message = ref("");
const error = ref("");

const _rules = {
	newPassword: [
		{ required: true, message: "请输入新密码" },
		{ minLength: 8, message: "密码长度至少8位" },
		{
			match:
				/^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[!@#$%^&*(),.?":{}|<>]).{8,}$/,
			message: "密码需包含大小写字母、数字和特殊字符",
		},
	],
	confirmPassword: [
		{ required: true, message: "请确认新密码" },
		{
			validator: (value, cb) => {
				if (value !== form.newPassword) {
					cb("两次输入的密码不一致");
				} else {
					cb();
				}
			},
		},
	],
};

const _handleSubmit = async ({ errors }) => {
	if (errors) return;
	if (!token) {
		error.value = "无效的重置链接";
		return;
	}

	loading.value = true;
	message.value = "";
	error.value = "";

	try {
		const res = await resetPassword(token, form.newPassword);
		message.value = res.message;
		// Delay redirect
		setTimeout(() => {
			router.push("/login");
		}, 3000);
	} catch (err) {
		error.value = err.response?.data?.detail || "重置失败，请重试";
	} finally {
		loading.value = false;
	}
};
</script>

<style scoped>
.reset-password-container {
  display: flex;
  justify-content: center;
  align-items: center;
  min-height: 100vh;
  background-color: var(--color-bg-2);
}

.reset-password-card {
  width: 100%;
  max-width: 400px;
  padding: 32px;
  background: var(--color-bg-1);
  border-radius: 8px;
  box-shadow: 0 4px 10px rgba(0, 0, 0, 0.1);
}

.title {
  text-align: center;
  margin-bottom: 24px;
  color: var(--color-text-1);
}

.success-message, .error-message {
  margin-top: 16px;
}
</style>
