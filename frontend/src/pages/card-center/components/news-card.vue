/*
 * @Author: 项目规范
 * @Date: 2024-03-25
 * @Description: 新闻卡片，展示实时最新资讯，支持分类筛选和点击跳转
 */
<template>
  <a-card class="news-card" :bordered="false">
    <template #title>
      <div class="card-header drag-handle">
        <icon-drag-dot-vertical class="drag-icon" />
        <span>实时新闻</span>
      </div>
    </template>
    <template #extra>
      <a-radio-group v-model="currentCategory" type="button" size="small" @change="fetchNews">
        <a-radio value="all">综合</a-radio>
        <a-radio value="finance">财经</a-radio>
        <a-radio value="tech">科技</a-radio>
        <a-radio value="sports">体育</a-radio>
      </a-radio-group>
    </template>

    <div class="news-list-container" v-loading="loading">
      <a-list :data="newsList" :bordered="false" class="news-list">
        <template #item="{ item }">
          <a-list-item class="news-item" @click="openNews(item)">
            <a-list-item-meta :title="item.title" :description="item.summary">
              <template #title>
                <div class="news-title">{{ item.title }}</div>
              </template>
              <template #description>
                <div class="news-summary">{{ item.summary }}</div>
                <div class="news-meta">
                  <span class="source">{{ item.source }}</span>
                  <span class="time">{{ item.publishTime }}</span>
                </div>
              </template>
            </a-list-item-meta>
          </a-list-item>
        </template>
        <template #empty>
          <a-empty description="暂无新闻资讯" />
        </template>
      </a-list>
    </div>
  </a-card>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { Message } from '@arco-design/web-vue'

// ========== 响应式数据 ==========
const currentCategory = ref('all') // 当前选中的分类
const loading = ref(false) // 加载状态
const newsList = ref([]) // 新闻列表数据

// ========== 生命周期 ==========
onMounted(() => {
  fetchNews()
})

// ========== 业务方法 ==========
/**
 * 获取新闻列表数据（带缓存）
 */
const fetchNews = async () => {
  loading.value = true
  
  const cacheKey = `news_data_${currentCategory.value}`
  const cached = localStorage.getItem(cacheKey)
  
  if (cached) {
    const { data, timestamp } = JSON.parse(cached)
    // 缓存10分钟有效
    if (Date.now() - timestamp < 10 * 60 * 1000) {
      newsList.value = data
      loading.value = false
      return
    }
  }

  // ========== 步骤1：模拟请求接口 ==========
  try {
    await new Promise(resolve => setTimeout(resolve, 600))
    const mockData = generateMockNews(currentCategory.value)
    
    // ========== 步骤2：更新状态并缓存 ==========
    newsList.value = mockData
    localStorage.setItem(cacheKey, JSON.stringify({
      data: mockData,
      timestamp: Date.now()
    }))
  } catch (error) {
    Message.error('获取新闻失败')
  } finally {
    loading.value = false
  }
}

/**
 * 模拟生成新闻数据
 * @param {String} category - 新闻分类
 * @returns {Array} 新闻列表
 */
const generateMockNews = (category) => {
  const titles = {
    finance: ['全球股市震荡，投资者寻找避险资产', '央行宣布新一轮降息政策', '科技巨头财报超预期，带动纳指上涨'],
    tech: ['AI模型再次进化，多模态能力突破', '新款智能手机发布，搭载自研芯片', '自动驾驶技术在更多城市落地测试'],
    sports: ['欧冠决赛之夜，豪门球队夺得桂冠', '马拉松新纪录诞生', '奥运会筹备工作进入最后冲刺阶段']
  }
  
  const baseTitles = category === 'all' 
    ? [...titles.finance, ...titles.tech, ...titles.sports]
    : titles[category] || titles.finance

  return baseTitles.map((title, index) => ({
    id: `${category}_${index}`,
    title,
    summary: `这是关于“${title}”的详细摘要内容，介绍了事件的背景、发展和未来可能的影响...`,
    source: ['新华网', '路透社', '科技日报', '体育周刊'][Math.floor(Math.random() * 4)],
    publishTime: new Date(Date.now() - Math.random() * 10000000).toLocaleString(),
    url: '#'
  }))
}

/**
 * 打开新闻详情（这里用Message模拟跳转）
 * @param {Object} item - 新闻对象
 */
const openNews = (item) => {
  Message.info(`正在打开: ${item.title}`)
  // 实际应用中会使用 window.open(item.url, '_blank')
}
</script>

<style scoped>
.news-card {
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
.news-list-container {
  height: 300px;
  overflow-y: auto;
}
.news-item {
  cursor: pointer;
  transition: background-color 0.2s;
}
.news-item:hover {
  background-color: var(--color-fill-2);
}
.news-title {
  font-weight: 500;
  font-size: 15px;
  color: var(--color-text-1);
  margin-bottom: 4px;
  display: -webkit-box;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 1;
  overflow: hidden;
}
.news-summary {
  font-size: 13px;
  color: var(--color-text-3);
  display: -webkit-box;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 2;
  overflow: hidden;
  margin-bottom: 8px;
}
.news-meta {
  display: flex;
  gap: 16px;
  font-size: 12px;
  color: var(--color-text-4);
}
</style>
