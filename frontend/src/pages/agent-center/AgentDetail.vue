<template>
      <div class="agent-detail h-full flex flex-col relative">
    <div v-if="loading" class="flex justify-center items-center h-full">
      <a-spin dot />
    </div>
    <div v-else-if="error" class="text-center text-red-500 py-10">
      {{ error }}
    </div>
    <div v-else class="flex-1 overflow-hidden bg-gray-50 dark:bg-gray-900 rounded-lg relative">
       <!-- Toolbar -->
       <div class="absolute top-4 right-4 z-10 flex gap-2">
         <a-button size="mini" @click="exportSVG">
            SVG
         </a-button>
         <a-button size="mini" @click="exportPNG">
            PNG
         </a-button>
         <a-button size="mini" @click="resetView">
            <template #icon><icon-sync /></template>
         </a-button>
         <a-button size="mini" @click="zoomIn">
            <template #icon><icon-plus /></template>
         </a-button>
         <a-button size="mini" @click="zoomOut">
            <template #icon><icon-minus /></template>
         </a-button>
       </div>

       <!-- Canvas -->
       <div
         class="w-full h-full cursor-grab active:cursor-grabbing overflow-hidden"
         @mousedown="startDrag"
         @mousemove="onDrag"
         @mouseup="stopDrag"
         @mouseleave="stopDrag"
         @wheel.prevent="onWheel"
       >
          <div
            ref="mermaidContainer"
            class="mermaid-container origin-center transition-transform duration-75"
            :style="transformStyle"
          >
            <!-- Mermaid content will be injected here -->
          </div>
       </div>
    </div>
  </div>
</template>

<script setup>
import mermaid from "mermaid";
import { computed, nextTick, onMounted, ref, watch } from "vue";
import { getAgentGraph } from "@/api/agent-center";

const props = defineProps({
	agentId: {
		type: String,
		required: true,
	},
});

const mermaidGraph = ref("");
const loading = ref(true);
const error = ref(null);
const mermaidContainer = ref(null);

// Pan/Zoom State
const scale = ref(1);
const translateX = ref(0);
const translateY = ref(0);
const isDragging = ref(false);
const startX = ref(0);
const startY = ref(0);

const _transformStyle = computed(() => ({
	transform: `translate(${translateX.value}px, ${translateY.value}px) scale(${scale.value})`,
}));

// Initialize Mermaid
onMounted(() => {
	mermaid.initialize({
		startOnLoad: false,
		theme: "default",
		securityLevel: "loose",
	});
});

const loadGraph = async () => {
	if (!props.agentId) return;
	loading.value = true;
	error.value = null;
	try {
		const res = await getAgentGraph(props.agentId);
		if (res?.mermaid) {
			mermaidGraph.value = res.mermaid;
			await nextTick();
			await renderGraph();
		} else {
			error.value = "No graph data available";
		}
	} catch (err) {
		console.error(err);
		error.value = "Failed to load agent graph";
	} finally {
		loading.value = false;
	}
};

const renderGraph = async () => {
	if (!mermaidGraph.value || !mermaidContainer.value) return;

	try {
		const id = `mermaid-${Date.now()}`;
		const { svg } = await mermaid.render(id, mermaidGraph.value);
		mermaidContainer.value.innerHTML = svg;

		// Reset view to center
		resetView();
	} catch (err) {
		console.error("Mermaid render error:", err);
		error.value = `Failed to render graph: ${err.message}`;
	}
};

const resetView = () => {
	scale.value = 1;
	translateX.value = 0;
	translateY.value = 0;
};

const _zoomIn = () => {
	scale.value = Math.min(scale.value * 1.2, 5);
};

const _zoomOut = () => {
	scale.value = Math.max(scale.value / 1.2, 0.1);
};

const _startDrag = (e) => {
	isDragging.value = true;
	startX.value = e.clientX - translateX.value;
	startY.value = e.clientY - translateY.value;
};

const _onDrag = (e) => {
	if (!isDragging.value) return;
	translateX.value = e.clientX - startX.value;
	translateY.value = e.clientY - startY.value;
};

const _stopDrag = () => {
	isDragging.value = false;
};

const _onWheel = (e) => {
	const delta = e.deltaY > 0 ? 0.9 : 1.1;
	const newScale = Math.min(Math.max(scale.value * delta, 0.1), 5);
	scale.value = newScale;
};

const _exportSVG = () => {
	if (!mermaidContainer.value) return;
	const svg = mermaidContainer.value.querySelector("svg");
	if (!svg) return;

	const svgData = new XMLSerializer().serializeToString(svg);
	const blob = new Blob([svgData], { type: "image/svg+xml;charset=utf-8" });
	const url = URL.createObjectURL(blob);

	const link = document.createElement("a");
	link.href = url;
	link.download = `agent-${props.agentId}.svg`;
	document.body.appendChild(link);
	link.click();
	document.body.removeChild(link);
};

const _exportPNG = () => {
	if (!mermaidContainer.value) return;
	const svg = mermaidContainer.value.querySelector("svg");
	if (!svg) return;

	const canvas = document.createElement("canvas");
	const ctx = canvas.getContext("2d");
	const svgData = new XMLSerializer().serializeToString(svg);
	const img = new Image();

	// Get SVG dimensions
	const bbox = svg.getBoundingClientRect();
	canvas.width = bbox.width * 2; // Higher resolution
	canvas.height = bbox.height * 2;

	img.onload = () => {
		ctx.scale(2, 2);
		ctx.drawImage(img, 0, 0);
		const pngUrl = canvas.toDataURL("image/png");

		const link = document.createElement("a");
		link.href = pngUrl;
		link.download = `agent-${props.agentId}.png`;
		document.body.appendChild(link);
		link.click();
		document.body.removeChild(link);
	};

	img.src = `data:image/svg+xml;base64,${btoa(unescape(encodeURIComponent(svgData)))}`;
};

watch(
	() => props.agentId,
	() => {
		loadGraph();
	},
);

onMounted(() => {
	loadGraph();
});
</script>

<style scoped>
.mermaid {
  min-height: 300px;
  display: flex;
  justify-content: center;
  align-items: center;
}
</style>
