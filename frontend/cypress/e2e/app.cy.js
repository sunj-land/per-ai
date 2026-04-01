// 导入 cypress 的相关 API
describe("App E2E Test", () => {
	// 测试用例：访问根 URL 并检查页面内容
	it("visits the app root url", () => {
		// 访问在 cypress.config.js 中配置的 baseUrl
		cy.visit("/");
		// 断言：页面上应该包含一个带有 “Vite + Vue” 文本的 h1 标签
		cy.contains("h1", "Vite + Vue");
	});
});
