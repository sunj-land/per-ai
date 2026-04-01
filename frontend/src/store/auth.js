/*
 * @Author: Project Rules
 * @Date: 2024-03-14
 * @Description: Authentication Store using Pinia
 */
import { defineStore } from "pinia";
import { computed, ref } from "vue";
import { login as apiLogin, register as apiRegister, getMe } from "../api/auth";
import { useLoadingStore } from "./loading";

export const useAuthStore = defineStore("auth", () => {
	const loadingStore = useLoadingStore();

	const user = ref(null);
	const token = ref(localStorage.getItem("access_token") || "");
	const refreshToken = ref(localStorage.getItem("refresh_token") || "");
	const error = ref(null);

	const loading = computed(
		() =>
			loadingStore.isLoading("auth-login") ||
			loadingStore.isLoading("auth-register") ||
			loadingStore.isLoading("auth-me"),
	);

	const isAuthenticated = computed(() => !!token.value);
	const isAdmin = computed(() => {
		// Check if user has admin role
		return user.value?.roles?.some((role) => role.name === "admin") || false;
	});

	// ========== Action: Login ==========
	const login = async (username, password) => {
		error.value = null;
		try {
			const data = await apiLogin(username, password);
			setToken(data.access_token, data.refresh_token);
			await fetchUser();
			return true;
		} catch (err) {
			error.value = err.response?.data?.detail || "Login failed";
			throw err;
		}
	};

	// ========== Action: Register ==========
	const register = async (userData) => {
		error.value = null;
		try {
			await apiRegister(userData);
			// Optional: Auto login after register
			return true;
		} catch (err) {
			error.value = err.response?.data?.detail || "Registration failed";
			throw err;
		}
	};

	// ========== Action: Fetch User ==========
	const fetchUser = async () => {
		if (!token.value) return;
		try {
			const data = await getMe();
			user.value = data;
		} catch (err) {
			// If 401, try refresh or logout
			if (err.response?.status === 401) {
				logout();
			}
			console.error("Failed to fetch user", err);
		}
	};

	// ========== Action: Logout ==========
	const logout = () => {
		user.value = null;
		token.value = "";
		refreshToken.value = "";
		localStorage.removeItem("access_token");
		localStorage.removeItem("refresh_token");
		// Redirect handled by component or router
	};

	// ========== Helper: Set Token ==========
	const setToken = (accessToken, refToken) => {
		token.value = accessToken;
		refreshToken.value = refToken;
		localStorage.setItem("access_token", accessToken);
		localStorage.setItem("refresh_token", refToken);
	};

	return {
		user,
		token,
		loading,
		error,
		isAuthenticated,
		isAdmin,
		login,
		register,
		fetchUser,
		logout,
	};
});
