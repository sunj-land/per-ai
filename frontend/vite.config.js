import { resolve } from "node:path";
import { vitePluginForArco } from "@arco-plugins/vite-vue";
import VueI18n from "@intlify/unplugin-vue-i18n/vite";
import vue from "@vitejs/plugin-vue";
import AutoImport from "unplugin-auto-import/vite";
import VueMacros from "unplugin-vue-macros/vite";
import { defineConfig } from "vite";
import Inspector from "vite-plugin-vue-inspector";

const frontendHealthPlugin = () => ({
	name: "frontend-health-plugin",
	configureServer(server) {
		server.middlewares.use("/frontend/health", (_req, res) => {
			res.statusCode = 200;
			res.setHeader("Content-Type", "application/json; charset=utf-8");
			res.end(JSON.stringify({ status: "ok" }));
		});
	},
});

// https://vite.dev/config/
export default defineConfig({
	plugins: [
		vue(),
		VueMacros(),
		// 移除 include 选项，避免与手动导入冲突
		VueI18n(),
		vitePluginForArco({
			style: "css",
		}),
		Inspector(),
		AutoImport({
			imports: ["vue", "vue-router", "@vueuse/core", "vue-i18n"],
			dts: "src/auto-imports.d.ts",
		}),
		frontendHealthPlugin(),
	],
	resolve: {
		alias: {
			"@": resolve(__dirname, "src"),
		},
	},
	server: {
		proxy: {
			"/agents-api": {
				target: "http://localhost:8001",
				changeOrigin: true,
				rewrite: (path) => path.replace(/^\/agents-api/, "/api"),
				timeout: 300000,
				proxyTimeout: 300000,
			},
			"/api": {
				target: "http://localhost:8000",
				changeOrigin: true,
				timeout: 300000,
				proxyTimeout: 300000,
			},
		},
	},
	optimizeDeps: {
		include: ["qs"],
	},
	test: {
		globals: true,
		environment: "jsdom",
	},
});
