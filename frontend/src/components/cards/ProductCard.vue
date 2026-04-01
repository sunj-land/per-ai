<template>
  <a-card class="product-card" hoverable>
    <template #cover>
      <div class="image-container">
        <img :src="image" :alt="title" />
      </div>
    </template>
    <a-card-meta :title="title">
      <template #description>
        <div class="description">{{ description }}</div>
        <div class="price-row">
          <span class="price">{{ price }}</span>
          <a-rate readonly :default-value="rating" allow-half />
        </div>
      </template>
    </a-card-meta>
    <template #actions>
      <a-button type="primary" size="small">Buy Now</a-button>
      <a-button size="small">Add to Cart</a-button>
    </template>
  </a-card>
</template>

<script setup>
defineProps({
	title: { type: String, default: "Product Name" },
	description: { type: String, default: "Product description goes here." },
	image: {
		type: String,
		default:
			"https://p1-arco.byteimg.com/tos-cn-i-uwbnlip3yd/a8c8cdb109cb051163646151a4a5083b.png~tplv-uwbnlip3yd-webp.webp",
	},
	price: { type: String, default: "$99.99" },
	rating: { type: Number, default: 4.5 },
});
</script>

<style scoped>
.product-card { width: 300px; border-radius: 8px; overflow: hidden; }
.image-container { height: 200px; overflow: hidden; display: flex; align-items: center; justify-content: center; background: #f7f8fa; }
.image-container img { width: 100%; height: 100%; object-fit: cover; transition: transform 0.3s; }
.product-card:hover img { transform: scale(1.05); }
.description { margin-bottom: 10px; color: var(--color-text-3); display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden; }
.price-row { display: flex; justify-content: space-between; align-items: center; margin-top: 8px; }
.price { color: rgb(var(--danger-6)); font-size: 18px; font-weight: bold; }
</style>
