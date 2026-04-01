<template>
  <a-card class="user-profile-card">
    <div class="header">
      <a-avatar :size="64">
        <img :src="avatar" alt="avatar" />
      </a-avatar>
      <div class="info">
        <div class="name">{{ name }}</div>
        <div class="role">{{ role }}</div>
      </div>
    </div>
    <div class="bio">{{ bio }}</div>
    <a-divider margin="12px" />
    <div class="stats">
      <div class="stat-item">
        <div class="value">{{ posts }}</div>
        <div class="label">Posts</div>
      </div>
      <div class="stat-item">
        <div class="value">{{ followers }}</div>
        <div class="label">Followers</div>
      </div>
      <div class="stat-item">
        <div class="value">{{ following }}</div>
        <div class="label">Following</div>
      </div>
    </div>
    <a-divider margin="12px" />
    <div class="actions">
      <a-button type="primary" shape="round">Follow</a-button>
      <a-button shape="round">Message</a-button>
    </div>
  </a-card>
</template>

<script setup>
defineProps({
	name: { type: String, default: "User Name" },
	role: { type: String, default: "Software Engineer" },
	bio: { type: String, default: "Passionate about building great software." },
	avatar: {
		type: String,
		default:
			"https://p1-arco.byteimg.com/tos-cn-i-uwbnlip3yd/3ee5f13fb09879ecb5185e440cef6eb9.png~tplv-uwbnlip3yd-webp.webp",
	},
	posts: { type: Number, default: 120 },
	followers: { type: String, default: "2.5k" },
	following: { type: Number, default: 180 },
});
</script>

<style scoped>
.user-profile-card { width: 300px; border-radius: 8px; text-align: center; }
.header { display: flex; flex-direction: column; align-items: center; margin-bottom: 16px; }
.name { font-size: 18px; font-weight: bold; margin-top: 8px; }
.role { color: var(--color-text-3); font-size: 14px; }
.bio { color: var(--color-text-2); font-size: 14px; line-height: 1.5; margin-bottom: 12px; }
.stats { display: flex; justify-content: space-around; }
.stat-item { display: flex; flex-direction: column; align-items: center; }
.value { font-weight: bold; font-size: 16px; }
.label { color: var(--color-text-3); font-size: 12px; }
.actions { display: flex; gap: 12px; justify-content: center; }
</style>
