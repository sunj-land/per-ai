<template>
  <div class="h-full w-full overflow-y-auto" @click="handleGlobalClick">
    <div class="p-4 sm:p-6 max-w-7xl mx-auto flex gap-6 relative">
      <!-- Main Content -->
      <div class="flex-1 min-w-0">
        <a-page-header :title="article ? article.title : '文章详情'" @back="$router.back()" class="px-0 mb-4">
        <template #extra>
            <a-space v-if="article">
            <a-button @click="showNoteList = !showNoteList" :type="showNoteList ? 'primary' : 'secondary'">
                <template #icon><icon-edit /></template>
                笔记 ({{ noteStore.notes.length }})
            </a-button>
            <a-button @click="handleExport('md')">
                <template #icon><icon-download /></template>
                导出 MD
            </a-button>
            <a-button @click="handleExport('json')">
                <template #icon><icon-code /></template>
                导出 JSON
            </a-button>
            <a-button type="primary" :href="article.link" target="_blank">
                <template #icon><icon-launch /></template>
                查看原文
            </a-button>
            <a-button @click="openSendModal" type="primary" status="success">
                <template #icon><icon-send /></template>
                发送消息
            </a-button>
            </a-space>
        </template>
        </a-page-header>

        <div v-if="loading" class="py-20 text-center">
            <a-spin dot size="large" />
        </div>

        <div v-else-if="article" class="space-y-6">
            <!-- Article Card -->
            <a-card class="shadow-sm rounded-lg article-card relative">
                <div class="flex flex-wrap items-center gap-4 text-gray-500 mb-8 pb-4 border-b border-gray-100">
                    <div class="flex items-center">
                    <icon-calendar class="mr-1.5" />
                    <span>{{ formatDate(article.published_at) }}</span>
                    </div>
                    <div class="flex items-center">
                    <icon-book class="mr-1.5" />
                    <span>{{ article.feed_title }}</span>
                    </div>
                    <div class="flex items-center" v-if="article.author">
                    <icon-user class="mr-1.5" />
                    <span>{{ article.author }}</span>
                    </div>
                </div>

                <!-- Content Renderer -->
                <div
                    ref="contentRef"
                    class="article-content rss-content relative"
                    :class="{ 'markdown-body': isMarkdownContent, 'prose': !isMarkdownContent }"
                    v-html="renderedContent"
                    @mouseup="handleSelection"
                ></div>
            </a-card>

            <!-- Summary Editor -->
            <div class="bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-100 dark:border-gray-700 mt-8 overflow-hidden transition-all duration-300 hover:shadow-md">
                <div class="px-6 py-4 border-b border-gray-100 dark:border-gray-700 flex items-center justify-between bg-gray-50/50 dark:bg-gray-800/50">
                    <div class="flex items-center gap-3">
                        <div class="w-8 h-8 rounded-full bg-blue-50 dark:bg-blue-900/30 flex items-center justify-center text-blue-500">
                            <icon-edit class="text-lg" />
                        </div>
                        <div>
                            <h3 class="font-bold text-base m-0 text-gray-800 dark:text-gray-200">文章总结与思考</h3>
                            <p class="text-xs text-gray-500 m-0 mt-0.5">支持 Markdown 语法，自动保存</p>
                        </div>
                    </div>
                    <a-popconfirm content="确定要清空总结内容吗？这会同时删除向量数据。" @ok="handleDeleteSummary" position="tr">
                        <a-button v-if="noteStore.summary" type="text" status="danger" class="hover:bg-red-50 dark:hover:bg-red-900/30 rounded-md">
                            <template #icon><icon-delete /></template>
                            清空
                        </a-button>
                    </a-popconfirm>
                </div>
                <SummaryEditor
                    :initial-content="summaryContent"
                    :saving="savingSummary"
                    @update:content="handleContentUpdate"
                    @save="handleSaveSummary"
                    class="min-h-[320px]"
                />
            </div>
        </div>

        <a-empty v-else description="文章未找到" class="py-20" />
    </div>

    <!-- Note List Sidebar -->
    <NoteList
              :notes="noteStore.notes"
              :visible="showNoteList"
              :active-note-id="activeNoteId"
              @close="showNoteList = false"
              @delete="handleDeleteNote"
              @update="handleUpdateNote"
              @scroll-to="scrollToHighlight"
            />

    <!-- Toolbar -->
    <NoteToolbar
        :visible="toolbarVisible"
        :x="toolbarX"
        :y="toolbarY"
        @highlight="addHighlight"
        @add-note="addNote"
        @copy="copySelection"
    />

    <!-- Send to Channel Modal -->
    <ChannelSelectorModal
      v-model="sendModalVisible"
      :initial-title="article ? article.title : ''"
      :initial-content="sendModalContent"
    />
    </div>
  </div>
</template>

<script setup>
import dayjs from "dayjs";
import MarkdownIt from "markdown-it";
import { computed, nextTick, onMounted, ref } from "vue";
import { useRoute, useRouter } from "vue-router";
import { getArticle } from "../../api/rss";
import { useNoteStore } from "../../store/note";
import "github-markdown-css/github-markdown.css";
import { Message } from "@arco-design/web-vue";

// Import components
import NoteList from "@/components/note/NoteList.vue";
import NoteToolbar from "@/components/note/NoteToolbar.vue";
import SummaryEditor from "@/components/note/SummaryEditor.vue";
import ChannelSelectorModal from "@/components/channel/ChannelSelectorModal.vue";

const route = useRoute();
const router = useRouter();
const noteStore = useNoteStore();
const article = ref(null);
const loading = ref(false);
const contentRef = ref(null);
const showNoteList = ref(false);
const activeNoteId = ref(null);
const savingSummary = ref(false);
const summaryContent = ref("");
const draftKey = computed(() => `summary_draft_${article.value?.id}`);

// Send Message State
const sendModalVisible = ref(false);
const sendModalContent = computed(() => {
	if (!article.value) return "";
	return `[${article.value.title}](${article.value.link})\n\n${article.value.summary || ""}`;
});
const openSendModal = () => {
	sendModalVisible.value = true;
};

// Toolbar State
const toolbarVisible = ref(false);
const toolbarX = ref(0);
const toolbarY = ref(0);
const currentSelection = ref(null);

const md = new MarkdownIt({ html: true, linkify: true, typographer: true });

const formatDate = (date) => dayjs(date).format("YYYY-MM-DD HH:mm");

const isMarkdownContent = computed(() => {
	if (!article.value) return false;
	const content = article.value.content || article.value.summary || "";
	return !/^\s*</.test(content);
});

const cleanHtml = (html) => {
	if (!html) return "";
	try {
		const parser = new DOMParser();
		// Check if html contains proper tags, otherwise it might just be text
		if (!/<[a-z][\s\S]*>/i.test(html)) {
			return html;
		}

		const doc = parser.parseFromString(html, "text/html");

		// 1. Remove dangerous tags
		const dangerousTags = [
			"script",
			"iframe",
			"object",
			"embed",
			"form",
			"input",
			"button",
			"link",
			"style",
			"meta",
			"head",
			"title",
		];
		dangerousTags.forEach((tag) => {
			const elements = doc.querySelectorAll(tag);
			elements.forEach((el) => {
				el.remove();
			});
		});

		// 2. Remove attributes (style, class, id, etc.)
		const allElements = doc.querySelectorAll("*");
		allElements.forEach((el) => {
			el.removeAttribute("style");
			el.removeAttribute("class");
			el.removeAttribute("id");
			el.removeAttribute("width");
			el.removeAttribute("height");

			// Remove event handlers
			Array.from(el.attributes).forEach((attr) => {
				if (attr.name.startsWith("on")) {
					el.removeAttribute(attr.name);
				}
			});

			// 3. Image optimization (Lazy load)
			if (el.tagName === "IMG") {
				el.setAttribute("loading", "lazy");
			}

			// Link optimization (Security)
			if (el.tagName === "A") {
				el.setAttribute("target", "_blank");
				el.setAttribute("rel", "noopener noreferrer");
			}
		});

		return doc.body.innerHTML;
	} catch (e) {
		console.error("HTML cleaning failed:", e);
		return html;
	}
};

const renderedContent = computed(() => {
	if (!article.value) return "";
	const content = article.value.content || article.value.summary || "";
	if (isMarkdownContent.value) {
		return md.render(content);
	}
	return cleanHtml(content);
});

// Load Data
onMounted(async () => {
	const id = route.params.id || route.query.id;
	if (id) {
		loading.value = true;
		try {
			article.value = await getArticle(id);
			await noteStore.fetchNotes(id);
			await noteStore.fetchSummary(id);

			// Load draft or remote
			const draft = localStorage.getItem(`summary_draft_${id}`);
			if (
				draft &&
				(!noteStore.summary || draft !== noteStore.summary.content)
			) {
				// If draft exists and is different from remote, use draft but notify
				summaryContent.value = draft;
				if (noteStore.summary) {
					Message.info("已恢复未保存的草稿");
				}
			} else {
				summaryContent.value = noteStore.summary?.content || "";
			}

			// Wait for v-html to render then apply highlights
			await nextTick();
			setTimeout(renderHighlights, 100); // Slight delay for robust rendering
		} catch (err) {
			console.error(err);
			Message.error("加载文章失败");
		} finally {
			loading.value = false;
		}
	}
});

const handleExport = (type) => {
	if (!article.value) return;

	let contentToExport = "";
	let filename = "";
	let mimeType = "";

	if (type === "md") {
		const title = article.value.title || "Untitled";
		const link = article.value.link || "";
		const author = article.value.author || "Unknown";
		const date = article.value.published_at
			? formatDate(article.value.published_at)
			: "";

		let mdContent = `# ${title}\n\n`;
		mdContent += `> Author: ${author} | Date: ${date} | [Original Link](${link})\n\n`;
		mdContent += article.value.content || article.value.summary || "";

		if (noteStore.summary?.content) {
			mdContent += `\n\n## 总结\n\n${noteStore.summary.content}`;
		}
		
		if (noteStore.notes.length > 0) {
			mdContent += `\n\n## 笔记\n\n`;
			noteStore.notes.forEach((note) => {
				mdContent += `- **${note.selected_text}**: ${note.content || ""}\n`;
			});
		}

		contentToExport = mdContent;
		// sanitize filename
		filename = `${title.replace(/[\\/:*?"<>|]/g, "_")}.md`;
		mimeType = "text/markdown;charset=utf-8;";
	} else if (type === "json") {
		const exportData = {
			...article.value,
			summary: noteStore.summary,
			notes: noteStore.notes,
		};
		contentToExport = JSON.stringify(exportData, null, 2);
		const title = article.value.title || "export";
		filename = `${title.replace(/[\\/:*?"<>|]/g, "_")}.json`;
		mimeType = "application/json;charset=utf-8;";
	}

	const blob = new Blob([contentToExport], { type: mimeType });
	const downloadLink = document.createElement("a");
	downloadLink.href = URL.createObjectURL(blob);
	downloadLink.download = filename;
	document.body.appendChild(downloadLink);
	downloadLink.click();
	document.body.removeChild(downloadLink);
	URL.revokeObjectURL(downloadLink.href);

	Message.success(`成功导出 ${type.toUpperCase()} 文件`);
};

// Handle Selection
const handleSelection = () => {
	const selection = window.getSelection();
	if (
		!selection.isCollapsed &&
		contentRef.value &&
		contentRef.value.contains(selection.anchorNode)
	) {
		const range = selection.getRangeAt(0);
		const rect = range.getBoundingClientRect();

		// Position toolbar above selection
		toolbarX.value = rect.left + rect.width / 2 - 100;
		if (toolbarX.value < 10) toolbarX.value = 10;

		toolbarY.value = rect.top + window.scrollY - 10;

		currentSelection.value = {
			text: selection.toString(),
			range: range.cloneRange(),
		};
		toolbarVisible.value = true;
	}
};

const handleGlobalClick = (e) => {
	// Hide toolbar if clicking outside
	if (
		toolbarVisible.value &&
		!e.target.closest(".article-content") &&
		!e.target.closest(".fixed")
	) {
		toolbarVisible.value = false;
		window.getSelection().removeAllRanges();
	}
};

// Add Highlight
const addHighlight = async (color) => {
	if (!currentSelection.value) return;

	const { text, range } = currentSelection.value;

	// Calculate offset
	const container = contentRef.value;
	const preSelectionRange = range.cloneRange();
	preSelectionRange.selectNodeContents(container);
	preSelectionRange.setEnd(range.startContainer, range.startOffset);
	const start = preSelectionRange.toString().length;
	const end = start + text.length;

	// Create temporary note with optimistic UI
	const tempId = `temp_${Date.now()}`;
	applyHighlightToRange(range, color, tempId);

	// Reset selection immediately
	window.getSelection().removeAllRanges();
	toolbarVisible.value = false;

	try {
		const note = await noteStore.addNote({
			article_id: article.value.id,
			selected_text: text,
			start_offset: start,
			end_offset: end,
			color: color,
		});

		// Update temporary highlight with real ID
		const span = contentRef.value.querySelector(
			`span[data-note-id="${tempId}"]`,
		);
		if (span) {
			span.dataset.noteId = note.id;
			span.onclick = (e) => {
				e.stopPropagation();
				scrollToNote(note.id);
			};
		}
		Message.success("标记成功");
	} catch (_err) {
		// Revert optimistic UI
		unwrapHighlight(tempId);
		Message.error("标记失败");
	}
};

const addNote = () => {
	addHighlight("yellow");
	showNoteList.value = true;
};

const copySelection = () => {
	if (currentSelection.value) {
		navigator.clipboard.writeText(currentSelection.value.text);
		Message.success("已复制");
		toolbarVisible.value = false;
	}
};

// Render Highlights
const renderHighlights = () => {
	if (!contentRef.value) return;

	const sortedNotes = [...noteStore.notes].sort(
		(a, b) => a.start_offset - b.start_offset,
	);

	sortedNotes.forEach((note) => {
		try {
			const range = restoreRange(
				contentRef.value,
				note.start_offset,
				note.end_offset,
			);
			if (range) {
				applyHighlightToRange(range, note.color, note.id);
			}
		} catch (e) {
			console.warn("Failed to restore highlight", note, e);
		}
	});
};

// DOM Helpers
const applyHighlightToRange = (range, color, id) => {
	const span = document.createElement("span");
	span.className = `highlight-${color} rounded px-0.5 transition-colors cursor-pointer border-b-2 border-${color}-400`;
	// Add inline styles for Tailwind classes if not compiled dynamically
	const colors = {
		yellow:
			"background-color: rgba(253, 224, 71, 0.3); border-color: rgba(250, 204, 21, 1);",
		red: "background-color: rgba(252, 165, 165, 0.3); border-color: rgba(248, 113, 113, 1);",
		green:
			"background-color: rgba(134, 239, 172, 0.3); border-color: rgba(74, 222, 128, 1);",
		blue: "background-color: rgba(147, 197, 253, 0.3); border-color: rgba(96, 165, 250, 1);",
	};
	span.style.cssText = colors[color];

	span.dataset.noteId = id;
	span.onclick = (e) => {
		e.stopPropagation();
		scrollToNote(id);
	};

	try {
		range.surroundContents(span);
	} catch (e) {
		console.warn("Complex range selection fallback", e);
		span.appendChild(range.extractContents());
		range.insertNode(span);
	}
};

const restoreRange = (container, start, end) => {
	let charCount = 0;
	const range = document.createRange();
	range.setStart(container, 0);
	range.collapse(true);

	let foundStart = false;
	let foundEnd = false;

	const nodeStack = [container];
	let node;

	while (nodeStack.length > 0) {
		node = nodeStack.pop();
		if (!node) {
			break;
		}
		if (node.nodeType === 3) {
			const nextCharCount = charCount + node.length;
			if (!foundStart && start >= charCount && start <= nextCharCount) {
				range.setStart(node, start - charCount);
				foundStart = true;
			}
			if (foundStart && end >= charCount && end <= nextCharCount) {
				range.setEnd(node, end - charCount);
				foundEnd = true;
				break;
			}
			charCount = nextCharCount;
		} else {
			let i = node.childNodes.length;
			while (i--) {
				nodeStack.push(node.childNodes[i]);
			}
		}
	}

	return foundStart && foundEnd ? range : null;
};

// Interactions
const scrollToNote = (id) => {
	showNoteList.value = true;
	activeNoteId.value = id;
	// Reset after delay so we can re-trigger
	setTimeout(() => (activeNoteId.value = null), 2000);
};

const scrollToHighlight = (note) => {
	const span = contentRef.value.querySelector(
		`span[data-note-id="${note.id}"]`,
	);
	if (span) {
		span.scrollIntoView({ behavior: "smooth", block: "center" });
		// Flash effect
		const originalStyle = span.style.cssText;
		span.style.boxShadow = "0 0 0 4px rgba(59, 130, 246, 0.5)";
		setTimeout(() => {
			span.style.cssText = originalStyle;
		}, 1000);
	} else {
		Message.warning("原文位置未找到");
	}
};

const unwrapHighlight = (id) => {
	const span = contentRef.value.querySelector(`span[data-note-id="${id}"]`);
	if (span) {
		const parent = span.parentNode;
		while (span.firstChild) parent.insertBefore(span.firstChild, span);
		parent.removeChild(span);
	}
};

const handleDeleteNote = async (id) => {
	try {
		await noteStore.removeNote(id);
		unwrapHighlight(id);
		Message.success("删除成功");
	} catch (_err) {
		Message.error("删除失败");
	}
};

const handleUpdateNote = async (id, data) => {
	try {
		await noteStore.updateNote(id, data);
		Message.success("更新成功");
	} catch (_err) {
		Message.error("更新失败");
	}
};

const handleContentUpdate = (content) => {
	summaryContent.value = content;
	localStorage.setItem(draftKey.value, content);
};

const handleSaveSummary = async (content) => {
	savingSummary.value = true;
	try {
		await noteStore.saveSummary({
			article_id: article.value.id,
			content: content,
			is_draft: false,
		});
		localStorage.removeItem(draftKey.value);
	} catch (_err) {
		Message.error("保存总结失败");
	} finally {
		savingSummary.value = false;
	}
};

const handleDeleteSummary = async () => {
	if (!noteStore.summary) return;
	try {
		await noteStore.removeSummary(noteStore.summary.id);
		summaryContent.value = "";
		localStorage.removeItem(draftKey.value);
		Message.success("总结已删除");
	} catch (_err) {
		Message.error("删除总结失败");
	}
};
</script>

<style scoped>
/* RSS Content Style Isolation & Beautification */
.rss-content {
    /* Container styles */
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, "Noto Sans", sans-serif, "Apple Color Emoji", "Segoe UI Emoji", "Segoe UI Symbol", "Noto Color Emoji";
    line-height: 1.8;
    font-size: 16px;
    color: var(--color-text-1);
    word-wrap: break-word;
    overflow-wrap: break-word;
}

/* Reset all children */
:deep(.rss-content) * {
    all: revert;
    box-sizing: border-box;
}

/* Typography & Layout */
:deep(.rss-content) p {
    margin-bottom: 1.2em;
    line-height: 1.8;
    text-align: justify;
}

/* Chinese indent for paragraphs (optional, based on preference, user requested it) */
:deep(.rss-content) p {
    text-indent: 2em;
}

:deep(.rss-content) h1,
:deep(.rss-content) h2,
:deep(.rss-content) h3,
:deep(.rss-content) h4,
:deep(.rss-content) h5,
:deep(.rss-content) h6 {
    font-weight: 600;
    line-height: 1.4;
    margin-top: 1.5em;
    margin-bottom: 0.8em;
    color: var(--color-text-1);
}

:deep(.rss-content) h1 { font-size: 1.8em; border-bottom: 1px solid var(--color-border-2); padding-bottom: 0.3em; }
:deep(.rss-content) h2 { font-size: 1.5em; border-bottom: 1px solid var(--color-border-1); padding-bottom: 0.3em; }
:deep(.rss-content) h3 { font-size: 1.25em; }
:deep(.rss-content) h4 { font-size: 1.1em; }

:deep(.rss-content) img,
:deep(.rss-content) video,
:deep(.rss-content) iframe {
    max-width: 100%;
    max-height: 500px;
    object-fit: contain;
    height: auto;
    display: block;
    margin: 1.5em auto;
    border-radius: 8px;
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.08);
}

:deep(.rss-content) ul,
:deep(.rss-content) ol {
    padding-left: 2em;
    margin-bottom: 1.2em;
}

:deep(.rss-content) li {
    margin-bottom: 0.5em;
    line-height: 1.6;
}

:deep(.rss-content) a {
    color: rgb(var(--primary-6));
    text-decoration: none;
    border-bottom: 1px solid transparent;
    transition: all 0.2s;
}

:deep(.rss-content) a:hover {
    border-bottom-color: rgb(var(--primary-6));
}

:deep(.rss-content) blockquote {
    margin: 1.5em 0;
    padding: 1em 1.2em;
    background-color: var(--color-fill-2);
    border-left: 4px solid rgb(var(--primary-6));
    border-radius: 4px;
    color: var(--color-text-2);
}

:deep(.rss-content) blockquote p {
    text-indent: 0; /* Reset indent for quotes */
    margin-bottom: 0.5em;
}

:deep(.rss-content) blockquote p:last-child {
    margin-bottom: 0;
}

:deep(.rss-content) pre {
    background-color: var(--color-fill-2);
    padding: 1.2em;
    border-radius: 8px;
    overflow-x: auto;
    font-family: ui-monospace, SFMono-Regular, SF Mono, Menlo, Consolas, Liberation Mono, monospace;
    font-size: 0.9em;
    margin: 1.5em 0;
    border: 1px solid var(--color-border-2);
}

:deep(.rss-content) code {
    font-family: ui-monospace, SFMono-Regular, SF Mono, Menlo, Consolas, Liberation Mono, monospace;
    font-size: 0.9em;
    background-color: var(--color-fill-2);
    padding: 0.2em 0.4em;
    border-radius: 4px;
    color: rgb(var(--danger-6));
}

:deep(.rss-content) pre code {
    background-color: transparent;
    padding: 0;
    color: inherit;
    font-size: inherit;
}

:deep(.rss-content) table {
    width: 100%;
    border-collapse: collapse;
    margin: 1.5em 0;
    font-size: 0.9em;
}

:deep(.rss-content) th,
:deep(.rss-content) td {
    border: 1px solid var(--color-border-2);
    padding: 0.8em;
    text-align: left;
}

:deep(.rss-content) th {
    background-color: var(--color-fill-2);
    font-weight: 600;
}

/* Dark Mode Adaptation (using Arco Design CSS variables automatically) */
/* Specific overrides for dark mode if needed */
:deep(.dark .rss-content) img {
    opacity: 0.9;
}
</style>
