/*
 * @Author: 项目规范
 * @Date: 2024-03-25
 * @Description: 提醒事项卡片，创建和管理个人提醒事项，支持优先级和完成状态
 */
<template>
  <a-card class="reminder-card" :bordered="false">
    <template #title>
      <div class="card-header drag-handle">
        <icon-drag-dot-vertical class="drag-icon" />
        <span>提醒事项</span>
      </div>
    </template>
    <template #extra>
      <a-button type="text" size="small" @click="showAddModal = true">
        <template #icon><icon-plus /></template>
        添加
      </a-button>
    </template>

    <div class="reminder-list-container">
      <a-list :data="reminders" :bordered="false" class="reminder-list">
        <template #item="{ item, index }">
          <a-list-item class="reminder-item" :class="{ 'is-completed': item.completed }">
            <div class="reminder-content">
              <a-checkbox v-model="item.completed" @change="saveReminders" />
              <div class="reminder-info">
                <div class="reminder-title">
                  <a-tag v-if="item.priority === 'high'" color="red" size="small">高</a-tag>
                  <a-tag v-else-if="item.priority === 'medium'" color="orange" size="small">中</a-tag>
                  <a-tag v-else color="gray" size="small">低</a-tag>
                  <span class="text">{{ item.title }}</span>
                </div>
                <div class="reminder-meta">
                  <span class="time"><icon-clock-circle /> {{ item.time }}</span>
                  <span v-if="item.repeat !== 'none'" class="repeat"><icon-sync /> {{ getRepeatText(item.repeat) }}</span>
                </div>
              </div>
              <a-button type="text" status="danger" size="small" @click="deleteReminder(index)">
                <template #icon><icon-delete /></template>
              </a-button>
            </div>
          </a-list-item>
        </template>
        <template #empty>
          <a-empty description="暂无提醒事项" />
        </template>
      </a-list>
    </div>

    <!-- 添加提醒弹窗 -->
    <a-modal v-model:visible="showAddModal" title="添加提醒事项" @ok="addReminder" @cancel="showAddModal = false">
      <a-form :model="form" layout="vertical">
        <a-form-item field="title" label="事项名称" required>
          <a-input v-model="form.title" placeholder="请输入提醒事项" />
        </a-form-item>
        <a-form-item field="time" label="提醒时间" required>
          <a-date-picker v-model="form.time" show-time format="YYYY-MM-DD HH:mm" style="width: 100%" />
        </a-form-item>
        <a-form-item field="priority" label="优先级">
          <a-select v-model="form.priority">
            <a-option value="low">低</a-option>
            <a-option value="medium">中</a-option>
            <a-option value="high">高</a-option>
          </a-select>
        </a-form-item>
        <a-form-item field="repeat" label="重复周期">
          <a-select v-model="form.repeat">
            <a-option value="none">不重复</a-option>
            <a-option value="daily">每天</a-option>
            <a-option value="weekly">每周</a-option>
            <a-option value="monthly">每月</a-option>
          </a-select>
        </a-form-item>
      </a-form>
    </a-modal>
  </a-card>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { Message } from '@arco-design/web-vue'

// ========== 响应式数据 ==========
const showAddModal = ref(false)
const reminders = ref([])

const form = reactive({
  title: '',
  time: '',
  priority: 'medium',
  repeat: 'none'
})

// ========== 生命周期 ==========
onMounted(() => {
  loadReminders()
  // 模拟到期提醒检查
  setInterval(checkDueReminders, 60000)
})

// ========== 业务方法 ==========
/**
 * 加载本地存储的提醒事项
 */
const loadReminders = () => {
  const saved = localStorage.getItem('reminder_data')
  if (saved) {
    reminders.value = JSON.parse(saved)
  } else {
    // 默认数据
    reminders.value = [
      { id: 1, title: '喝水休息', time: '2024-03-25 15:00', priority: 'medium', repeat: 'daily', completed: false },
      { id: 2, title: '提交周报', time: '2024-03-29 18:00', priority: 'high', repeat: 'weekly', completed: false }
    ]
    saveReminders()
  }
}

/**
 * 保存提醒事项到本地
 */
const saveReminders = () => {
  localStorage.setItem('reminder_data', JSON.stringify(reminders.value))
}

/**
 * 添加新的提醒事项
 */
const addReminder = () => {
  if (!form.title || !form.time) {
    Message.warning('请填写完整信息')
    return false
  }
  
  reminders.value.unshift({
    id: Date.now(),
    title: form.title,
    time: form.time,
    priority: form.priority,
    repeat: form.repeat,
    completed: false
  })
  
  saveReminders()
  Message.success('添加成功')
  
  // 重置表单
  form.title = ''
  form.time = ''
  form.priority = 'medium'
  form.repeat = 'none'
  return true
}

/**
 * 删除提醒事项
 * @param {Number} index - 列表索引
 */
const deleteReminder = (index) => {
  reminders.value.splice(index, 1)
  saveReminders()
  Message.success('已删除')
}

/**
 * 获取重复周期的中文文本
 * @param {String} value - 英文标识
 * @returns {String} 中文文本
 */
const getRepeatText = (value) => {
  const map = { daily: '每天', weekly: '每周', monthly: '每月' }
  return map[value] || ''
}

/**
 * 检查是否有到期的提醒
 */
const checkDueReminders = () => {
  const now = new Date()
  reminders.value.forEach(item => {
    if (!item.completed) {
      const itemTime = new Date(item.time)
      // 如果时间误差在1分钟内
      if (Math.abs(now - itemTime) < 60000) {
        Message.info({
          content: `【提醒】${item.title}`,
          duration: 5000
        })
      }
    }
  })
}
</script>

<style scoped>
.reminder-card {
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
.reminder-list-container {
  height: 300px;
  overflow-y: auto;
}
.reminder-item {
  padding: 12px 0;
}
.reminder-content {
  display: flex;
  align-items: flex-start;
  gap: 12px;
  width: 100%;
}
.reminder-info {
  flex: 1;
}
.reminder-title {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 4px;
}
.reminder-title .text {
  font-size: 15px;
  color: var(--color-text-1);
}
.reminder-meta {
  display: flex;
  gap: 12px;
  font-size: 12px;
  color: var(--color-text-3);
}
.is-completed .reminder-title .text {
  text-decoration: line-through;
  color: var(--color-text-4);
}
</style>
