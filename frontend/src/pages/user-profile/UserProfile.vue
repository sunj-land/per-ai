<template>
  <div class="profile-container">
    <a-page-header
      title="User Profile Management"
      subtitle="Manage your Soul Identity and Personal Rules for AI context"
      @back="$router.push('/')"
    >
      <template #extra>
        <a-button type="primary" @click="handleSave" :loading="loadingStore.isLoading('profile-update')">
          <template #icon><icon-save /></template>
          Save Changes
        </a-button>
      </template>
    </a-page-header>

    <div class="content-wrapper">
      <a-spin :loading="loadingStore.isLoading('profile-get')" style="width: 100%">
        <a-card title="Soul Identity" class="section-card">
        <template #extra>
          <a-tooltip content="Define who you are. This information helps the AI understand your persona, background, and preferences.">
            <icon-info-circle />
          </a-tooltip>
        </template>
        <a-textarea
          v-model="form.identity"
          placeholder="e.g., I am a senior software engineer interested in AI architecture. I prefer concise technical explanations..."
          :auto-size="{ minRows: 4, maxRows: 10 }"
          allow-clear
          show-word-limit
        />
      </a-card>

      <a-card title="Personal Rules" class="section-card" style="margin-top: 24px">
        <template #extra>
          <a-tooltip content="Set explicit rules for the AI. e.g., 'Always answer in Chinese', 'Be concise', 'Explain concepts with metaphors'.">
            <icon-info-circle />
          </a-tooltip>
        </template>
        <a-textarea
          v-model="form.rules"
          placeholder="e.g., \n1. Always use Python for code examples.\n2. Keep explanations under 200 words.\n3. Use emojis sparingly."
          :auto-size="{ minRows: 6, maxRows: 15 }"
          allow-clear
          show-word-limit
        />
      </a-card>

      <a-card title="Version History" class="section-card" style="margin-top: 24px">
        <a-table :data="history" :pagination="false" :loading="loadingStore.isLoading('profile-history')" size="small">
          <template #columns>
            <a-table-column title="Time" data-index="created_at" :width="180">
                <template #cell="{ record }">
                    {{ new Date(record.created_at).toLocaleString() }}
                </template>
            </a-table-column>
            <a-table-column title="Identity" data-index="identity" ellipsis tooltip />
            <a-table-column title="Rules" data-index="rules" ellipsis tooltip />
            <a-table-column title="Action" :width="100">
                <template #cell="{ record }">
                    <a-button type="text" size="mini" @click="restoreVersion(record)">Restore</a-button>
                </template>
            </a-table-column>
          </template>
        </a-table>
      </a-card>
      </a-spin>
    </div>
  </div>
</template>

<script setup>
/*
 * @Author: 项目规范
 * @Date: 自动生成
 * @Description: 用户个人信息管理页面
 */

import { Message } from "@arco-design/web-vue";
import { onMounted, reactive, ref } from "vue";
import { useRouter } from "vue-router";
import {
	getUserProfile,
	getUserProfileHistory,
	updateUserProfile,
} from "@/api/user-profile";
import { useLoadingStore } from "@/store/loading";

const router = useRouter();
const loadingStore = useLoadingStore();
const history = ref([]);
const form = reactive({
	identity: "",
	rules: "",
});

// ========== 步骤1：获取用户信息 ==========
const fetchProfile = async () => {
	try {
		const res = await getUserProfile();
		if (res) {
			form.identity = res.identity || "";
			form.rules = res.rules || "";
		}
	} catch (error) {
		console.error(error);
	}
};

// ========== 步骤2：获取历史记录 ==========
const fetchHistory = async () => {
	try {
		const res = await getUserProfileHistory();
		history.value = res || [];
	} catch (error) {
		console.error(error);
	}
};

// ========== 步骤3：保存用户信息 ==========
const handleSave = async () => {
	try {
		await updateUserProfile({
			identity: form.identity,
			rules: form.rules,
		});
		Message.success("Profile updated successfully!");
		fetchHistory(); // 刷新历史记录
	} catch (error) {
		console.error(error);
	}
};

// ========== 步骤4：恢复历史版本 ==========
const restoreVersion = (record) => {
	form.identity = record.identity;
	form.rules = record.rules;
	Message.info("Version content loaded into editor. Click Save to apply.");
};

onMounted(() => {
	fetchProfile();
	fetchHistory();
});
</script>

<style scoped>
.profile-container {
  padding: 24px;
  background-color: var(--color-bg-1);
  min-height: 100vh;
}

.content-wrapper {
  max-width: 800px;
  margin: 0 auto;
  padding-top: 24px;
}

.section-card {
  border-radius: 8px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.05);
}
</style>
