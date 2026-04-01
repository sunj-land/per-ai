/*
 * @Author: 项目规范
 * @Date: 2024-03-25
 * @Description: 股价趋势卡片，展示股票价格走势折线图，包含开盘价、收盘价等数据点
 */
<template>
  <a-card class="stock-card" :bordered="false">
    <template #title>
      <div class="card-header drag-handle">
        <icon-drag-dot-vertical class="drag-icon" />
        <span>股价趋势</span>
      </div>
    </template>
    <template #extra>
      <a-input-search
        v-model="stockCode"
        placeholder="输入股票代码"
        button-text="查询"
        search-button
        @search="fetchStockData"
        style="width: 200px"
      />
    </template>

    <div class="chart-container" ref="chartRef" v-loading="loading"></div>
  </a-card>
</template>

<script setup>
import { ref, onMounted, onUnmounted, shallowRef } from 'vue'
import * as echarts from 'echarts'
import { Message } from '@arco-design/web-vue'

// ========== 响应式数据 ==========
const stockCode = ref('AAPL') // 默认股票代码
const loading = ref(false) // 加载状态
const chartRef = ref(null) // 图表DOM引用
const chartInstance = shallowRef(null) // ECharts实例

// ========== 生命周期 ==========
onMounted(() => {
  initChart()
  fetchStockData()
  window.addEventListener('resize', handleResize)
})

onUnmounted(() => {
  window.removeEventListener('resize', handleResize)
  if (chartInstance.value) {
    chartInstance.value.dispose()
  }
})

// ========== 业务方法 ==========
/**
 * 初始化图表实例
 */
const initChart = () => {
  if (chartRef.value) {
    chartInstance.value = echarts.init(chartRef.value)
  }
}

/**
 * 处理窗口大小变化，重绘图表
 */
const handleResize = () => {
  if (chartInstance.value) {
    chartInstance.value.resize()
  }
}

/**
 * 获取股票数据并渲染图表（模拟API请求与缓存）
 */
const fetchStockData = async () => {
  if (!stockCode.value) {
    Message.warning('请输入股票代码')
    return
  }

  loading.value = true
  
  // 模拟缓存机制
  const cacheKey = `stock_data_${stockCode.value}`
  const cached = localStorage.getItem(cacheKey)
  
  if (cached) {
    const { data, timestamp } = JSON.parse(cached)
    // 缓存5分钟有效
    if (Date.now() - timestamp < 5 * 60 * 1000) {
      renderChart(data)
      loading.value = false
      return
    }
  }

  // ========== 步骤1：模拟请求数据 ==========
  try {
    await new Promise(resolve => setTimeout(resolve, 800))
    const mockData = generateMockStockData()
    
    // ========== 步骤2：缓存数据 ==========
    localStorage.setItem(cacheKey, JSON.stringify({
      data: mockData,
      timestamp: Date.now()
    }))
    
    // ========== 步骤3：渲染图表 ==========
    renderChart(mockData)
  } catch (error) {
    Message.error('获取股票数据失败')
  } finally {
    loading.value = false
  }
}

/**
 * 生成模拟的股票K线数据（过去8周，约40个交易日）
 * @returns {Object} 包含日期和价格的数组
 */
const generateMockStockData = () => {
  const dates = []
  const values = []
  let basePrice = Math.random() * 100 + 50
  
  const today = new Date()
  for (let i = 40; i >= 0; i--) {
    const d = new Date(today)
    d.setDate(d.getDate() - i)
    // 跳过周末
    if (d.getDay() === 0 || d.getDay() === 6) continue
    
    dates.push(`${d.getMonth() + 1}/${d.getDate()}`)
    
    const open = basePrice + (Math.random() - 0.5) * 5
    const close = open + (Math.random() - 0.5) * 5
    const highest = Math.max(open, close) + Math.random() * 2
    const lowest = Math.min(open, close) - Math.random() * 2
    
    values.push([open, close, lowest, highest])
    basePrice = close
  }
  return { dates, values }
}

/**
 * 渲染ECharts图表
 * @param {Object} data - 包含dates和values的数据对象
 */
const renderChart = (data) => {
  if (!chartInstance.value) return

  const option = {
    tooltip: {
      trigger: 'axis',
      axisPointer: { type: 'cross' }
    },
    grid: {
      left: '10%',
      right: '10%',
      bottom: '15%'
    },
    xAxis: {
      type: 'category',
      data: data.dates,
      scale: true,
      boundaryGap: false,
      axisLine: { onZero: false },
      splitLine: { show: false }
    },
    yAxis: {
      scale: true,
      splitArea: { show: true }
    },
    dataZoom: [
      { type: 'inside', start: 50, end: 100 },
      { show: true, type: 'slider', top: '90%', start: 50, end: 100 }
    ],
    series: [
      {
        name: 'K线',
        type: 'candlestick',
        data: data.values,
        itemStyle: {
          color: '#ec0000',
          color0: '#00da3c',
          borderColor: '#8A0000',
          borderColor0: '#008F28'
        }
      }
    ]
  }
  
  chartInstance.value.setOption(option)
}
</script>

<style scoped>
.stock-card {
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
.card-header:active {
  cursor: grabbing;
}
.chart-container {
  height: 300px;
  width: 100%;
}
</style>
