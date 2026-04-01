<template>
  <div 
    class="flex flex-col bg-white dark:bg-gray-800 border-l border-gray-200 dark:border-gray-700 shadow-xl z-40 transition-all duration-300"
    :class="[
      // Mobile: Fixed overlay
      'fixed right-0 top-0 h-full w-full sm:hidden transform',
      !visible ? 'translate-x-full' : 'translate-x-0',
      // Desktop: Sticky sidebar
      'sm:sticky sm:top-20 sm:h-[calc(100vh-6rem)] sm:w-80 sm:shrink-0 sm:transform-none',
      !visible && 'sm:hidden' // Hide on desktop if not visible to free space
    ]"
  >
    <div class="p-4 border-b border-gray-200 dark:border-gray-700 font-bold text-lg flex justify-between items-center mt-16 sm:mt-0">
      <span>笔记列表 ({{ notes.length }})</span>
      <a-button type="text" size="small" @click="$emit('close')">
        <icon-close />
      </a-button>
    </div>
    <div class="flex-1 overflow-y-auto p-4 space-y-4">
      <div v-if="notes.length === 0" class="text-center text-gray-400 py-10">
        暂无笔记，选中文字以添加。
      </div>
      <div
        v-for="note in notes"
        :key="note.id"
        :id="`note-item-${note.id}`"
        class="p-3 rounded border border-gray-200 dark:border-gray-700 hover:shadow-md transition-shadow relative group bg-gray-50 dark:bg-gray-900"
      >
        <div
            class="mb-2 text-sm text-gray-500 italic border-l-4 pl-2 cursor-pointer hover:bg-gray-100 dark:hover:bg-gray-800 p-1 rounded"
            :style="{ borderLeftColor: getColorHex(note.color) }"
            @click="$emit('scroll-to', note)"
        >
          "{{ note.selected_text }}"
        </div>
        <div class="mb-2">
          <a-textarea
            v-if="editingId === note.id"
            :id="`note-input-${note.id}`"
            v-model="editContent"
            auto-size
            @blur="saveEdit(note)"
            @keydown.enter.ctrl="saveEdit(note)"
            placeholder="输入笔记内容..."
            class="w-full"
          />
          <div
            v-else
            @click.stop="startEdit(note)"
            class="cursor-text min-h-[1.5em] text-gray-800 dark:text-gray-200 hover:bg-gray-100 dark:hover:bg-gray-800 p-1 rounded transition-colors text-sm whitespace-pre-wrap"
          >
             {{ note.content || '点击添加笔记...' }}
          </div>
        </div>
        <div class="flex justify-between items-center text-xs text-gray-400 mt-2">
          <span>{{ formatDate(note.updated_at) }}</span>
          <div class="flex items-center space-x-2">
            <button 
                class="hover:text-yellow-500 transition-colors" 
                :class="{'text-yellow-500': note.importance === 5}"
                @click.stop="toggleImportance(note)"
            >
              <icon-star-fill v-if="note.importance === 5" />
              <icon-star v-else />
            </button>
            <div class="opacity-0 group-hover:opacity-100 transition-opacity">
                <button class="hover:text-red-500 transition-colors" @click.stop="$emit('delete', note.id)">
                <icon-delete />
                </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import dayjs from "dayjs";
import { nextTick, ref, watch } from "vue";

const props = defineProps({
	notes: Array,
	visible: Boolean,
	activeNoteId: [String, Number],
});

watch(
	() => props.activeNoteId,
	(newId) => {
		if (newId) {
			nextTick(() => {
				const el = document.getElementById(`note-item-${newId}`);
				if (el) {
					el.scrollIntoView({ behavior: "smooth", block: "center" });
					// Flash effect
					el.classList.add("ring-2", "ring-blue-500");
					setTimeout(
						() => el.classList.remove("ring-2", "ring-blue-500"),
						1500,
					);
				}
			});
		}
	},
);

const emit = defineEmits(["close", "delete", "update", "scroll-to"]);

const editingId = ref(null);
const editContent = ref("");

const formatDate = (date) => dayjs(date).format("MM-DD HH:mm");

const toggleImportance = (note) => {
	const newImportance = note.importance === 5 ? 1 : 5;
	emit("update", note.id, { importance: newImportance });
};

const getColorHex = (colorName) => {
	const map = {
		yellow: "#FACC15",
		red: "#F87171",
		green: "#4ADE80",
		blue: "#60A5FA",
	};
	return map[colorName] || "#FACC15";
};

const startEdit = async (note) => {
	editingId.value = note.id;
	editContent.value = note.content || "";
	await nextTick();
	const el = document.getElementById(`note-input-${note.id}`);
	if (el) {
		// Find the textarea element inside the arco component wrapper if needed
		const textarea = el.querySelector("textarea") || el;
		textarea.focus();
	}
};

const saveEdit = (note) => {
	if (editingId.value === note.id) {
		// Only update if changed
		if (editContent.value !== note.content) {
			emit("update", note.id, { content: editContent.value });
		}
		editingId.value = null;
	}
};
</script>
