import { createRouter, createWebHistory } from "vue-router";
import { useAuthStore } from "./store/auth";

const routes = [
	{
		path: "/",
		name: "Home",
		component: () => import("./pages/homePage/HomePage.vue"),
	},
	{
		path: "/rss/feeds",
		name: "RSSFeeds",
		component: () => import("./pages/rss/RSSFeeds.vue"),
	},
	{
		path: "/rss/articles",
		name: "RSSArticles",
		component: () => import("./pages/rss/RSSArticles.vue"),
	},
	{
		path: "/rss/articles/:id",
		name: "ArticleDetail",
		component: () => import("./pages/rss/ArticleDetail.vue"),
	},
	{
		path: "/vector/admin",
		name: "VectorAdmin",
		component: () => import("./pages/vector/VectorAdmin.vue"),
	},
	{
		path: "/profile",
		name: "UserProfile",
		component: () => import("./pages/user-profile/UserProfile.vue"),
	},
	{
		path: "/card-center",
		name: "CardCenter",
		component: () => import("./pages/card-center/CardCenter.vue"),
	},
	{
		path: "/task-center",
		name: "TaskCenter",
		component: () => import("./pages/task/TaskCenter.vue"),
	},
	{
		path: "/channels",
		name: "ChannelManage",
		component: () => import("./pages/channel/index.vue"),
	},
	{
		path: "/messages",
		name: "MessageCenter",
		component: () => import("./pages/message/index.vue"),
	},
	{
		path: "/agent-center",
		name: "AgentCenter",
		component: () => import("./pages/agent-center/index.vue"),
	},
	{
		path: "/agent-test",
		name: "AgentTest",
		component: () => import("./pages/agent-test/AgentInterruptTest.vue"),
	},
	{
		path: "/attachment-center",
		name: "AttachmentCenter",
		component: () => import("./pages/attachment/index.vue"),
	},
	{
		path: "/users",
		name: "UserManagement",
		component: () => import("./pages/user/index.vue"),
		meta: { roles: ["admin"] },
	},
	// --- Learning Agent Routes ---
	{
		path: "/login",
		name: "Login",
		component: () => import("./pages/auth/Login.vue"),
	},
	{
		path: "/auth/forgot-password",
		name: "ForgotPassword",
		component: () => import("./pages/auth/ForgotPassword.vue"),
	},
	{
		path: "/auth/reset-password",
		name: "ResetPassword",
		component: () => import("./pages/auth/ResetPassword.vue"),
	},
	{
		path: "/plan",
		name: "PlanDashboard",
		component: () => import("./pages/plan/PlanDashboard.vue"),
	},
	{
		path: "/plan/create",
		name: "PlanCreate",
		component: () => import("./pages/plan/PlanCreate.vue"),
	},
	{
		path: "/schedule",
		name: "Schedule",
		component: () => import("./pages/schedule/index.vue"),
	},
	// -----------------------------
];

const router = createRouter({
	history: createWebHistory(),
	routes,
});

// Navigation Guard
router.beforeEach(async (to, _from) => {
	const authStore = useAuthStore();
	const publicPages = [
		"/login",
		"/auth/forgot-password",
		"/auth/reset-password",
	];
	const authRequired = !publicPages.includes(to.path);

	// If page requires auth and user is not authenticated
	if (authRequired && !authStore.isAuthenticated) {
		return "/login";
	}

	// If authenticated but user info is missing, try to fetch it
	if (authStore.isAuthenticated && !authStore.user) {
		try {
			await authStore.fetchUser();
		} catch (_error) {
			// If fetch fails (e.g. token expired), redirect to login
			authStore.logout();
			return "/login";
		}
	}

	// If user is already authenticated and tries to access login page, redirect to home
	if (to.path === "/login" && authStore.isAuthenticated) {
		return "/";
	}

	// Role check
	if (to.meta.roles && authStore.user) {
		const userRoles = authStore.user.roles
			? authStore.user.roles.map((r) => r.name)
			: [];
		const hasRole = to.meta.roles.some((role) => userRoles.includes(role));

		if (!hasRole) {
			// Redirect to home or 403 page
			// For now redirect to home
			return "/";
		}
	}

	return true;
});

export default router;
