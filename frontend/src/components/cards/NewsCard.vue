<template>
  <a-card class="news-card" hoverable>
    <div class="news-content">
      <div class="text-area">
        <div class="meta">
          <a-tag size="small" color="blue">{{ source }}</a-tag>
          <span class="date">{{ date }}</span>
        </div>
        <h3 class="title">{{ title }}</h3>
        <p class="summary">{{ summary }}</p>
      </div>
      <div class="image-area" v-if="thumbnail">
        <img :src="thumbnail" alt="thumbnail" />
      </div>
    </div>
  </a-card>
</template>

<script setup>
defineProps({
	title: { type: String, default: "News Headline" },
	summary: { type: String, default: "Brief summary of the news article..." },
	source: { type: String, default: "TechCrunch" },
	date: { type: String, default: "2 hours ago" },
	thumbnail: {
		type: String,
		default:
			"https://p1-arco.byteimg.com/tos-cn-i-uwbnlip3yd/cd7a1aaea8e1c5e3d26fe2591e561798.png~tplv-uwbnlip3yd-webp.webp",
	},
});
</script>

<style scoped>
.news-card { width: 100%; max-width: 600px; border-radius: 4px; }
.news-content { display: flex; gap: 16px; }
.text-area { flex: 1; }
.image-area { width: 120px; height: 90px; border-radius: 4px; overflow: hidden; flex-shrink: 0; }
.image-area img { width: 100%; height: 100%; object-fit: cover; }
.meta { display: flex; align-items: center; gap: 8px; margin-bottom: 8px; }
.date { color: var(--color-text-3); font-size: 12px; }
.title { margin: 0 0 8px 0; font-size: 16px; font-weight: bold; color: var(--color-text-1); line-height: 1.4; }
.summary { margin: 0; color: var(--color-text-3); font-size: 14px; line-height: 1.5; display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden; }
</style>
