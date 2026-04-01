<template>
  <div
    v-show="visible"
    class="fixed z-50 bg-white dark:bg-gray-800 shadow-lg rounded-lg border border-gray-200 dark:border-gray-700 flex items-center p-2 gap-3"
    :style="{ top: `${y}px`, left: `${x}px`, transform: 'translateY(-100%) marginTop(-10px)' }"
    @mousedown.stop
    @click.stop
  >
    <a-tooltip content="高亮 (Yellow)">
      <button class="w-8 h-8 rounded-full bg-yellow-200 hover:ring-2 ring-yellow-400 transition-all" @click="$emit('highlight', 'yellow')"></button>
    </a-tooltip>
    <a-tooltip content="高亮 (Red)">
      <button class="w-8 h-8 rounded-full bg-red-200 hover:ring-2 ring-red-400 transition-all" @click="$emit('highlight', 'red')"></button>
    </a-tooltip>
    <a-tooltip content="高亮 (Green)">
      <button class="w-8 h-8 rounded-full bg-green-200 hover:ring-2 ring-green-400 transition-all" @click="$emit('highlight', 'green')"></button>
    </a-tooltip>
    <a-tooltip content="高亮 (Blue)">
      <button class="w-8 h-8 rounded-full bg-blue-200 hover:ring-2 ring-blue-400 transition-all" @click="$emit('highlight', 'blue')"></button>
    </a-tooltip>
    <div class="w-px h-6 bg-gray-200 dark:bg-gray-700"></div>
    <a-tooltip content="添加笔记">
      <button class="w-8 h-8 flex items-center justify-center rounded-full hover:bg-gray-100 dark:hover:bg-gray-700 text-gray-600 dark:text-gray-300 transition-all" @click="$emit('add-note')">
        <icon-edit />
      </button>
    </a-tooltip>
    <a-tooltip content="复制">
      <button class="w-8 h-8 flex items-center justify-center rounded-full hover:bg-gray-100 dark:hover:bg-gray-700 text-gray-600 dark:text-gray-300 transition-all" @click="$emit('copy')">
        <icon-copy />
      </button>
    </a-tooltip>
  </div>
</template>

<script setup>
defineProps({
	visible: Boolean,
	x: Number,
	y: Number,
});

defineEmits(["highlight", "add-note", "copy"]);
</script>
