<template>
  <div class="app-sidebar" :class="{ collapsed: isCollapsed }">
    <!-- Top Section: Functional Modules -->
    <div class="sidebar-top">
      <div class="logo-area" :class="{ 'collapsed-logo': isCollapsed }">
        <div class="logo-left" @click="handleNavigate('/')" v-if="!isCollapsed">
          <div class="logo-icon">AI</div>
          <span class="logo-text">secretary</span>
        </div>
        <div class="collapse-btn" @click="toggleCollapse">
          <icon-menu-unfold v-if="isCollapsed" />
          <icon-menu-fold v-else />
        </div>
      </div>

      <div class="nav-menu">
        <div
          class="nav-item"
          :class="{ active: currentRoute === '/' }"
          @click="handleNavigate('/')"
        >
          <icon-message class="nav-icon" />
          <span class="nav-label">Chat</span>
        </div>
        <div
          class="nav-item"
          :class="{ active: currentRoute.startsWith('/agent-center') }"
          @click="handleNavigate('/agent-center')"
        >
          <icon-robot class="nav-icon" />
          <span class="nav-label">Agents</span>
        </div>
        <div
          class="nav-item"
          :class="{ active: currentRoute.startsWith('/rss') }"
          @click="handleNavigate('/rss/feeds')"
        >
          <icon-subscribe class="nav-icon" />
          <span class="nav-label">RSS</span>
        </div>
        <div
          class="nav-item"
          :class="{ active: currentRoute.startsWith('/task-center') }"
          @click="handleNavigate('/task-center')"
        >
          <icon-schedule class="nav-icon" />
          <span class="nav-label">Tasks</span>
        </div>
        <div
          class="nav-item"
          :class="{ active: currentRoute.startsWith('/schedule') }"
          @click="handleNavigate('/schedule')"
        >
          <icon-calendar class="nav-icon" />
          <span class="nav-label">Schedule</span>
        </div>
        <div
          class="nav-item"
          :class="{ active: currentRoute.startsWith('/messages') }"
          @click="handleNavigate('/messages')"
        >
          <icon-notification class="nav-icon" />
          <span class="nav-label">Messages</span>
        </div>
        <div
          class="nav-item"
          :class="{ active: currentRoute.startsWith('/channels') }"
          @click="handleNavigate('/channels')"
        >
          <icon-relation class="nav-icon" />
          <span class="nav-label">Channels</span>
        </div>
        <div
          class="nav-item"
          :class="{ active: currentRoute.startsWith('/card-center') }"
          @click="handleNavigate('/card-center')"
        >
          <icon-apps class="nav-icon" />
          <span class="nav-label">Cards</span>
        </div>
        <div
          class="nav-item"
          :class="{ active: currentRoute.startsWith('/attachment-center') }"
          @click="handleNavigate('/attachment-center')"
        >
          <icon-attachment class="nav-icon" />
          <span class="nav-label">Files</span>
        </div>
        <div
          class="nav-item"
          :class="{ active: currentRoute.startsWith('/plan') }"
          @click="handleNavigate('/plan')"
        >
          <icon-mind-mapping class="nav-icon" />
          <span class="nav-label">Plan</span>
        </div>
        <div
          class="nav-item"
          :class="{ active: currentRoute.startsWith('/agent-test') }"
          @click="handleNavigate('/agent-test')"
        >
          <icon-experiment class="nav-icon" />
          <span class="nav-label">Agent Test</span>
        </div>
      </div>
    </div>

    <!-- Middle Section: Chat List -->
    <div class="sidebar-middle">
      <div class="chat-list-header" :class="{ 'collapsed-header': isCollapsed }">
        <a-button
          type="primary"
          :long="!isCollapsed"
          class="new-chat-btn"
          :loading="createLoading"
          @click="handleNewChat"
          :shape="isCollapsed ? 'circle' : 'square'"
        >
          <template #icon><icon-plus /></template>
          <span v-if="!isCollapsed">New Chat</span>
        </a-button>
      </div>

      <div class="chat-search" v-if="!isCollapsed">
        <a-input-search
          v-model="searchQuery"
          placeholder="Search chats..."
          allow-clear
          @search="handleSearch"
          @press-enter="handleSearch"
          class="search-input"
        />
      </div>

      <!-- Fixed QQBot Entry -->
      <div class="chat-list-container qqbot-container" style="flex: 0 0 auto; margin-bottom: 8px;">
        <div class="chat-list">
          <div
            class="chat-item"
            :class="{ active: currentSessionId === qqbotSessionId && currentRoute === '/' }"
            @click="handleSelectQQBot"
            style="background-color: var(--color-fill-2);"
          >
            <div class="chat-item-icon" style="color: #165dff;">
              <icon-robot />
            </div>
            <div class="chat-item-content">
              <div class="chat-title" style="font-weight: bold; color: #165dff;">QQBot 协同会话</div>
              <div class="chat-time">Fixed</div>
            </div>
          </div>
        </div>
      </div>

      <div class="chat-list-container">
        <SkeletonLoading :loading="listLoading" :rows="5" :full-width="false">
          <div v-if="sessions.length === 0" class="empty-state">
            No chats found
          </div>
          <div v-else class="chat-list">
            <div
              v-for="session in sessions"
              :key="session.id"
              class="chat-item"
              :class="{ active: currentSessionId === session.id && currentRoute === '/' }"
              @click="handleSelectSession(session.id)"
            >
              <div class="chat-item-icon">
                <icon-message />
              </div>
              <div class="chat-item-content">
                <div class="chat-title">{{ session.title }}</div>
                <div class="chat-time">{{ formatDate(session.updated_at) }}</div>
              </div>
              <div class="chat-actions">
                 <a-dropdown trigger="click" position="br" @select="handleDropdownSelect($event, session)">
                    <icon-more class="more-icon" @click.stop />
                    <template #content>
                      <a-doption value="delete" style="color: rgb(var(--danger-6))">Delete</a-doption>
                    </template>
                 </a-dropdown>
              </div>
            </div>
          </div>
        </SkeletonLoading>
      </div>
    </div>

    <!-- Bottom Section: User Profile -->
    <div class="sidebar-bottom">
      <div
        class="user-profile"
        :class="{ active: currentRoute === '/profile' }"
        @click="handleNavigate('/profile')"
      >
        <a-avatar :size="32" class="user-avatar">{{ user?.name?.[0] || 'U' }}</a-avatar>
        <div class="user-info">
          <div class="user-name">{{ user?.name || user?.email || 'Guest' }}</div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { storeToRefs } from "pinia";
import { computed, onMounted, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import { useWindowSize } from "@vueuse/core";
import SkeletonLoading from "../loading/SkeletonLoading.vue";
import { getQQBotSession } from "../../api/chat";
import { useAuthStore } from "../../store/auth";
import { useChatStore } from "../../store/chat";
import { useLoadingStore } from "../../store/loading";

const router = useRouter();
const route = useRoute();
const chatStore = useChatStore();
const authStore = useAuthStore();
const loadingStore = useLoadingStore();

const { sessions, currentSessionId, searchQuery } = storeToRefs(chatStore);
const { user } = storeToRefs(authStore);

const listLoading = computed(() => loadingStore.isLoading("session-list"));
const createLoading = computed(() => loadingStore.isLoading("session-create"));

const currentRoute = computed(() => route.path);
const qqbotSessionId = ref(null);

const { width } = useWindowSize();
const isCollapsed = ref(width.value < 768);

watch(width, (newWidth) => {
  if (newWidth < 768 && !isCollapsed.value) {
    isCollapsed.value = true;
  } else if (newWidth >= 768 && isCollapsed.value) {
    isCollapsed.value = false;
  }
});

const toggleCollapse = () => {
  isCollapsed.value = !isCollapsed.value;
};

onMounted(async () => {
	chatStore.loadSessions();
	try {
		const res = await getQQBotSession();
		if (res?.id) {
			qqbotSessionId.value = res.id;
		}
	} catch (e) {
		console.error("Failed to load QQBot session", e);
	}

	if (!user.value) {
		try {
			await authStore.fetchUser(); // Assuming fetchUser exists in auth store
		} catch (e) {
			console.error(e);
		}
	}
});

const handleNavigate = (path) => {
	router.push(path);
};

const handleSelectQQBot = async () => {
	if (currentRoute.value !== "/") {
		router.push("/");
	}
	await chatStore.loadQQBotSession();
};

const handleSelectSession = (id) => {
	if (currentRoute.value !== "/") {
		router.push("/");
	}
	chatStore.selectSession(id);
};

const handleNewChat = () => {
	if (currentRoute.value !== "/") {
		router.push("/");
	}
	chatStore.createNewSession();
};

const handleSearch = () => {
	chatStore.loadSessions();
};

const handleDropdownSelect = async (value, session) => {
	if (value === "delete") {
		await chatStore.removeSession(session.id);
	}
};

const formatDate = (dateString) => {
	if (!dateString) return "";
	const date = new Date(dateString);
	return date.toLocaleDateString();
};
</script>

<style scoped>
.app-sidebar {
  display: flex;
  flex-direction: column;
  height: 100vh;
  width: 260px;
  background-color: var(--color-bg-2);
  border-right: 1px solid var(--color-border);
  flex-shrink: 0;
  transition: width 0.3s ease;
}

.app-sidebar.collapsed {
  width: 80px;
}

.sidebar-top {
  padding: 16px;
  border-bottom: 1px solid var(--color-border-2);
}

.logo-area {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 20px;
  color: rgb(var(--primary-6));
}

.logo-left {
  display: flex;
  align-items: center;
  gap: 8px;
  cursor: pointer;
  font-weight: bold;
  font-size: 18px;
}

.collapsed-logo {
  justify-content: center;
}

.collapse-btn {
  cursor: pointer;
  font-size: 18px;
  color: var(--color-text-2);
  display: flex;
  align-items: center;
  justify-content: center;
  width: 32px;
  height: 32px;
  border-radius: 8px;
  transition: background-color 0.2s;
}

.collapse-btn:hover {
  background-color: var(--color-fill-2);
}

.logo-icon {
  width: 32px;
  height: 32px;
  background: rgb(var(--primary-6));
  color: white;
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 20px;
}

.nav-menu {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.nav-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 12px;
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.2s;
  color: var(--color-text-2);
}

.app-sidebar.collapsed .nav-item {
  justify-content: center;
  padding: 10px 0;
}

.app-sidebar.collapsed .nav-icon {
  margin: 0;
}

.app-sidebar.collapsed .nav-label,
.app-sidebar.collapsed .chat-title,
.app-sidebar.collapsed .chat-time,
.app-sidebar.collapsed .chat-actions,
.app-sidebar.collapsed .user-name,
.app-sidebar.collapsed .user-info,
.app-sidebar.collapsed .empty-state {
  display: none;
}

.nav-item:hover {
  background-color: var(--color-fill-2);
}

.nav-item.active {
  background-color: var(--color-fill-3);
  color: rgb(var(--primary-6));
  font-weight: 500;
}

.nav-icon {
  font-size: 18px;
}

.sidebar-middle {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  padding-top: 16px;
}

.chat-list-header {
  padding: 0 16px 12px;
  display: flex;
  justify-content: center;
}

.app-sidebar.collapsed .chat-list-header {
  padding: 0 8px 12px;
}

.chat-search {
  padding: 0 16px 12px;
}

.chat-list-container {
  flex: 1;
  overflow-y: auto;
  padding: 0 8px;
}

.chat-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 12px;
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.2s;
  margin-bottom: 4px;
  position: relative;
}

.chat-item:hover {
  background-color: var(--color-fill-2);
}

.chat-item.active {
  background-color: var(--color-fill-3);
}

.chat-item-icon {
  color: var(--color-text-3);
}

.chat-item-content {
  flex: 1;
  overflow: hidden;
}

.chat-title {
  font-size: 14px;
  color: var(--color-text-1);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.chat-time {
  font-size: 12px;
  color: var(--color-text-3);
  margin-top: 2px;
}

.chat-actions {
  opacity: 0;
  transition: opacity 0.2s;
}

.chat-item:hover .chat-actions {
  opacity: 1;
}

.app-sidebar.collapsed .chat-item {
  justify-content: center;
  padding: 10px 0;
}

.app-sidebar.collapsed .chat-item-content {
  display: none;
}

.app-sidebar.collapsed .chat-item-icon {
  margin: 0;
}

.more-icon {
  color: var(--color-text-3);
  cursor: pointer;
}

.more-icon:hover {
  color: var(--color-text-1);
}

.sidebar-bottom {
  padding: 16px;
  border-top: 1px solid var(--color-border-2);
}

.user-profile {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 8px 12px;
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.2s;
}

.app-sidebar.collapsed .user-profile {
  justify-content: center;
  padding: 8px 0;
}

.user-profile:hover {
  background-color: var(--color-fill-2);
}

.user-profile.active {
  background-color: var(--color-fill-3);
}

.user-name {
  font-size: 14px;
  font-weight: 500;
  color: var(--color-text-1);
}
</style>
