<template>
  <div class="card-center">
    <!-- ========== 左侧边栏：卡片列表 ========== -->
    <div class="sidebar">
      <div class="sidebar-header">
        <h3>卡片中心</h3>
        <a-button type="primary" long @click="createNew">
          <template #icon><icon-plus /></template>
          新建卡片
        </a-button>
      </div>
      <a-list :data="cards" hoverable :loading="loadingStore.isLoading('card-list')">
        <template #item="{ item }">
          <a-list-item
            :class="{ active: currentCard?.id === item.id }"
            @click="selectCard(item)"
          >
            <a-list-item-meta :title="item.name" :description="item.type">
              <template #avatar>
                <a-tag color="arcoblue">{{ item.id }}</a-tag>
              </template>
            </a-list-item-meta>
          </a-list-item>
        </template>
      </a-list>
    </div>

    <!-- ========== 主内容区：卡片编辑工作区 ========== -->
    <div class="main-content">
      <div v-if="currentCard || isCreating" class="workspace">
        <!-- 工具栏 -->
        <a-page-header
          :title="isCreating ? '新建卡片' : currentCard.name"
          :subtitle="isCreating ? '草稿' : `v${currentCard.version}`"
          :show-back="false"
        >
          <template #extra>
            <a-space>
              <a-button @click="loadCards"><template #icon><icon-refresh /></template></a-button>
              <a-button type="primary" @click="saveCard" :loading="isSaving">保存版本</a-button>
              <a-popconfirm content="此操作将代码写入源文件目录，确定继续？" @ok="publish">
                <a-button v-if="currentCard && !isCreating" status="success" :loading="loadingStore.isLoading('card-publish')">发布到应用</a-button>
              </a-popconfirm>
            </a-space>
          </template>
        </a-page-header>

        <!-- 卡片基本信息表单 -->
        <a-form :model="cardForm" layout="inline" class="card-form">
          <a-form-item field="name" label="名称">
            <a-input v-model="cardForm.name" placeholder="例如：产品卡片" />
          </a-form-item>
          <a-form-item field="type" label="类型">
            <a-select v-model="cardForm.type" placeholder="选择类型" style="width: 150px">
              <a-option value="custom">自定义</a-option>
              <a-option value="chart">图表</a-option>
              <a-option value="table">表格</a-option>
              <a-option value="form">表单</a-option>
            </a-select>
          </a-form-item>
        </a-form>

        <!-- AI 代码生成器 -->
        <a-card title="AI 代码生成器" class="ai-panel">
          <div class="ai-input-group">
            <a-textarea
              v-model="prompt"
              placeholder="描述你想要的卡片（例如：'一个带有图片、标题、价格和购买按钮的产品卡片'）"
              :auto-size="{ minRows: 2, maxRows: 4 }"
              style="flex: 1"
            />
            <a-button type="primary" status="warning" :loading="loadingStore.isLoading('card-generate')" @click="generate">
              <template #icon><icon-robot /></template>
              生成代码
            </a-button>
          </div>
        </a-card>

        <!-- 代码编辑与实时预览 -->
        <div class="preview-area">
          <!-- 代码编辑面板 -->
          <div class="panel code-panel">
            <div class="panel-header">Vue 代码</div>
            <a-textarea
              v-model="code"
              class="code-editor"
              placeholder="<template>..."
            />
            <div class="panel-header" style="border-top: 1px solid #e5e6eb; display: flex; justify-content: space-between; align-items: center;">
              <span>模拟数据 (JSON)</span>
              <a-button type="text" size="small" @click="autoGenerateMockData">
                <template #icon><icon-magic /></template> 自动生成
              </a-button>
            </div>
            <a-textarea
              v-model="mockDataStr"
              class="code-editor"
              style="height: 200px; flex: none;"
              placeholder="{}"
            />
          </div>
          <!-- 实时预览面板 -->
          <div class="panel preview-panel">
            <div class="panel-header">实时预览</div>
            <div class="preview-container">
              <DynamicCardPreview :code="code" :component-props="parsedMockData" />
            </div>
          </div>
        </div>
      </div>

      <!-- 空状态提示 -->
      <div v-else class="empty-state">
        <a-empty description="从侧边栏选择一个卡片或创建新卡片" />
      </div>
    </div>
  </div>
</template>

<script setup>
/*
 * @Author: 项目规范
 * @Date: 2024-03-25
 * @Description: 卡片中心主页面，支持卡片列表管理、AI 代码生成、版本保存和发布功能
 */
import { Message } from "@arco-design/web-vue";
import { computed, onMounted, reactive, ref } from "vue";
import {
  createCard,
  createVersion,
  generateCardCode,
  getCards,
  getVersions,
  publishCard,
  updateCard,
} from "@/api/card-center";
import { useLoadingStore } from "@/store/loading";
import DynamicCardPreview from "@/components/cards/DynamicCardPreview.vue";

// ========== 加载状态管理 ==========
const loadingStore = useLoadingStore();

// ========== 响应式数据 ==========
const cards = ref([]);
const currentCard = ref(null);
const isCreating = ref(false);
const prompt = ref("");
const code = ref(
  '<template>\n  <a-card title="New Card">\n    Content\n  </a-card>\n</template>',
);
const mockDataStr = ref('{}');

// ========== 计算属性 ==========
const parsedMockData = computed(() => {
  try {
    return JSON.parse(mockDataStr.value || '{}');
  } catch (e) {
    return {};
  }
});

// 保存操作是否处于加载中状态
const isSaving = computed(
  () =>
    loadingStore.isLoading("card-create") ||
    loadingStore.isLoading("card-update") ||
    loadingStore.isLoading("card-versions") ||
    loadingStore.isLoading("card-version-create"),
);

// ========== 卡片表单数据 ==========
const cardForm = reactive({
  name: "",
  type: "custom",
  description: "",
});

/**
 * 从服务器加载卡片列表
 */
const loadCards = async () => {
  try {
    cards.value = await getCards();
  } catch (e) {
    Message.error(`加载卡片失败: ${e.message}`);
  }
};

/**
 * 选择卡片并加载其最新版本代码
 * @param {Object} card - 选中的卡片对象
 */
const selectCard = async (card) => {
  currentCard.value = card;
  isCreating.value = false;
  cardForm.name = card.name;
  cardForm.type = card.type;

  try {
    const versions = await getVersions(card.id);
    if (versions && versions.length > 0) {
      versions.sort((a, b) => b.version - a.version);
      code.value = versions[0].code;
      setTimeout(autoGenerateMockData, 100);
    } else {
      code.value = '<template>\n  <a-empty description="未找到代码版本" />\n</template>';
      mockDataStr.value = '{}';
    }
  } catch (e) {
    Message.error(`加载版本失败: ${e.message}`);
  }
};

/**
 * 创建新卡片（重置表单和编辑器状态）
 */
const createNew = () => {
  currentCard.value = null;
  isCreating.value = true;
  cardForm.name = "";
  cardForm.type = "custom";
  code.value = '<template>\n  <a-card title="New Card">\n    Content\n  </a-card>\n</template>';
};

/**
 * 根据代码中的 defineProps 自动生成模拟数据
 */
const autoGenerateMockData = () => {
  const propsMatch = code.value.match(/defineProps\(\s*(\{[\s\S]*?\})\s*\)/);
  if (!propsMatch) {
    Message.info("代码中未找到 defineProps，无法自动生成模拟数据");
    return;
  }
  try {
    const propsStr = propsMatch[1];
    const props = {};
    const regex = /([a-zA-Z0-9_]+)\s*:\s*(\{[^}]*\}|[a-zA-Z]+)/g;
    let match;
    while ((match = regex.exec(propsStr)) !== null) {
      const key = match[1];
      const valStr = match[2];

      if (valStr.includes('String')) {
        if (key.toLowerCase().includes('image') || key.toLowerCase().includes('url') || key.toLowerCase().includes('thumbnail') || key.toLowerCase().includes('avatar')) {
          props[key] = "https://p1-arco.byteimg.com/tos-cn-i-uwbnlip3yd/a8c8cdb109cb051163646151a4a5083b.png~tplv-uwbnlip3yd-webp.webp";
        } else if (key.toLowerCase().includes('date') || key.toLowerCase().includes('time')) {
          props[key] = new Date().toISOString().split('T')[0];
        } else {
          props[key] = `Mock ${key}`;
        }
      }
      else if (valStr.includes('Number')) props[key] = 100;
      else if (valStr.includes('Boolean')) props[key] = true;
      else if (valStr.includes('Array')) props[key] = ["Item 1", "Item 2", "Item 3"];
      else if (valStr.includes('Object')) props[key] = { id: 1, name: "Mock Object" };
      else props[key] = `Mock ${key}`;
    }
    mockDataStr.value = JSON.stringify(props, null, 2);
    Message.success("模拟数据生成成功!");
  } catch(e) {
    Message.error("解析 props 失败");
  }
};

/**
 * 通过 AI 生成卡片代码
 */
const generate = async () => {
  if (!prompt.value) return;
  try {
    const res = await generateCardCode(prompt.value, { provider: "ollama" });
    if (res.code) {
      code.value = res.code;
      Message.success("代码生成成功!");
    }
  } catch (e) {
    Message.error(`生成失败: ${e.message}`);
  }
};

/**
 * 保存卡片（创建新卡片或更新现有卡片）及其新版本
 */
const saveCard = async () => {
  try {
    let card;
    if (isCreating.value) {
      card = await createCard(cardForm);
      isCreating.value = false;
      currentCard.value = card;
      cards.value.push(card);
    } else {
      card = await updateCard(currentCard.value.id, cardForm);
    }

    // 获取最新版本号
    const versions = await getVersions(card.id);
    const latestVersion = versions.length > 0 ? Math.max(...versions.map((v) => v.version)) : 0;
    const nextVersion = latestVersion + 1;

    // 创建新版本
    await createVersion(card.id, {
      version: nextVersion,
      code: code.value,
      changelog: "通过卡片中心更新",
    });

    // 更新本地状态
    currentCard.value.version = nextVersion;

    Message.success(`版本 ${nextVersion} 保存成功`);
    loadCards();
  } catch (e) {
    Message.error(`保存失败: ${e.message}`);
  }
};

/**
 * 发布卡片到前端源文件目录
 */
const publish = async () => {
  if (!currentCard.value) return;
  try {
    await publishCard(currentCard.value.id, currentCard.value.version);
    Message.success("发布成功！如有新文件创建，请重启开发服务器");
  } catch (e) {
    Message.error(`发布失败: ${e.message}`);
  }
};

// ========== 生命周期 ==========
onMounted(loadCards);
</script>

<style scoped>
/* ========== 整体布局 ========== */
.card-center {
  display: flex;
  height: 100vh;
  background: #f2f3f5;
}

/* ========== 左侧边栏 ========== */
.sidebar {
  width: 300px;
  background: #fff;
  border-right: 1px solid #e5e6eb;
  display: flex;
  flex-direction: column;
}

.sidebar-header {
  padding: 16px;
  border-bottom: 1px solid #e5e6eb;
}

.sidebar-header h3 {
  margin: 0 0 16px 0;
}

/* ========== 主内容区 ========== */
.main-content {
  flex: 1;
  padding: 16px;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

/* ========== 工作区 ========== */
.workspace {
  display: flex;
  flex-direction: column;
  height: 100%;
  gap: 16px;
}

/* ========== 表单 ========== */
.card-form {
  background: #fff;
  padding: 16px;
  border-radius: 4px;
}

/* ========== AI 生成面板 ========== */
.ai-panel {
  border-radius: 4px;
}

.ai-input-group {
  display: flex;
  gap: 12px;
}

/* ========== 预览区域 ========== */
.preview-area {
  display: flex;
  flex: 1;
  gap: 16px;
  min-height: 0;
}

/* ========== 代码/预览面板 ========== */
.panel {
  flex: 1;
  background: #fff;
  border-radius: 4px;
  display: flex;
  flex-direction: column;
  border: 1px solid #e5e6eb;
}

.panel-header {
  padding: 12px;
  border-bottom: 1px solid #e5e6eb;
  font-weight: bold;
  background: #fafafa;
}

.code-editor {
  flex: 1;
  font-family: monospace;
  height: 100%;
  border: none;
  resize: none;
}

.code-editor :deep(.arco-textarea) {
  height: 100%;
  border: none;
  border-radius: 0;
}

.preview-container {
  flex: 1;
  padding: 16px;
  overflow: auto;
}

/* ========== 空状态 ========== */
.empty-state {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 100%;
  color: #86909c;
}

/* ========== 选中状态 ========== */
.active {
  background-color: var(--color-primary-light-1);
}
</style>
