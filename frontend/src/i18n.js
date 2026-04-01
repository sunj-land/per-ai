// 导入 vue-i18n 的相关 API
import { createI18n } from "vue-i18n";

// 导入语言包
import en from "./locales/en.json";
import zhCN from "./locales/zh-CN.json";

// 创建 i18n 实例
const i18n = createI18n({
	legacy: false, // 使用 Composition API
	locale: "zh-CN", // 默认语言
	fallbackLocale: "en", // 回退语言
	messages: {
		en,
		"zh-CN": zhCN,
	},
});

// 导出 i18n 实例
export default i18n;
