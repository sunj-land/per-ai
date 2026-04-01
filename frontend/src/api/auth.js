/*
 * @Author: Project Rules
 * @Date: 2024-03-14
 * @Description: Authentication API encapsulation
 */
import request from "@/utils/request";

const BASE_URL = "/v1/auth";

/**
 * 用户登录
 * 将账号密码转换为 form-urlencoded 格式进行请求
 * @param {string} username - 用户名
 * @param {string} password - 密码
 * @returns {Promise<Object>} 返回包含 access_token, refresh_token 和 token_type 的对象
 */
export const login = async (username, password) => {
	const formData = new URLSearchParams();
	formData.append("username", username);
	formData.append("password", password);

	// Login usually triggers full loading
	return request.post(`${BASE_URL}/token`, formData, {
		headers: {
			"Content-Type": "application/x-www-form-urlencoded",
		},
		loading: "auth-login", // Enable specific loading key
	});
};

/**
 * 用户注册
 * @param {Object} userData - 注册相关的用户数据
 * @returns {Promise<Object>} 返回新注册的用户信息
 */
export const register = async (userData) => {
	return request.post(`${BASE_URL}/register`, userData, {
		loading: "auth-register",
	});
};

/**
 * 获取当前登录用户信息
 * 此接口通常为静默检查，不触发全局 loading
 * @returns {Promise<Object>} 返回当前用户信息
 */
export const getMe = async () => {
	return request.get(`${BASE_URL}/me`, {
		loading: false, // Silent check
	});
};

/**
 * 忘记密码，请求重置链接
 * @param {string} email - 用户注册的邮箱
 * @returns {Promise<Object>} 返回操作提示信息
 */
export const forgotPassword = async (email) => {
	return request.post(
		`${BASE_URL}/forgot-password`,
		{ email },
		{
			loading: true,
		},
	);
};

/**
 * 重置密码
 * @param {string} token - 邮箱收到的重置 token
 * @param {string} newPassword - 新密码
 * @returns {Promise<Object>} 返回操作提示信息
 */
export const resetPassword = async (token, newPassword) => {
	return request.post(
		`${BASE_URL}/reset-password`,
		{
			token,
			new_password: newPassword,
		},
		{
			loading: true,
		},
	);
};

/**
 * 刷新认证 token
 * @param {string} refreshToken - 用于刷新的 token
 * @returns {Promise<Object>} 返回新的 access_token, refresh_token 等信息
 */
export const refreshToken = async (refreshToken) => {
	return request.post(
		`${BASE_URL}/refresh`,
		{ refresh_token: refreshToken },
		{
			loading: false,
		},
	);
};
