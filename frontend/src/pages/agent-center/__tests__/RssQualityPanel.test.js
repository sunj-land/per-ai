import { createTestingPinia } from "@pinia/testing";
import { flushPromises, mount } from "@vue/test-utils";
import { beforeEach, describe, expect, it, vi } from "vitest";

import RssQualityPanel from "../RssQualityPanel.vue";

vi.mock("@/api/rss", () => ({
	getFeeds: vi.fn().mockResolvedValue([
		{
			id: 1,
			title: "AI Weekly",
			url: "https://example.com/rss.xml",
		},
	]),
}));

vi.mock("@/api/agent-center", () => ({
	getDefaultRssQualityConfig: vi.fn().mockResolvedValue({
		name: "RSS 默认评分规则",
		weights: {
			originality: 0.24,
			information_value: 0.24,
			writing_quality: 0.18,
			interaction_potential: 0.17,
			timeliness: 0.17,
		},
		thresholds: {
			excellent: 85,
			good: 70,
			review: 55,
		},
		settings: {
			originality: { comparison_window: 25 },
			timeliness: { fresh_hours: 48 },
		},
	}),
	getRssQualityConfig: vi.fn().mockResolvedValue({
		name: "运营规则",
		weights: {
			originality: 0.24,
			information_value: 0.24,
			writing_quality: 0.18,
			interaction_potential: 0.17,
			timeliness: 0.17,
		},
		thresholds: {
			excellent: 85,
			good: 70,
			review: 55,
		},
		settings: {
			originality: { comparison_window: 30 },
			timeliness: { fresh_hours: 36 },
		},
	}),
	getRssQualityLogs: vi.fn().mockResolvedValue([]),
	getRssQualityResults: vi.fn().mockResolvedValue([
		{
			id: "1",
			batchId: "batch-1",
			articleId: 1,
			articleTitle: "2026 AI Agent 增长趋势完整指南",
			feedTitle: "AI Weekly",
			overallScore: 88.5,
			grade: "excellent",
			dimensions: {
				originality: 90,
				information_value: 86,
				writing_quality: 84,
				interaction_potential: 88,
				timeliness: 89,
			},
			report: {
				dimensions: {
					originality: { score: 90, reasons: ["重复率较低"] },
					information_value: { score: 86, reasons: ["关键词密度较高"] },
					writing_quality: { score: 84, reasons: ["结构清晰"] },
					interaction_potential: { score: 88, reasons: ["标题吸引力高"] },
					timeliness: { score: 89, reasons: ["内容较新"] },
				},
			},
		},
	]),
	scoreRssArticles: vi.fn().mockResolvedValue({
		batchId: "batch-1",
		summary: {
			total: 1,
			success: 1,
			failed: 0,
			averageScore: 88.5,
		},
		results: [],
	}),
	updateRssQualityConfig: vi.fn().mockResolvedValue({
		name: "运营规则",
		weights: {
			originality: 0.24,
			information_value: 0.24,
			writing_quality: 0.18,
			interaction_potential: 0.17,
			timeliness: 0.17,
		},
		thresholds: {
			excellent: 85,
			good: 70,
			review: 55,
		},
		settings: {
			originality: { comparison_window: 30 },
			timeliness: { fresh_hours: 36 },
		},
	}),
}));

describe("RssQualityPanel.vue", () => {
	beforeEach(() => {
		vi.clearAllMocks();
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

	it("renders rss quality panel and loads initial data", async () => {
		const wrapper = mount(RssQualityPanel, {
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
					"a-row": true,
					"a-col": true,
					"a-card": true,
					"a-space": true,
					"a-input": true,
					"a-tag": true,
					"a-slider": true,
					"a-input-number": true,
					"a-divider": true,
					"a-button": true,
					"a-select": true,
					"a-option": true,
					"a-textarea": true,
					"a-statistic": true,
					"a-empty": true,
					"a-table": true,
					"a-table-column": true,
					"a-drawer": true,
					"a-descriptions": true,
					"a-descriptions-item": true,
					"a-progress": true,
				},
			},
		});

		await flushPromises();

		expect(wrapper.html()).toContain("评分规则配置");
		expect(wrapper.html()).toContain("批量评分任务");
		expect(wrapper.html()).toContain("评分结果筛选");
		expect(wrapper.vm.results.length).toBe(1);
	});
});
