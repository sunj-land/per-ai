// 导入 vitest 的相关 API

import { createTestingPinia } from "@pinia/testing";
// 导入 Vue Test Utils 的相关 API
import { mount } from "@vue/test-utils";
import { beforeAll, describe, expect, it, vi } from "vitest";
import { createRouter, createWebHistory } from "vue-router";
import App from "./src/App.vue";
const router = createRouter({
	history: createWebHistory(),
	routes: [{ path: "/", component: { template: "<div>Home</div>" } }],
});

beforeAll(() => {
	// Mock localStorage
	global.localStorage = {
		getItem: vi.fn(),
		setItem: vi.fn(),
		removeItem: vi.fn(),
		clear: vi.fn(),
	};
});

describe("App.vue", () => {
	// 测试用例：检查组件是否能够被成功挂载
	it("should mount successfully", async () => {
		// 挂载组件
		const wrapper = mount(App, {
			global: {
				plugins: [
					router,
					createTestingPinia({
						createSpy: vi.fn,
					}),
				],
			},
		});
		// 断言：期望组件存在
		expect(wrapper.exists()).toBe(true);
	});
});
