import { createTestingPinia } from "@pinia/testing";
import { flushPromises, mount } from "@vue/test-utils";
import { beforeAll, beforeEach, describe, expect, it, vi } from "vitest";

import SkillList from "../SkillList.vue";

vi.mock("@/api/agent-center", () => ({
	getSkillList: vi.fn().mockResolvedValue([
		{
			id: "1",
			name: "weather",
			description: "weather forecast",
			install_status: "installed",
			version: "1.0.0",
			tags: ["tool"],
		},
	]),
	installSkillByUrl: vi.fn().mockResolvedValue({ task_id: "task-url" }),
	installSkillFromHub: vi.fn().mockResolvedValue({ task_id: "task-hub" }),
	createSkill: vi.fn().mockResolvedValue({}),
	syncSkills: vi.fn().mockResolvedValue([]),
	searchSkillHub: vi.fn().mockResolvedValue([
		{
			name: "weather",
			version: "1.0.0",
			description: "weather forecast",
			tags: ["tool"],
		},
	]),
	getInstallRecords: vi.fn().mockResolvedValue([
		{
			task_id: "task-hub",
			skill_name: "weather",
			target_version: "1.0.0",
			operation: "install",
			status: "success",
			result_message: "ok",
		},
	]),
	streamInstallProgress: vi.fn().mockImplementation((_taskId, onMessage) => {
		setTimeout(
			() => onMessage({ status: "success", progress: 100, message: "done" }),
			0,
		);
		return { close: vi.fn() };
	}),
	uninstallSkill: vi.fn().mockResolvedValue({}),
	upgradeSkill: vi.fn().mockResolvedValue({ task_id: "task-upgrade" }),
}));

describe("SkillList.vue", () => {
	beforeAll(() => {
		Object.defineProperty(window, "matchMedia", {
			writable: true,
			value: vi.fn().mockImplementation(() => ({
				matches: false,
				addEventListener: vi.fn(),
				removeEventListener: vi.fn(),
				addListener: vi.fn(),
				removeListener: vi.fn(),
			})),
		});
	});

	beforeEach(() => {
		vi.clearAllMocks();
	});

	it("renders installed skill data", async () => {
		const wrapper = mount(SkillList, {
			global: {
				plugins: [
					createTestingPinia({
						createSpy: vi.fn,
						initialState: {
							loading: {
								globalLoading: false,
								localLoadings: {},
							},
						},
					}),
				],
				stubs: {
					"a-table": true,
					"a-table-column": true,
					"a-space": true,
					"a-tabs": true,
					"a-tab-pane": true,
					"a-input-search": true,
					"a-select": true,
					"a-option": true,
					"a-button": true,
					"a-alert": true,
					"a-tag": true,
					"a-modal": true,
					"a-form": true,
					"a-form-item": true,
					"a-input": true,
					"a-textarea": true,
					"a-drawer": true,
					SkillDetail: true,
				},
			},
		});
		await flushPromises();
		expect(wrapper.html()).toContain("安装记录");
		expect(wrapper.html()).toContain("Hub结果");
	});

	it("supports search keyword highlight", async () => {
		const wrapper = mount(SkillList, {
			global: {
				plugins: [
					createTestingPinia({
						createSpy: vi.fn,
						initialState: {
							loading: {
								globalLoading: false,
								localLoadings: {},
							},
						},
					}),
				],
				stubs: {
					"a-table": true,
					"a-table-column": true,
					"a-space": true,
					"a-tabs": true,
					"a-tab-pane": true,
					"a-input-search": true,
					"a-select": true,
					"a-option": true,
					"a-button": true,
					"a-alert": true,
					"a-tag": true,
					"a-modal": true,
					"a-form": true,
					"a-form-item": true,
					"a-input": true,
					"a-textarea": true,
					"a-drawer": true,
					SkillDetail: true,
				},
			},
		});
		await flushPromises();
		wrapper.vm.searchQuery = "weather";
		const highlighted = wrapper.vm.highlightText("weather forecast");
		expect(highlighted).toContain("<mark>weather</mark>");
	});
});
