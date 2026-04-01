<template>
  <div class="user-management">
    <a-card title="用户管理">
      <template #extra>
        <a-space>
          <a-button type="primary" @click="handleAdd">
            <template #icon><icon-plus /></template>
            新增用户
          </a-button>
          <a-button
            status="danger"
            :disabled="!selectedKeys.length"
            @click="handleBatchDelete"
          >
            <template #icon><icon-delete /></template>
            批量删除
          </a-button>
        </a-space>
      </template>

      <!-- 搜索栏 -->
      <a-row :gutter="16" class="search-bar">
        <a-col :span="8">
          <a-input-search
            v-model="searchQuery"
            placeholder="搜索用户名/邮箱/手机号"
            allow-clear
            @search="handleSearch"
            @clear="handleSearch"
          />
        </a-col>
        <a-col :span="6">
          <a-select
            v-model="statusFilter"
            placeholder="用户状态"
            allow-clear
            @change="handleSearch"
          >
            <a-option value="active">正常</a-option>
            <a-option value="locked">锁定</a-option>
            <a-option value="disabled">禁用</a-option>
          </a-select>
        </a-col>
      </a-row>

      <!-- 用户列表 -->
      <a-table
        row-key="id"
        :data="userList"
        :loading="loading"
        :pagination="pagination"
        :row-selection="rowSelection"
        @page-change="handlePageChange"
        @selection-change="handleSelectionChange"
      >
        <template #columns>
          <a-table-column title="ID" data-index="id" :width="80" />
          <a-table-column title="用户名" data-index="username" />
          <a-table-column title="邮箱" data-index="email" />
          <a-table-column title="手机号" data-index="phone" />
          <a-table-column title="角色" data-index="roles">
            <template #cell="{ record }">
              <a-tag
                v-for="role in record.roles"
                :key="role.id"
                color="blue"
                class="role-tag"
              >
                {{ role.name }}
              </a-tag>
            </template>
          </a-table-column>
          <a-table-column title="状态" data-index="status">
            <template #cell="{ record }">
              <a-tag :color="getStatusColor(record.status)">
                {{ getStatusText(record.status) }}
              </a-tag>
            </template>
          </a-table-column>
          <a-table-column title="创建时间" data-index="created_at">
            <template #cell="{ record }">
              {{ formatDate(record.created_at) }}
            </template>
          </a-table-column>
          <a-table-column title="操作" :width="200">
            <template #cell="{ record }">
              <a-space>
                <a-button type="text" size="small" @click="handleEdit(record)">
                  编辑
                </a-button>
                <a-popconfirm
                  content="确定要删除该用户吗？"
                  type="warning"
                  @ok="handleDelete(record)"
                >
                  <a-button
                    type="text"
                    status="danger"
                    size="small"
                    :disabled="isSystemUser(record)"
                  >
                    删除
                  </a-button>
                </a-popconfirm>
              </a-space>
            </template>
          </a-table-column>
        </template>
      </a-table>
    </a-card>

    <!-- 新增/编辑用户弹窗 -->
    <a-modal
      v-model:visible="modalVisible"
      :title="modalTitle"
      @ok="handleModalOk"
      @cancel="handleModalCancel"
      :ok-loading="modalOkLoading"
    >
      <a-form ref="formRef" :model="form" :rules="rules" layout="vertical">
        <a-form-item field="username" label="用户名">
          <a-input v-model="form.username" :disabled="isEdit" placeholder="请输入用户名" />
        </a-form-item>

        <a-form-item
          field="password"
          label="密码"
          :rules="isEdit ? [{ required: false }] : rules.password"
        >
          <a-input-password
            v-model="form.password"
            :placeholder="isEdit ? '留空则不修改密码' : '请输入密码'"
          />
        </a-form-item>

        <a-form-item
          field="confirmPassword"
          label="确认密码"
          :rules="isEdit ? [{ required: false }] : rules.confirmPassword"
          v-if="!isEdit || form.password"
        >
          <a-input-password
            v-model="form.confirmPassword"
            placeholder="请再次输入密码"
          />
        </a-form-item>

        <a-form-item field="email" label="邮箱">
          <a-input v-model="form.email" placeholder="请输入邮箱" />
        </a-form-item>

        <a-form-item field="phone" label="手机号">
          <a-input v-model="form.phone" placeholder="请输入手机号" />
        </a-form-item>

        <a-form-item field="role_ids" label="角色分配">
          <a-select
            v-model="form.role_ids"
            multiple
            placeholder="请选择角色"
          >
            <a-option
              v-for="role in roleList"
              :key="role.id"
              :value="role.id"
            >
              {{ role.name }} ({{ role.description }})
            </a-option>
          </a-select>
        </a-form-item>

        <a-form-item field="status" label="状态" v-if="isEdit">
          <a-select v-model="form.status">
            <a-option value="active">正常</a-option>
            <a-option value="locked">锁定</a-option>
            <a-option value="disabled">禁用</a-option>
          </a-select>
        </a-form-item>
      </a-form>
    </a-modal>
  </div>
</template>

<script setup>
import { Message, Modal } from "@arco-design/web-vue";
import dayjs from "dayjs";
import { computed, onMounted, reactive, ref } from "vue";
import {
	batchDeleteUsers,
	createUser,
	deleteUser,
	getRoles,
	getUsers,
	updateUser,
} from "@/api/user";
import { useLoadingStore } from "@/store/loading";

const loadingStore = useLoadingStore();

// ========== 状态定义 ==========
const _loading = computed(() => loadingStore.isLoading("user-list"));
const userList = ref([]);
const roleList = ref([]);
const pagination = reactive({
	current: 1,
	pageSize: 10,
	total: 0,
	showTotal: true,
});
const searchQuery = ref("");
const statusFilter = ref("");
const selectedKeys = ref([]);

// 弹窗状态
const modalVisible = ref(false);
const _modalOkLoading = computed(
	() =>
		loadingStore.isLoading("user-create") ||
		loadingStore.isLoading("user-update"),
);
const isEdit = ref(false);
const formRef = ref(null);
const currentId = ref(null);

// 表单数据
const form = reactive({
	username: "",
	password: "",
	confirmPassword: "",
	email: "",
	phone: "",
	role_ids: [],
	status: "active",
});

// 表单校验规则
const _rules = {
	username: [
		{ required: true, message: "请输入用户名" },
		{ min: 3, max: 20, message: "用户名长度在 3 到 20 个字符" },
	],
	password: [
		{ required: true, message: "请输入密码" },
		{ min: 6, message: "密码长度至少 6 位" },
	],
	confirmPassword: [
		{ required: true, message: "请确认密码" },
		{
			validator: (value, cb) => {
				if (value !== form.password) {
					cb("两次输入的密码不一致");
				} else {
					cb();
				}
			},
		},
	],
	email: [{ type: "email", message: "请输入有效的邮箱地址" }],
	role_ids: [{ required: true, message: "请至少选择一个角色" }],
};

// 表格选择配置
const _rowSelection = {
	type: "checkbox",
	showCheckedAll: true,
};

// 计算属性
const _modalTitle = computed(() => (isEdit.value ? "编辑用户" : "新增用户"));

// ========== 方法定义 ==========

/**
 * 获取用户列表
 */
const fetchUsers = async () => {
	// loading state handled by store via 'user-list' key
	try {
		const params = {
			skip: (pagination.current - 1) * pagination.pageSize,
			limit: pagination.pageSize,
			query: searchQuery.value || undefined,
			status: statusFilter.value || undefined,
		};
		const { items, total } = await getUsers(params);
		userList.value = items;
		pagination.total = total;
	} catch (_error) {
		// Error handled by interceptor
	} finally {
		// loading handled by store
	}
};

/**
 * 获取角色列表
 */
const fetchRoles = async () => {
	try {
		const roles = await getRoles();
		roleList.value = roles;
	} catch (error) {
		console.error("Failed to fetch roles", error);
	}
};

/**
 * 搜索处理
 */
const _handleSearch = () => {
	pagination.current = 1;
	fetchUsers();
};

/**
 * 分页切换
 */
const _handlePageChange = (page) => {
	pagination.current = page;
	fetchUsers();
};

/**
 * 表格选择
 */
const _handleSelectionChange = (rowKeys) => {
	selectedKeys.value = rowKeys;
};

/**
 * 格式化日期
 */
const _formatDate = (date) => {
	return dayjs(date).format("YYYY-MM-DD HH:mm:ss");
};

/**
 * 获取状态颜色
 */
const _getStatusColor = (status) => {
	const colors = {
		active: "green",
		locked: "orange",
		disabled: "red",
	};
	return colors[status] || "gray";
};

/**
 * 获取状态文本
 */
const _getStatusText = (status) => {
	const texts = {
		active: "正常",
		locked: "锁定",
		disabled: "禁用",
	};
	return texts[status] || status;
};

/**
 * 判断是否为系统关键用户
 */
const _isSystemUser = (record) => {
	return record.id === 1 || record.username === "admin";
};

/**
 * 打开新增弹窗
 */
const _handleAdd = () => {
	isEdit.value = false;
	currentId.value = null;
	resetForm();
	modalVisible.value = true;
};

/**
 * 打开编辑弹窗
 */
const _handleEdit = (record) => {
	isEdit.value = true;
	currentId.value = record.id;
	Object.assign(form, {
		username: record.username,
		email: record.email,
		phone: record.phone,
		role_ids: record.roles.map((r) => r.id),
		status: record.status,
		password: "",
		confirmPassword: "",
	});
	modalVisible.value = true;
};

/**
 * 重置表单
 */
const resetForm = () => {
	Object.assign(form, {
		username: "",
		password: "",
		confirmPassword: "",
		email: "",
		phone: "",
		role_ids: [],
		status: "active",
	});
	if (formRef.value) {
		formRef.value.clearValidate();
	}
};

/**
 * 弹窗确认
 */
const _handleModalOk = async () => {
	const res = await formRef.value.validate();
	if (res) return; // Validation failed

	try {
		if (isEdit.value) {
			const updateData = { ...form };
			if (!updateData.password) {
				delete updateData.password;
				delete updateData.confirmPassword;
			}
			await updateUser(currentId.value, updateData);
			Message.success("用户更新成功");
		} else {
			await createUser(form);
			Message.success("用户创建成功");
		}
		modalVisible.value = false;
		fetchUsers();
	} catch (_error) {
		// Error handled by interceptor
	}
};

/**
 * 弹窗取消
 */
const _handleModalCancel = () => {
	modalVisible.value = false;
	resetForm();
};

/**
 * 单个删除
 */
const _handleDelete = async (record) => {
	try {
		await deleteUser(record.id);
		Message.success("删除成功");
		fetchUsers();
	} catch (_error) {
		// Error handled by interceptor
	}
};

/**
 * 批量删除
 */
const _handleBatchDelete = () => {
	Modal.warning({
		title: "确认删除",
		content: `确定要删除选中的 ${selectedKeys.value.length} 个用户吗？此操作不可恢复。`,
		onOk: async () => {
			try {
				await batchDeleteUsers(selectedKeys.value);
				Message.success("批量删除成功");
				selectedKeys.value = [];
				fetchUsers();
			} catch (_error) {
				// Error handled by interceptor
			}
		},
	});
};

// ========== 生命周期 ==========
onMounted(() => {
	fetchUsers();
	fetchRoles();
});
</script>

<style scoped>
.user-management {
  padding: 20px;
}

.search-bar {
  margin-bottom: 20px;
}

.role-tag {
  margin-right: 5px;
}
</style>
