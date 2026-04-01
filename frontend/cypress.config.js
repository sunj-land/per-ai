import { defineConfig } from "cypress";

export default defineConfig({
	allowCypressEnv: false,

	e2e: {
		baseUrl: "http://localhost:5174",
		setupNodeEvents(_on, _config) {
			// implement node event listeners here
		},
	},
});
