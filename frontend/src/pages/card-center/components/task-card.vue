/*
 * @Author: 项目规范
 * @Date: 2024-03-25
 * @Description: 任务管理卡片，支持任务的增删改查、优先级、进度统计
 */
<template>
  <a-card class="task-card" :bordered="false">
    <template #title>
      <div class="card-header drag-handle">
        <icon-drag-dot-vertical class="drag-icon" />
        <span>任务管理</span>
      </div>
    </template>
    <template #extra>
      <a-button type="text" size="small" @click="openTaskModal()">
        <template #icon><icon-plus /></template>
        新建
      </a-button>
    </template>

    <div class="task-content">
      <!-- 进度统计 -->
      <div class="task-stats">
        <div class="stat-info">
          <span>总进度</span>
          <span>{{ completedCount }} / {{ tasks.length }}</span>
        </div>
        <a-progress :percent="progressPercent" />
      </div>

      <!-- 筛选 -->
      <div class="task-filters">
        <a-radio-group v-model="filterStatus" type="button" size="mini">
          <a-radio value="all">全部</a-radio>
          <a-radio value="pending">待办</a-radio>
          <a-radio value="completed">已完成</a-radio>
        </a-radio-group>
      </div>

      <!-- 任务列表 -->
      <div class="task-list-container">
        <a-list :data="filteredTasks" :bordered="false" class="task-list">
          <template #item="{ item }">
            <a-list-item class="task-item" :class="{ 'is-completed': item.status === 'completed' }">
              <div class="task-row">
                <a-checkbox 
                  :model-value="item.status === 'completed'" 
                  @change="(val) => toggleTaskStatus(item, val)"
                />
                <div class="task-info">
                  <div class="task-title">
                    <a-tag :color="getPriorityColor(item.priority)" size="small">{{ getPriorityText(item.priority) }}</a-tag>
                    <span class="text">{{ item.title }}</span>
                  </div>
                  <div class="task-meta" v-if="item.deadline">
                    <icon-calendar /> {{ item.deadline }}
                  </div>
                </div>
                <div class="task-actions">
                  <a-button type="text" size="small" @click="openTaskModal(item)">
                    <template #icon><icon-edit /></template>
                  </a-button>
                  <a-popconfirm content="确认删除该任务吗？" @ok="deleteTask(item.id)">
                    <a-button type="text" status="danger" size="small">
                      <template #icon><icon-delete /></template>
                    </a-button>
                  </a-popconfirm>
                </div>
              </div>
            </a-list-item>
          </template>
          <template #empty>
            <a-empty description="暂无任务" />
          </template>
        </a-list>
      </div>
    </div>

    <!-- 任务编辑弹窗 -->
    <a-modal v-model:visible="showModal" :title="isEdit ? '编辑任务' : '新建任务'" @ok="saveTask" @cancel="showModal = false">
      <a-form :model="form" layout="vertical">
        <a-form-item field="title" label="任务标题" required>
          <a-input v-model="form.title" placeholder="请输入任务标题" />
        </a-form-item>
        <a-form-item field="deadline" label="截止日期">
          <a-date-picker v-model="form.deadline" style="width: 100%" />
        </a-form-item>
        <a-form-item field="priority" label="优先级">
          <a-select v-model="form.priority">
            <a-option value="high">高</a-option>
            <a-option value="medium">中</a-option>
            <a-option value="low">低</a-option>
          </a-select>
        </a-form-item>
      </a-form>
    </a-modal>
  </a-card>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { Message } from '@arco-design/web-vue'

// ========== 响应式数据 ==========
const tasks = ref([])
const filterStatus = ref('all')
const showModal = ref(false)
const isEdit = ref(false)

const form = reactive({
  id: null,
  title: '',
  deadline: '',
  priority: 'medium',
  status: 'pending'
})

// ========== 计算属性 ==========
const filteredTasks = computed(() => {
  if (filterStatus.value === 'all') return tasks.value
  return tasks.value.filter(t => t.status === filterStatus.value)
})

const completedCount = computed(() => tasks.value.filter(t => t.status === 'completed').length)

const progressPercent = computed(() => {
  if (tasks.value.length === 0) return 0
  return Number((completedCount.value / tasks.value.length).toFixed(2))
})

// ========== 生命周期 ==========
onMounted(() => {
  loadTasks()
})

// ========== 业务方法 ==========
/**
 * 加载任务数据
 */
const loadTasks = () => {
  const saved = localStorage.getItem('task_data')
  if (saved) {
    tasks.value = JSON.parse(saved)
  } else {
    tasks.value = [
      { id: 1, title: '完成项目架构设计', deadline: '2024-04-01', priority: 'high', status: 'pending' },
      { id: 2, title: '更新需求文档', deadline: '2024-03-28', priority: 'medium', status: 'completed' }
    ]
    saveData()
  }
}

/**
 * 保存任务数据到本地
 */
const saveData = () => {
  localStorage.setItem('task_data', JSON.stringify(tasks.value))
}

/**
 * 获取优先级颜色
 */
const getPriorityColor = (p) => {
  const map = { high: 'red', medium: 'orange', low: 'gray' }
  return map[p] || 'gray'
}

/**
 * 获取优先级文本
 */
const getPriorityText = (p) => {
  const map = { high: '高', medium: '中', low: '低' }
  return map[p] || '低'
}

/**
 * 切换任务状态
 */
const toggleTaskStatus = (item, isCompleted) => {
  item.status = isCompleted ? 'completed' : 'pending'
  saveData()
}

/**
 * 打开弹窗
 */
const openTaskModal = (item = null) => {
  if (item) {
    isEdit.value = true
    form.id = item.id
    form.title = item.title
    form.deadline = item.deadline
    form.priority = item.priority
    form.status = item.status
  } else {
    isEdit.value = false
    form.id = null
    form.title = ''
    form.deadline = ''
    form.priority = 'medium'
    form.status = 'pending'
  }
  showModal.value = true
}

/**
 * 保存任务（新增/编辑）
 */
const saveTask = () => {
  if (!form.title) {
    Message.warning('请输入任务标题')
    return false
  }

  if (isEdit.value) {
    const index = tasks.value.findIndex(t => t.id === form.id)
    if (index > -1) {
      tasks.value[index] = { ...form }
    }
  } else {
    tasks.value.unshift({
      ...form,
      id: Date.now()
    })
  }
  
  saveData()
  Message.success(isEdit.value ? '修改成功' : '创建成功')
  return true
}

/**
 * 删除任务
 */
const deleteTask = (id) => {
  tasks.value = tasks.value.filter(t => t.id !== id)
  saveData()
  Message.success('已删除')
}
</script>

<style scoped>
.task-card {
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
.task-content {
  display: flex;
  flex-direction: column;
  height: 300px;
}
.task-stats {
  margin-bottom: 12px;
}
.stat-info {
  display: flex;
  justify-content: space-between;
  margin-bottom: 4px;
  font-size: 13px;
  color: var(--color-text-2);
}
.task-filters {
  margin-bottom: 12px;
}
.task-list-container {
  flex: 1;
  overflow-y: auto;
}
.task-row {
  display: flex;
  align-items: flex-start;
  gap: 12px;
  width: 100%;
}
.task-info {
  flex: 1;
}
.task-title {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 4px;
}
.task-title .text {
  font-size: 14px;
  color: var(--color-text-1);
}
.task-meta {
  font-size: 12px;
  color: var(--color-text-3);
}
.is-completed .task-title .text {
  text-decoration: line-through;
  color: var(--color-text-4);
}
.task-actions {
  display: flex;
  gap: 4px;
  opacity: 0;
  transition: opacity 0.2s;
}
.task-item:hover .task-actions {
  opacity: 1;
}
</style>
