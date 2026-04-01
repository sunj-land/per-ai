/*
 * @Author: Project Rules
 * @Date: 2024-03-14
 * @Description: Unified Request Utility with Loading and Error Handling
 */

import { Message } from "@arco-design/web-vue";
import axios from "axios";
import qs from "qs";
import { useLoadingStore } from "../store/loading";

// Create axios instance
const service = axios.create({
	baseURL: "/api", // Proxy will handle the rest
	timeout: 300000, // 5 minutes timeout
	paramsSerializer: (params) => {
		return qs.stringify(params, { arrayFormat: "repeat" });
	},
});

// Request interceptor
service.interceptors.request.use(
	(config) => {
		// Access store inside interceptor to ensure Pinia is initialized
		const loadingStore = useLoadingStore();

		// Add token
		const token = localStorage.getItem("access_token");
		if (token) {
			config.headers.Authorization = `Bearer ${token}`;
		}

		// Handle loading
		// config.loading:
		// - true (or undefined): Global loading (default)
		// - false: No loading
		// - string: Local loading with this key
		const showLoading = config.loading !== false;
		const loadingKey =
			typeof config.loading === "string" ? config.loading : null;

		if (showLoading) {
			loadingStore.startLoading(loadingKey);
		}

		// Add cancel token/signal
		// If signal is already provided, respect it, otherwise create new one
		if (!config.signal) {
			const controller = new AbortController();
			config.signal = controller.signal;

			// Store controller for cancellation
			const requestId = `req_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
			config.requestId = requestId;

			// Track request in store for cancellation
			if (showLoading) {
				loadingStore.addRequest(requestId, controller);
			}
		}

		return config;
	},
	(error) => {
		return Promise.reject(error);
	},
);

// Response interceptor
service.interceptors.response.use(
	(response) => {
		const loadingStore = useLoadingStore();
		const { loading, requestId } = response.config;

		if (loading !== false) {
			const loadingKey = typeof loading === "string" ? loading : null;
			loadingStore.stopLoading(loadingKey);
		}

		if (requestId) {
			loadingStore.removeRequest(requestId);
		}

		return response.data;
	},
	(error) => {
		const loadingStore = useLoadingStore();
		const { config } = error;

		if (config) {
			const { loading, requestId } = config;
			if (loading !== false) {
				const loadingKey = typeof loading === "string" ? loading : null;
				loadingStore.stopLoading(loadingKey);
			}
			if (requestId) {
				loadingStore.removeRequest(requestId);
			}
		}

		// Handle cancellation
		if (axios.isCancel(error)) {
			return Promise.reject(error);
		}

		// Error handling
		const msg =
			error.response?.data?.detail || error.message || "Request failed";

		// Handle 401 Unauthorized
		if (error.response?.status === 401) {
			// Clear token?
			// TODO Let the store or router handle redirection if needed
		}

		// Only show message if not silent
		if (!config?.silent) {
			Message.error(msg);
		}

		return Promise.reject(error);
	},
);

export default service;
