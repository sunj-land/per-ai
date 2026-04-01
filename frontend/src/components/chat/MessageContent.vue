<template>
  <div class="message-content-renderer">
    <!-- Thinking Process -->
    <ThinkingDisplay
      v-if="thinkingContent"
      :content="thinkingContent"
      :auto-collapse="thinkingComplete"
      :completed="thinkingComplete"
    />

    <!-- Main Content with Cards and Images -->
    <div class="main-content">
      <template v-for="(segment, index) in contentSegments" :key="index">
        <!-- Text Segment (Markdown) -->
        <div
          v-if="segment.type === 'text'"
          class="markdown-body"
          v-html="renderMarkdown(segment.content)"
        ></div>

        <!-- Image Segment -->
        <div v-else-if="segment.type === 'image'" class="image-wrapper">
          <a-image
            :src="segment.src"
            :alt="segment.alt"
            :title="segment.title"
            fit="contain"
            show-loader
            preview
          >
            <template #error>
              <div class="image-error">
                <icon-image-close />
                <span>Failed to load image</span>
              </div>
            </template>
          </a-image>
        </div>

        <!-- Legacy Card Segment (Value-based) -->
        <component
          v-else-if="segment.type === 'card'"
          :is="getCardComponent(segment.cardType)"
          :payload="segment.payload"
        />

        <!-- Async Card Segment (Reference-based) -->
        <AsyncCardRenderer
          v-else-if="segment.type === 'ref-card'"
          :id="segment.id"
          :params="segment.params"
        />
      </template>
    </div>
  </div>
</template>

<script setup>
import MarkdownIt from "markdown-it";
import {
	computed,
	defineAsyncComponent,
	onBeforeUnmount,
	ref,
	shallowRef,
	watch,
} from "vue";
import AsyncCardRenderer from "../cards/AsyncCardRenderer.vue";

// Initialize MarkdownIt
const md = new MarkdownIt({
	html: true,
	linkify: true,
	breaks: true,
	typographer: true,
});

const props = defineProps({
	content: {
		type: String,
		required: true,
	},
	speed: {
		type: Number,
		default: 30, // 30-60ms
	},
	loading: {
		type: Boolean,
		default: false,
	},
	error: {
		type: String,
		default: "",
	},
	animate: {
		type: Boolean,
		default: false, // Set to true for new messages to enable typewriter
	},
	thinkingComplete: {
		type: Boolean,
		default: false,
	},
});

const emit = defineEmits(["retry"]);

const displayedText = ref("");
const isTyping = ref(false);
const isPaused = ref(false);
let typingTimer = null;
let targetText = "";

// Dynamic Card Loading (Legacy)
const cardModules = import.meta.glob("../cards/*.vue");
const cardComponents = shallowRef({});

// Pre-register cards based on filename
for (const path in cardModules) {
	const fileName = path
		.split("/")
		.pop()
		.replace(/\.\w+$/, "");
	const name = fileName.toLowerCase();
	const simpleName = name.replace("card", "");

	cardComponents.value[fileName] = defineAsyncComponent(cardModules[path]);
	if (simpleName !== name) {
		cardComponents.value[simpleName] = cardComponents.value[fileName];
	}
}

const getCardComponent = (type) => {
	const key = type.toLowerCase();
	return cardComponents.value[key] || cardComponents.value[type] || null;
};

// 净化并提取 JSON 内容
const extractContent = (raw) => {
	if (!raw) return "";
	let text = raw;
	try {
		// 如果是 JSON 格式，尝试提取核心字段
		const parsed = JSON.parse(raw);
		text = parsed.content || parsed.text || parsed.message || raw;
	} catch (_e) {
		// 非 JSON，直接使用
	}
	return text;
};

const typeNextChar = () => {
	if (isPaused.value) return;

	// Recalculate lag based on current state
	const lag = targetText.length - displayedText.value.length;

	if (lag <= 0) {
		isTyping.value = false;
		return;
	}

	isTyping.value = true;

	// Adaptive Speed Control
	// Base speed: props.speed (default 30ms)
	let delay = props.speed;
	let charsToRender = 1;

	// Dynamic Speed Adjustment based on Lag
	if (lag > 200) {
		// Very high lag: Burst mode
		delay = 5;
		charsToRender = Math.min(lag, 10); // Render up to 10 chars at once
	} else if (lag > 100) {
		// High lag: Fast catchup
		delay = 10;
		charsToRender = 5;
	} else if (lag > 50) {
		// Moderate lag: Speed up
		delay = 15;
		charsToRender = 2;
	} else if (lag > 20) {
		// Slight lag: Slightly faster
		delay = 20;
		charsToRender = 1;
	} else {
		// Normal/Sync mode: Smooth typing
		// Add random jitter for natural feel
		delay = props.speed + Math.random() * 10;
		charsToRender = 1;
	}

	const nextChunk = targetText.substr(
		displayedText.value.length,
		charsToRender,
	);
	displayedText.value += nextChunk;

	typingTimer = setTimeout(typeNextChar, delay);
};

watch(
	() => props.content,
	(newVal) => {
		targetText = extractContent(newVal);

		if (!props.animate) {
			// 非动画模式，直接全量显示
			displayedText.value = targetText;
			return;
		}

		if (
			!isTyping.value &&
			!isPaused.value &&
			displayedText.value.length < targetText.length
		) {
			typeNextChar();
		}
	},
	{ immediate: true },
);

// 暴露控制方法
const pause = () => {
	isPaused.value = true;
	if (typingTimer) clearTimeout(typingTimer);
};

const resume = () => {
	isPaused.value = false;
	typeNextChar();
};

const interrupt = () => {
	if (typingTimer) clearTimeout(typingTimer);
	isTyping.value = false;
	displayedText.value = targetText; // 立即显示全部已接收内容
};

defineExpose({
	pause,
	resume,
	interrupt,
	isTyping,
	isPaused,
});

onBeforeUnmount(() => {
	if (typingTimer) clearTimeout(typingTimer);
});

const thinkingContent = computed(() => {
	const match = displayedText.value.match(/<think>([\s\S]*?)(?:<\/think>|$)/);
	return match ? match[1] : null;
});

const mainContent = computed(() => {
	return displayedText.value
		.replace(/<think>[\s\S]*?(?:<\/think>|$)/, "")
		.trim();
});

const contentSegments = computed(() => {
	const text = mainContent.value;
	if (!text) return [];

	// Regex definitions
	const cardRegex = /\[\[card:(\w+)\|(.*?)\]\]/s;
	const refCardRegex = /\{\{card:([^}]+)\}\}/;
	const imgRegex = /!\[([^\]]*)\]\(([^)\s]+)(?:\s+"([^"]+)")?\)/;

	const segments = [];
	let remaining = text;

	while (remaining) {
		const cardMatch = cardRegex.exec(remaining);
		const refCardMatch = refCardRegex.exec(remaining);
		const imgMatch = imgRegex.exec(remaining);

		// Find earliest match
		const matches = [
			{
				match: cardMatch,
				type: "card",
				index: cardMatch ? cardMatch.index : Infinity,
			},
			{
				match: refCardMatch,
				type: "ref-card",
				index: refCardMatch ? refCardMatch.index : Infinity,
			},
			{
				match: imgMatch,
				type: "image",
				index: imgMatch ? imgMatch.index : Infinity,
			},
		].filter((m) => m.match);

		if (matches.length === 0) {
			segments.push({ type: "text", content: remaining });
			break;
		}

		// Sort by index
		matches.sort((a, b) => a.index - b.index);
		const best = matches[0];
		const match = best.match;

		// Add text before match
		if (best.index > 0) {
			segments.push({
				type: "text",
				content: remaining.slice(0, best.index),
			});
		}

		// Add match content
		if (best.type === "card") {
			try {
				const payload = JSON.parse(match[2]);
				segments.push({
					type: "card",
					cardType: match[1],
					payload,
				});
			} catch (e) {
				console.error("Failed to parse card payload", e);
				segments.push({ type: "text", content: match[0] });
			}
		} else if (best.type === "ref-card") {
			segments.push({
				type: "ref-card",
				id: match[1],
				params: {}, // Future: support {{card:ID|params}} parsing if needed
			});
		} else if (best.type === "image") {
			segments.push({
				type: "image",
				alt: match[1],
				src: match[2],
				title: match[3] || "",
			});
		}

		remaining = remaining.slice(best.index + match[0].length);
	}

	return segments;
});

const renderMarkdown = (text) => {
	return md.render(text);
};
</script>

<style scoped>
.message-content-renderer {
  width: 100%;
}
.markdown-body {
  font-size: 14px;
  line-height: 1.6;
  color: var(--color-text-1);
}
.markdown-body :deep(p) {
  margin-bottom: 1em;
}
.markdown-body :deep(p:last-child) {
  margin-bottom: 0;
}
.markdown-body :deep(pre) {
  background-color: var(--color-fill-2);
  padding: 12px;
  border-radius: 4px;
  overflow-x: auto;
}
.markdown-body :deep(code) {
  font-family: monospace;
  background-color: var(--color-fill-2);
  padding: 2px 4px;
  border-radius: 4px;
}
.markdown-body :deep(pre code) {
  padding: 0;
  background-color: transparent;
}
.markdown-body :deep(ul), .markdown-body :deep(ol) {
  padding-left: 20px;
  margin-bottom: 1em;
}
.markdown-body :deep(a) {
  color: rgb(var(--primary-6));
  text-decoration: none;
}
.markdown-body :deep(a:hover) {
  text-decoration: underline;
}
.markdown-body :deep(table) {
  border-collapse: collapse;
  width: 100%;
  margin-bottom: 1em;
}
.markdown-body :deep(th), .markdown-body :deep(td) {
  border: 1px solid var(--color-border-2);
  padding: 6px 12px;
}
.image-wrapper {
  margin: 12px 0;
}
.image-error {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 20px;
  background: var(--color-fill-2);
  color: var(--color-text-3);
  border-radius: 4px;
}
</style>
