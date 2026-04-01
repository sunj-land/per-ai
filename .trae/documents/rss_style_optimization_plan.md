# RSS文章HTML样式优化实施计划

## 1. 概述
本计划旨在优化RSS文章的HTML内容展示，解决样式堆叠、排版混乱等问题。通过前后端双重清洗机制，确保内容的安全性与整洁度，并采用隔离的CSS样式策略实现统一美观的阅读体验。

## 2. 现状分析
- **后端 (`backend/app/services/rss_service.py`)**: 目前直接存储RSS源提供的原始内容，未进行任何清洗或处理。
- **前端 (`frontend/packages/web/src/pages/rss/ArticleDetail.vue`)**: 直接通过 `v-html` 渲染内容，缺乏样式隔离，容易受全局样式影响或破坏全局布局。
- **依赖**: 后端已包含 `beautifulsoup4`，前端可利用原生 `DOMParser`。

## 3. 实施步骤

### 阶段一：后端内容清洗 (Python)
**目标**: 在数据入库前进行预处理，从源头净化数据。

1.  **创建工具模块**: 在 `backend/app/core/html_utils.py` (新建) 中实现 `clean_html_content` 函数。
    -   使用 `BeautifulSoup` 解析 HTML。
    -   移除所有 `style`, `class`, `id` 属性。
    -   移除危险标签: `script`, `iframe`, `object`, `embed`, `form`, `input`, `button`。
    -   移除空标签 (保留 `img`, `br`, `hr`)。
2.  **集成到服务**: 修改 `backend/app/services/rss_service.py`。
    -   引入 `clean_html_content`。
    -   在 `fetch_and_parse_feed` 函数中，在创建 `RSSArticle` 对象前调用清洗函数处理 `content` 和 `summary`。

### 阶段二：前端内容清洗与增强 (Vue/JS)
**目标**: 确保展示时的安全性与样式一致性，提供二次防护。

1.  **实现清洗函数**: 在 `frontend/packages/web/src/pages/rss/ArticleDetail.vue` 中添加 `cleanHtml` 方法。
    -   使用 `DOMParser` 解析 HTML 字符串。
    -   执行与后端一致的清洗逻辑 (移除 `style`, `class`, `id`, 危险标签)。
    -   **增强功能**: 为所有 `<img>` 标签添加 `loading="lazy"` 属性。
2.  **应用清洗**: 修改 `renderedContent` 计算属性，先调用 `cleanHtml` 处理内容，再进行 Markdown 渲染 (如果需要) 或直接返回。

### 阶段三：CSS样式隔离与美化
**目标**: 建立独立的样式沙箱，提供优质阅读体验。

1.  **样式容器**: 在 `frontend/packages/web/src/pages/rss/ArticleDetail.vue` 的模板中，确保内容容器拥有 `.rss-content` 类名。
2.  **编写样式**: 在 `<style scoped>` (或使用 `::v-deep` / 全局样式文件) 中定义 `.rss-content` 的样式规则。
    -   **重置**: `all: unset; display: block;` (针对容器内元素)。
    -   **排版**:
        -   行高: `1.8`
        -   字体: `16px`
        -   段落间距: `15px`
        -   首行缩进: `2em` (针对中文 `<p>`)
    -   **标签美化**:
        -   `h1, h2, h3`: 统一字号、加粗、上下间距。
        -   `img`: `max-width: 100%; height: auto; display: block; margin: 0 auto; border-radius: 8px; box-shadow: ...`
        -   `ul, ol`: 标准缩进 (`padding-left: 2em`)。
        -   `a`: 统一链接颜色，下划线。
        -   `blockquote`: 引用块样式 (左边框、背景色)。
        -   `pre, code`: 代码块样式。
    -   **深色模式**: 使用 `.dark .rss-content` 选择器适配深色主题颜色。

## 4. 验证与测试
1.  **后端测试**:
    -   抓取一个新的 RSS 源，检查数据库中存储的 `content` 是否已去除 `style` 和 `class`。
2.  **前端测试**:
    -   打开文章详情页，检查控制台是否有脚本执行错误 (验证危险标签过滤)。
    -   检查页面样式是否整洁，无横向滚动条 (图片自适应)。
    -   切换深色模式，确认文章内容颜色适配。
    -   检查图片是否懒加载 (网络请求面板)。

## 5. 约束与注意事项
-   **零依赖**: 前端仅使用原生 API，后端复用现有 `beautifulsoup4`。
-   **兼容性**: CSS 使用标准属性，JS 使用 ES6+ 标准特性。
-   **安全性**: 严格过滤 `<script>` 和 `<iframe>` 等标签。
