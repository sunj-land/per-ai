/*
 * @Author: 项目规范
 * @Date: 2024-03-25
 * @Description: 待办提醒卡片，轻量级待办事项管理，支持快速添加、拖拽排序
 */
<template>
  <a-card class="todo-card" :bordered="false">
    <template #title>
      <div class="card-header drag-handle">
        <icon-drag-dot-vertical class="drag-icon" />
        <span>待办清单</span>
      </div>
    </template>

    <div class="todo-content">
      <!-- 快速添加输入框 -->
      <div class="todo-input-wrap">
        <a-input
          v-model="newTodo"
          placeholder="添加新待办，回车保存..."
          @press-enter="addTodo"
        >
          <template #append>
            <a-button type="primary" size="small" @click="addTodo">添加</a-button>
          </template>
        </a-input>
      </div>

      <!-- 可拖拽的待办列表 -->
      <div class="todo-list-container">
        <draggable
          v-model="todos"
          item-key="id"
          class="todo-list"
          ghost-class="todo-ghost"
          @end="saveTodos"
          handle=".todo-drag-handle"
        >
          <template #item="{ element, index }">
            <div class="todo-item" :class="{ 'is-completed': element.completed }">
              <icon-drag-dot-vertical class="todo-drag-handle" />
              <a-checkbox v-model="element.completed" @change="saveTodos" />
              <div class="todo-text">{{ element.text }}</div>
              <a-button type="text" status="danger" size="mini" class="delete-btn" @click="deleteTodo(index)">
                <icon-close />
              </a-button>
            </div>
          </template>
        </draggable>
        <a-empty v-if="todos.length === 0" description="所有待办已清空" />
      </div>
    </div>
  </a-card>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import draggable from 'vuedraggable'
import { Message } from '@arco-design/web-vue'

// ========== 响应式数据 ==========
const newTodo = ref('')
const todos = ref([])

// ========== 生命周期 ==========
onMounted(() => {
  loadTodos()
})

// ========== 业务方法 ==========
/**
 * 加载本地待办数据
 */
const loadTodos = () => {
  const saved = localStorage.getItem('lite_todo_data')
  if (saved) {
    todos.value = JSON.parse(saved)
  } else {
    todos.value = [
      { id: 1, text: '检查邮件', completed: false },
      { id: 2, text: '准备明日会议材料', completed: false }
    ]
    saveTodos()
  }
}

/**
 * 保存待办数据到本地
 */
const saveTodos = () => {
  localStorage.setItem('lite_todo_data', JSON.stringify(todos.value))
}

/**
 * 添加新待办
 */
const addTodo = () => {
  const text = newTodo.value.trim()
  if (!text) return
  
  todos.value.unshift({
    id: Date.now(),
    text,
    completed: false
  })
  
  newTodo.value = ''
  saveTodos()
}

/**
 * 删除待办
 * @param {Number} index - 列表索引
 */
const deleteTodo = (index) => {
  todos.value.splice(index, 1)
  saveTodos()
}
</script>

<style scoped>
.todo-card {
  height: 100%;
}
.card-header {
  display: flex;
  align-items: center;
  gap: 8px;
  cursor: grab;
}
.drag-icon {
  color: var(--color-text-3);
}
.todo-content {
  display: flex;
  flex-direction: column;
  height: 300px;
}
.todo-input-wrap {
  margin-bottom: 16px;
}
.todo-list-container {
  flex: 1;
  overflow-y: auto;
}
.todo-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.todo-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px;
  background: var(--color-fill-1);
  border-radius: 4px;
  transition: background-color 0.2s;
}
.todo-item:hover {
  background: var(--color-fill-2);
}
.todo-drag-handle {
  cursor: grab;
  color: var(--color-text-4);
}
.todo-drag-handle:active {
  cursor: grabbing;
}
.todo-text {
  flex: 1;
  font-size: 14px;
  color: var(--color-text-1);
  word-break: break-all;
}
.is-completed .todo-text {
  text-decoration: line-through;
  color: var(--color-text-4);
}
.delete-btn {
  opacity: 0;
  transition: opacity 0.2s;
}
.todo-item:hover .delete-btn {
  opacity: 1;
}
.todo-ghost {
  opacity: 0.5;
  background: var(--color-fill-3);
}
</style>
