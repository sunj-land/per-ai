/*
 * @Author: Project Rules
 * @Date: 2024-03-14
 * @Description: Global Loading State Management
 */
import { defineStore } from "pinia";
import { ref } from "vue";

export const useLoadingStore = defineStore("loading", () => {
	// Global loading state (for full-screen overlay)
	const globalLoading = ref(false);

	// Request counter to handle multiple parallel requests
	const requestCount = ref(0);

	// Map to store active requests for cancellation
	// Key: requestId (string), Value: AbortController
	const activeRequests = ref(new Map());

	// Local loading map for specific components/blocks
	// Key: Unique identifier (e.g., 'user-list', 'chat-messages')
	// Value: Boolean
	const loadingMap = ref(new Map());

	// Minimum loading time to prevent flickering (ms)
	const MIN_LOADING_TIME = 300;

	// Timer for minimum loading
	let minLoadTimer = null;
	let startTime = 0;

	/**
	 * Register a request to be tracked
	 * @param {string} id - Request ID
	 * @param {AbortController} controller
	 */
	const addRequest = (id, controller) => {
		activeRequests.value.set(id, controller);
	};

	/**
	 * Remove a request from tracking
	 * @param {string} id - Request ID
	 */
	const removeRequest = (id) => {
		activeRequests.value.delete(id);
	};

	/**
	 * Cancel all active requests
	 */
	const cancelAll = () => {
		activeRequests.value.forEach((controller) => {
			controller.abort();
		});
		activeRequests.value.clear();
		stopLoading(null, true);
	};

	/**
	 * Start global loading
	 * @param {string} [key] - Optional key for local loading
	 */
	const startLoading = (key = null) => {
		if (key) {
			loadingMap.value.set(key, true);
		} else {
			if (requestCount.value === 0) {
				startTime = Date.now();
				globalLoading.value = true;
			}
			requestCount.value++;
		}
	};

	/**
	 * Stop global loading
	 * @param {string} [key] - Optional key for local loading
	 * @param {boolean} [force] - Force stop global loading
	 */
	const stopLoading = (key = null, force = false) => {
		if (key) {
			loadingMap.value.set(key, false);
			loadingMap.value.delete(key); // Cleanup
		} else {
			if (force) {
				requestCount.value = 0;
				globalLoading.value = false;
				return;
			}

			if (requestCount.value > 0) {
				requestCount.value--;
			}

			if (requestCount.value === 0) {
				const elapsedTime = Date.now() - startTime;
				if (elapsedTime < MIN_LOADING_TIME) {
					// Delay hiding to ensure minimum display time
					if (minLoadTimer) clearTimeout(minLoadTimer);
					minLoadTimer = setTimeout(() => {
						globalLoading.value = false;
					}, MIN_LOADING_TIME - elapsedTime);
				} else {
					globalLoading.value = false;
				}
			}
		}
	};

	/**
	 * Check if a specific key is loading
	 * @param {string} key
	 * @returns {boolean}
	 */
	const isLoading = (key) => {
		return loadingMap.value.get(key) || false;
	};

	return {
		globalLoading,
		requestCount,
		startLoading,
		stopLoading,
		isLoading,
		addRequest,
		removeRequest,
		cancelAll,
	};
});
