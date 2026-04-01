import { createTestingPinia } from "@pinia/testing";
import { flushPromises, mount } from "@vue/test-utils";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { scoreRssArticles } from "../../../api/agent-center.js";
import RSSArticles from "../RSSArticles.vue";

const pushMock = vi.fn();
const replaceMock = vi.fn();

vi.mock("vue-router", () => ({
	useRoute: () => ({
		query: {},
	}),
	useRouter: () => ({
		push: pushMock,
		replace: replaceMock,
	}),
}));

vi.mock("../../../api/rss.js", () => ({
	getArticles: vi.fn().mockResolvedValue([
		{
			id: 101,
			title: "AI Agent 增长趋势完整指南",
			summary: "从产品策略到自动化工作流的完整拆解。",
			feed_title: "AI Weekly",
			published_at: "2026-03-25T01:19:29.470272",
			author: "SunJie",
			category: "AI",
		},
		{
			id: 102,
			title: "企业自动化工作流实战",
			summary: "聚焦流程重构与效率提升。",
			feed_title: "Automation Daily",
			published_at: "2026-03-24T01:19:29.470272",
			author: "SunJie",
			category: "Workflow",
		},
		{
			id: 103,
			title: "深度学习新趋势解读",
			summary: "2026年最新深度学习研究方向总结。",
			feed_title: "Tech Daily",
			published_at: "2026-03-23T01:19:29.470272",
			author: "Alex",
			category: "AI",
		},
	]),
}));

vi.mock("../../../api/vector.js", () => ({
	searchVectors: vi.fn().mockResolvedValue([]),
}));

vi.mock("../../../api/agent-center.js", () => ({
	getRssQualityResults: vi.fn().mockResolvedValue([
		{
			id: "score-1",
			batchId: "batch-1",
			articleId: 101,
			articleTitle: "AI Agent 增长趋势完整指南",
			overallScore: 89.5,
			grade: "excellent",
			createdAt: "2026-03-25T02:00:00.000Z",
			report: {
				dimensions: {
					originality: { score: 90, reasons: ["原创性较高"] },
					information_value: { score: 88, reasons: ["信息密度较高"] },
					writing_quality: { score: 86, reasons: ["结构清晰"] },
					interaction_potential: { score: 91, reasons: ["标题吸引力较强"] },
					timeliness: { score: 92, reasons: ["发布时间较新"] },
				},
			},
		},
		{
			id: "score-2",
			batchId: "batch-1",
			articleId: 102,
			articleTitle: "企业自动化工作流实战",
			overallScore: 76.5,
			grade: "good",
			createdAt: "2026-03-25T01:00:00.000Z",
			report: {
				dimensions: {
					originality: { score: 78, reasons: ["原创性良好"] },
					information_value: { score: 80, reasons: ["信息价值稳定"] },
					writing_quality: { score: 74, reasons: ["可读性良好"] },
					interaction_potential: { score: 72, reasons: ["互动潜力一般"] },
					timeliness: { score: 79, reasons: ["具备一定时效性"] },
				},
			},
		},
		{
			id: "score-3",
			batchId: "batch-2",
			articleId: 103,
			articleTitle: "深度学习新趋势解读",
			overallScore: 93.0,
			grade: "excellent",
			createdAt: "2026-03-25T03:00:00.000Z",
			report: {
				dimensions: {
					originality: { score: 94, reasons: ["原创性强"] },
					information_value: { score: 92, reasons: ["信息价值高"] },
					writing_quality: { score: 91, reasons: ["表达顺畅"] },
					interaction_potential: { score: 94, reasons: ["标题有吸引力"] },
					timeliness: { score: 95, reasons: ["内容新鲜"] },
				},
			},
		},
	]),
	scoreRssArticles: vi.fn().mockResolvedValue({
		summary: {
			success: 2,
			averageScore: 83,
		},
		results: [
			{
				id: "score-1",
				batchId: "batch-1",
				articleId: 101,
				articleTitle: "AI Agent 增长趋势完整指南",
				overallScore: 89.5,
				grade: "excellent",
				createdAt: "2026-03-25T02:00:00.000Z",
				report: {
					dimensions: {
						originality: { score: 90, reasons: ["原创性较高"] },
						information_value: { score: 88, reasons: ["信息密度较高"] },
						writing_quality: { score: 86, reasons: ["结构清晰"] },
						interaction_potential: { score: 91, reasons: ["标题吸引力较强"] },
						timeliness: { score: 92, reasons: ["发布时间较新"] },
					},
				},
			},
			{
				id: "score-2",
				batchId: "batch-1",
				articleId: 102,
				articleTitle: "企业自动化工作流实战",
				overallScore: 76.5,
				grade: "good",
				createdAt: "2026-03-25T01:00:00.000Z",
				report: {
					dimensions: {
						originality: { score: 78, reasons: ["原创性良好"] },
						information_value: { score: 80, reasons: ["信息价值稳定"] },
						writing_quality: { score: 74, reasons: ["可读性良好"] },
						interaction_potential: { score: 72, reasons: ["互动潜力一般"] },
						timeliness: { score: 79, reasons: ["具备一定时效性"] },
					},
				},
			},
		],
	}),
}));

const makeWrapper = () =>
	mount(RSSArticles, {
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
				GroupTree: true,
				ChannelSelectorModal: true,
				"a-page-header": true,
				"a-space": true,
				"a-input-search": true,
				"a-popover": true,
				"a-button": true,
				"a-slider": true,
				"a-input-number": true,
				"a-select": true,
				"a-option": true,
				"a-card": true,
				"a-list": true,
				"a-list-item": true,
				"a-list-item-meta": true,
				"a-typography-title": true,
				"a-typography-text": true,
				"a-typography-paragraph": true,
				"a-empty": true,
				"a-tag": true,
				"a-avatar": true,
				"a-skeleton": true,
				"a-skeleton-shape": true,
				"a-skeleton-line": true,
				"a-divider": true,
				"a-drawer": true,
				"a-descriptions": true,
				"a-descriptions-item": true,
				"a-progress": true,
				"a-spin": true,
				"a-table": true,
				"a-table-column": true,
			},
		},
	});

describe("RSSArticles.vue", () => {
	beforeEach(() => {
		vi.clearAllMocks();
		global.IntersectionObserver = vi.fn().mockImplementation(() => ({
			observe: vi.fn(),
			disconnect: vi.fn(),
			unobserve: vi.fn(),
		}));
	});

	it("renders score controls and supports quick filter and score sort", async () => {
		const wrapper = makeWrapper();
		await flushPromises();

		expect(wrapper.html()).toContain("评分当前列表");
		expect(wrapper.html()).toContain("已评分");
		expect(wrapper.html()).toContain("质量分");
		expect(wrapper.vm.filteredArticles.length).toBe(3);
		expect(wrapper.vm.displayedArticles[0].id).toBe(101);

		wrapper.vm.scoreFilter.minScore = 90;
		await flushPromises();

		expect(wrapper.vm.filteredArticles.length).toBe(1);

		wrapper.vm.applyQuickScoreFilter("high");
		await flushPromises();

		expect(wrapper.vm.filteredArticles.length).toBe(2);
		expect(wrapper.vm.quickScoreFilterLabel).toBe("快捷筛选 80+");

		wrapper.vm.applyQuickScoreFilter("all");
		await flushPromises();

		expect(wrapper.vm.filteredArticles.length).toBe(3);

		wrapper.vm.sortMode = "score_asc";
		await flushPromises();

		expect(wrapper.vm.displayedArticles[0].id).toBe(102);
		expect(wrapper.vm.displayedArticles[2].id).toBe(103);
	});

	it("supports grade filter and unscored-only filter", async () => {
		const wrapper = makeWrapper();
		await flushPromises();

		wrapper.vm.gradeFilter = "excellent";
		await flushPromises();
		expect(wrapper.vm.filteredArticles.length).toBe(2);
		expect(wrapper.vm.filteredArticles.map((a) => a.id).sort()).toEqual([
			101, 103,
		]);

		wrapper.vm.gradeFilter = undefined;
		await flushPromises();
		expect(wrapper.vm.filteredArticles.length).toBe(3);

		wrapper.vm.toggleOnlyUnscored();
		await flushPromises();
		expect(wrapper.vm.filteredArticles.length).toBe(0);
	});

	it("batch history groups results by batchId", async () => {
		const { getRssQualityResults } = await import(
			"../../../api/agent-center.js"
		);
		const wrapper = makeWrapper();
		await flushPromises();

		await wrapper.vm.openBatchHistory();
		await flushPromises();

		expect(getRssQualityResults).toHaveBeenCalled();

		expect(wrapper.vm.batchHistory.length).toBeGreaterThan(0);
		const batch = wrapper.vm.batchHistory.find((b) => b.batchId === "batch-1");
		expect(batch).toBeDefined();
		expect(batch.successCount).toBe(2);
		expect(batch.averageScore).toBeCloseTo((89.5 + 76.5) / 2);
	});
});
