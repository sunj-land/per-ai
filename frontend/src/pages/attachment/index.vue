<template>
  <div class="attachment-center">
    <a-card title="附件中心" :bordered="false" class="card-container">
      <!-- Header -->
      <div class="header">
        <a-space>
          <a-upload
            action="#"
            :custom-request="customUpload"
            :show-file-list="false"
            multiple
          >
            <template #upload-button>
              <a-button type="primary" :loading="loadingStore.isLoading('attachment-upload')">
                <template #icon><icon-upload /></template>
                上传附件
              </a-button>
            </template>
          </a-upload>
        </a-space>
        <a-space>
          <a-input-search
            v-model="searchParams.keyword"
            placeholder="搜索文件名"
            @search="fetchData"
            @press-enter="fetchData"
            style="width: 260px"
          />
        </a-space>
      </div>

      <!-- Table -->
      <a-table
        :data="data"
        :pagination="pagination"
        @page-change="onPageChange"
        row-key="uuid"
        :loading="loadingStore.isLoading('attachment-list')"
        style="margin-top: 16px"
      >
        <template #columns>
          <a-table-column title="缩略图" width="100" align="center">
            <template #cell="{ record }">
              <a-image
                v-if="record.mime_type && record.mime_type.startsWith('image/') && record.size < 1024 * 1024"
                :src="getPreviewUrl(record.uuid)"
                width="60"
                height="60"
                fit="cover"
                style="border-radius: 4px; cursor: pointer"
              />
              <div v-else style="color: #c9cdd4; display: flex; align-items: center; justify-content: center; width: 60px; height: 60px; background: #f2f3f5; border-radius: 4px;">
                <icon-file size="24" />
              </div>
            </template>
          </a-table-column>
          <a-table-column title="文件名" data-index="original_name" />
          <a-table-column title="类型" data-index="mime_type" width="200" />
          <a-table-column title="大小" width="120">
            <template #cell="{ record }">{{ formatSize(record.size) }}</template>
          </a-table-column>
          <a-table-column title="上传时间" data-index="created_at" width="180">
            <template #cell="{ record }">{{ new Date(record.created_at).toLocaleString() }}</template>
          </a-table-column>
          <a-table-column title="操作" width="200">
            <template #cell="{ record }">
              <a-space>
                <a-button type="text" size="small" @click="handlePreview(record)">预览</a-button>
                <a-button type="text" size="small" @click="handleDownload(record)">下载</a-button>
                <a-popconfirm content="确定删除该附件吗？" @ok="handleDelete(record)">
                  <a-button type="text" status="danger" size="small" :loading="loadingStore.isLoading('attachment-delete')">删除</a-button>
                </a-popconfirm>
              </a-space>
            </template>
          </a-table-column>
        </template>
      </a-table>
    </a-card>

    <!-- Preview Modal -->
    <a-modal
      v-model:visible="previewVisible"
      title="预览"
      fullscreen
      :footer="false"
      unmount-on-close
    >
      <div class="preview-container">
        <iframe
          v-if="previewUrl"
          :src="previewUrl"
          frameborder="0"
          style="width: 100%; height: 100%;"
        ></iframe>
      </div>
    </a-modal>
  </div>
</template>

<script setup>
import { Message } from "@arco-design/web-vue";
import { onMounted, reactive, ref } from "vue";
import {
	deleteAttachment,
	getDownloadUrl,
	getPreviewUrl,
	searchAttachments,
	uploadAttachment,
} from "@/api/attachment";
import { useLoadingStore } from "@/store/loading";

const loadingStore = useLoadingStore();
const data = ref([]);
const pagination = reactive({
	current: 1,
	pageSize: 20,
	total: 0,
	showTotal: true,
});
const searchParams = reactive({ keyword: "" });
const previewVisible = ref(false);
const previewUrl = ref("");

const fetchData = async () => {
	try {
		const res = await searchAttachments({
			keyword: searchParams.keyword,
			offset: (pagination.current - 1) * pagination.pageSize,
			limit: pagination.pageSize,
		});
		// Assuming API returns List[Attachment] for now.
		data.value = res;
	} catch (_err) {
		// handled by interceptor
	}
};

const customUpload = async (option) => {
	const { fileItem, onSuccess, onError } = option;
	const formData = new FormData();
	formData.append("file", fileItem.file);
	try {
		await uploadAttachment(formData);
		Message.success("上传成功");
		onSuccess();
		fetchData();
	} catch (err) {
		onError(err);
	}
};

const handlePreview = (record) => {
	previewUrl.value = getPreviewUrl(record.uuid);
	previewVisible.value = true;
};

const handleDownload = (record) => {
	window.open(getDownloadUrl(record.uuid), "_blank");
};

const handleDelete = async (record) => {
	await deleteAttachment(record.uuid);
	Message.success("删除成功");
	fetchData();
};

const formatSize = (bytes) => {
	if (bytes === 0) return "0 B";
	const k = 1024;
	const sizes = ["B", "KB", "MB", "GB"];
	const i = Math.floor(Math.log(bytes) / Math.log(k));
	return `${parseFloat((bytes / k ** i).toFixed(2))} ${sizes[i]}`;
};

const onPageChange = (page) => {
	pagination.current = page;
	fetchData();
};

onMounted(() => {
	fetchData();
});
</script>

<style scoped>
.attachment-center {
  padding: 20px;
  height: 100%;
}
.header {
  display: flex;
  justify-content: space-between;
  margin-bottom: 16px;
}
.preview-container {
  width: 100%;
  height: calc(100vh - 100px);
}
</style>
