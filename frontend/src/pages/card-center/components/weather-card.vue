/*
 * @Author: 项目规范
 * @Date: 2024-03-25
 * @Description: 天气卡片，显示当前位置及多城市天气信息，包含未来5天预报
 */
<template>
  <a-card class="weather-card" :bordered="false">
    <template #title>
      <div class="card-header drag-handle">
        <icon-drag-dot-vertical class="drag-icon" />
        <span>天气预报</span>
      </div>
    </template>
    <template #extra>
      <a-input-search
        v-model="searchCity"
        placeholder="搜索城市"
        button-text="搜索"
        search-button
        @search="fetchWeather"
        style="width: 160px"
      />
    </template>

    <div class="weather-content" v-loading="loading">
      <div v-if="weatherData" class="current-weather">
        <div class="city-name">
          <icon-location /> {{ weatherData.city }}
        </div>
        <div class="main-info">
          <div class="temperature">{{ weatherData.temp }}°</div>
          <div class="desc">{{ weatherData.desc }}</div>
        </div>
        <div class="details">
          <div class="detail-item">
            <span class="label">湿度</span>
            <span class="value">{{ weatherData.humidity }}%</span>
          </div>
          <div class="detail-item">
            <span class="label">风速</span>
            <span class="value">{{ weatherData.wind }}</span>
          </div>
          <div class="detail-item">
            <span class="label">AQI</span>
            <a-tag :color="getAqiColor(weatherData.aqi)" size="small">{{ weatherData.aqi }}</a-tag>
          </div>
        </div>
      </div>

      <a-divider style="margin: 16px 0" />

      <div class="forecast-list" v-if="weatherData">
        <div v-for="(day, index) in weatherData.forecast" :key="index" class="forecast-item">
          <div class="day">{{ day.date }}</div>
          <div class="icon">{{ day.icon }}</div>
          <div class="temp-range">{{ day.min }}° ~ {{ day.max }}°</div>
        </div>
      </div>
    </div>
  </a-card>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { Message } from '@arco-design/web-vue'

// ========== 响应式数据 ==========
const searchCity = ref('北京') // 当前城市
const loading = ref(false) // 加载状态
const weatherData = ref(null) // 天气数据

// ========== 生命周期 ==========
onMounted(() => {
  fetchWeather()
})

// ========== 业务方法 ==========
/**
 * 获取天气数据（带缓存）
 */
const fetchWeather = async () => {
  if (!searchCity.value) {
    Message.warning('请输入城市名称')
    return
  }

  loading.value = true
  const cacheKey = `weather_data_${searchCity.value}`
  const cached = localStorage.getItem(cacheKey)
  
  if (cached) {
    const { data, timestamp } = JSON.parse(cached)
    // 缓存1小时有效
    if (Date.now() - timestamp < 60 * 60 * 1000) {
      weatherData.value = data
      loading.value = false
      return
    }
  }

  // ========== 步骤1：模拟接口请求 ==========
  try {
    await new Promise(resolve => setTimeout(resolve, 500))
    const mockData = generateMockWeather(searchCity.value)
    
    // ========== 步骤2：缓存并更新状态 ==========
    weatherData.value = mockData
    localStorage.setItem(cacheKey, JSON.stringify({
      data: mockData,
      timestamp: Date.now()
    }))
  } catch (error) {
    Message.error('获取天气失败')
  } finally {
    loading.value = false
  }
}

/**
 * 根据AQI获取颜色
 * @param {Number} aqi - 空气质量指数
 * @returns {String} 颜色值
 */
const getAqiColor = (aqi) => {
  if (aqi <= 50) return 'green'
  if (aqi <= 100) return 'gold'
  if (aqi <= 150) return 'orange'
  return 'red'
}

/**
 * 生成模拟天气数据
 * @param {String} city - 城市名称
 * @returns {Object} 天气数据对象
 */
const generateMockWeather = (city) => {
  const isSunny = Math.random() > 0.5
  const baseTemp = Math.floor(Math.random() * 20) + 10
  
  const forecast = []
  const today = new Date()
  const icons = ['☀️', '🌤️', '☁️', '🌧️', '⛈️']
  
  for (let i = 1; i <= 5; i++) {
    const d = new Date(today)
    d.setDate(d.getDate() + i)
    forecast.push({
      date: `${d.getMonth() + 1}/${d.getDate()}`,
      icon: icons[Math.floor(Math.random() * icons.length)],
      min: baseTemp - Math.floor(Math.random() * 5),
      max: baseTemp + Math.floor(Math.random() * 5) + 5
    })
  }

  return {
    city,
    temp: baseTemp + 2,
    desc: isSunny ? '晴朗' : '多云',
    humidity: Math.floor(Math.random() * 40) + 30,
    wind: `东南风 ${Math.floor(Math.random() * 4) + 1}级`,
    aqi: Math.floor(Math.random() * 100) + 20,
    forecast
  }
}
</script>

<style scoped>
.weather-card {
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
.weather-content {
  height: 300px;
  display: flex;
  flex-direction: column;
}
.current-weather {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 10px 0;
}
.city-name {
  font-size: 16px;
  color: var(--color-text-2);
  margin-bottom: 8px;
}
.main-info {
  display: flex;
  align-items: baseline;
  gap: 12px;
  margin-bottom: 16px;
}
.temperature {
  font-size: 48px;
  font-weight: 600;
  line-height: 1;
  color: var(--color-text-1);
}
.desc {
  font-size: 18px;
  color: var(--color-text-2);
}
.details {
  display: flex;
  justify-content: space-around;
  width: 100%;
  padding: 0 20px;
}
.detail-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 4px;
}
.detail-item .label {
  font-size: 12px;
  color: var(--color-text-3);
}
.detail-item .value {
  font-size: 14px;
  font-weight: 500;
  color: var(--color-text-1);
}
.forecast-list {
  display: flex;
  justify-content: space-between;
  padding: 0 10px;
}
.forecast-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
}
.forecast-item .day {
  font-size: 12px;
  color: var(--color-text-3);
}
.forecast-item .icon {
  font-size: 20px;
}
.forecast-item .temp-range {
  font-size: 12px;
  color: var(--color-text-2);
}
</style>
