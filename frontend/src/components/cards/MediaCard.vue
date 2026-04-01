<template>
  <a-card class="media-card" :body-style="{ padding: 0 }">
    <div class="media-wrapper">
      <video v-if="type === 'video'" controls :src="src" :poster="poster"></video>
      <audio v-else-if="type === 'audio'" controls :src="src"></audio>
      <img v-else :src="src" :alt="alt" />
    </div>
    <div class="media-info">
      <div class="title">{{ title }}</div>
      <div class="desc">{{ description }}</div>
    </div>
  </a-card>
</template>

<script setup>
defineProps({
	type: { type: String, default: "video" }, // video, audio, image
	src: {
		type: String,
		default:
			"https://p1-arco.byteimg.com/tos-cn-i-uwbnlip3yd/cd7a1aaea8e1c5e3d26fe2591e561798.png~tplv-uwbnlip3yd-webp.webp",
	},
	poster: { type: String, default: "" },
	alt: { type: String, default: "Media content" },
	title: { type: String, default: "Media Title" },
	description: { type: String, default: "Description of the media content." },
});
</script>

<style scoped>
.media-card { width: 100%; max-width: 500px; border-radius: 8px; overflow: hidden; }
.media-wrapper { width: 100%; background: #000; display: flex; justify-content: center; }
.media-wrapper video, .media-wrapper img { width: 100%; max-height: 300px; object-fit: contain; }
.media-wrapper audio { width: 100%; padding: 10px; }
.media-info { padding: 16px; }
.title { font-size: 16px; font-weight: bold; margin-bottom: 4px; }
.desc { color: var(--color-text-3); font-size: 14px; }
</style>
