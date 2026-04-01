import request from "@/utils/request";

const BASE_URL = "/v1/rss";

const unwrapResponse = (payload) => {
	if (
		payload &&
		typeof payload === "object" &&
		Object.hasOwn(payload, "code")
	) {
		if (payload.code !== 0) {
			throw new Error(payload.msg || "请求失败");
		}
		return payload.data;
	}
	return payload;
};

/**
 * 获取所有订阅源
 */
export const getFeeds = async (config = {}) => {
	const res = await request.get(`${BASE_URL}/feeds`, {
		loading: "rss-feeds",
		...config,
	});
	return unwrapResponse(res);
};

/**
 * 添加订阅源
 */
export const addFeed = async (urlOrData, groupIdsIfUrl = null, config = {}) => {
	let data;
	if (typeof urlOrData === "string") {
		data = { url: urlOrData };
		if (groupIdsIfUrl) {
			data.group_ids = groupIdsIfUrl;
		}
	} else {
		data = urlOrData;
	}
	const res = await request.post(`${BASE_URL}/feeds`, data, config);
	return unwrapResponse(res);
};

/**
 * 导入 OPML
 */
export const importOpml = async (content, config = {}) => {
	const res = await request.post(`${BASE_URL}/feeds/import`, { content }, config);
	return unwrapResponse(res);
};

/**
 * 刷新所有订阅源
 */
export const refreshFeeds = async (config = {}) => {
	const res = await request.post(
		`${BASE_URL}/feeds/refresh`,
		{},
		{
			loading: "rss-refresh",
			...config,
		},
	);
	return unwrapResponse(res);
};

/**
 * 刷新单个订阅源
 */
export const refreshFeed = async (feedId, config = {}) => {
	const res = await request.post(`${BASE_URL}/feeds/${feedId}/refresh`, {}, config);
	return unwrapResponse(res);
};

/**
 * 更新订阅源
 */
export const updateFeed = async (feedId, data, config = {}) => {
	const res = await request.post(`${BASE_URL}/feeds/${feedId}/update`, data, config);
	return unwrapResponse(res);
};

/**
 * 删除订阅源
 */
export const deleteFeed = async (feedId, config = {}) => {
	const res = await request.post(`${BASE_URL}/feeds/${feedId}/delete`, {}, config);
	return unwrapResponse(res);
};

/**
 * 批量删除订阅源
 */
export const batchDeleteFeeds = async (feedIds, config = {}) => {
	const res = await request.post(
		`${BASE_URL}/feeds/batch_delete`,
		{ feed_ids: feedIds },
		config,
	);
	return unwrapResponse(res);
};

/**
 * 清理抓取失败的订阅源
 */
export const cleanupFailedFeeds = async (config = {}) => {
	const res = await request.post(`${BASE_URL}/feeds/cleanup_failed`, {}, config);
	return unwrapResponse(res);
};

// ==========================================
// 分组管理 API
// ==========================================

/**
 * 获取所有分组
 */
export const getGroups = async (parentId = null, config = {}) => {
	const params = parentId ? { parent_id: parentId } : {};
	const res = await request.get(`${BASE_URL}/groups`, {
		params,
		loading: "rss-groups",
		...config,
	});
	return unwrapResponse(res);
};

/**
 * 创建分组
 */
export const createGroup = async (name, parentId = null, config = {}) => {
	const res = await request.post(
		`${BASE_URL}/groups`,
		{ name, parent_id: parentId },
		config,
	);
	return unwrapResponse(res);
};

/**
 * 更新分组
 */
export const updateGroup = async (groupId, data, config = {}) => {
	const res = await request.post(`${BASE_URL}/groups/${groupId}/update`, data, config);
	return unwrapResponse(res);
};

/**
 * 删除分组
 */
export const deleteGroup = async (groupId, config = {}) => {
	const res = await request.post(`${BASE_URL}/groups/${groupId}/delete`, {}, config);
	return unwrapResponse(res);
};

/**
 * 移动分组
 */
export const moveGroup = async (groupId, parentId, config = {}) => {
	const res = await request.post(
		`${BASE_URL}/groups/${groupId}/move`,
		{ parent_id: parentId },
		config,
	);
	return unwrapResponse(res);
};

// ==========================================
// 文章管理 API
// ==========================================

/**
 * 获取文章列表
 */
export const getArticles = async (params = {}, config = {}) => {
	const res = await request.get(`${BASE_URL}/articles`, {
		params,
		loading: "rss-articles",
		...config,
	});
	return unwrapResponse(res);
};

/**
 * 获取单篇文章详情
 */
export const getArticle = async (id, config = {}) => {
	const res = await request.get(`${BASE_URL}/articles/${id}`, config);
	return unwrapResponse(res);
};

/**
 * 标记文章已读/未读
 */
export const markRead = async (articleIds, isRead = true, config = {}) => {
	const res = await request.post(
		`${BASE_URL}/articles/mark_read`,
		{ article_ids: articleIds, is_read: isRead },
		config,
	);
	return unwrapResponse(res);
};

/**
 * 标记所有文章已读
 */
export const markAllRead = async (
	feedId = null,
	groupId = null,
	config = {},
) => {
	const data = {};
	if (feedId) data.feed_id = feedId;
	if (groupId) data.group_id = groupId;
	const res = await request.post(`${BASE_URL}/articles/mark_all_read`, data, config);
	return unwrapResponse(res);
};

/**
 * 收藏/取消收藏文章
 */
export const toggleStar = async (articleIds, isStarred = true, config = {}) => {
	const res = await request.post(
		`${BASE_URL}/articles/star`,
		{ article_ids: articleIds, is_starred: isStarred },
		config,
	);
	return unwrapResponse(res);
};

// ==========================================
// 缺失的函数补充 (基于 RSSFeeds.vue 的调用)
// ==========================================

/**
 * 获取分组树
 */
export const getGroupsTree = async (config = {}) => {
	const res = await request.get(`${BASE_URL}/groups/tree`, {
		loading: "rss-groups-tree",
		...config,
	});
	return unwrapResponse(res);
};

/**
 * 设置订阅源分组
 */
export const setFeedGroups = async (feedId, groupIds, config = {}) => {
	const res = await request.post(
		`${BASE_URL}/feeds/${feedId}/groups`,
		groupIds,
		config,
	);
	return unwrapResponse(res);
};

/**
 * 获取清理候选列表
 */
export const getCleanupCandidates = async (threshold = 3, config = {}) => {
	const res = await request.post(
		`${BASE_URL}/cleanup/candidates`,
		{ threshold },
		{
			loading: "rss-cleanup-candidates",
			...config,
		},
	);
	return unwrapResponse(res);
};

/**
 * 执行清理
 */
export const executeCleanup = async (feedIds, config = {}) => {
	const res = await request.post(
		`${BASE_URL}/cleanup/execute`,
		{ feed_ids: feedIds },
		{
			loading: "rss-cleanup-execute",
			...config,
		},
	);
	return unwrapResponse(res);
};

/**
 * 智能分类
 */
export const autoClassifyFeeds = async (config = {}) => {
	const res = await request.post(
		`${BASE_URL}/feeds/auto_classify`,
		{},
		{
			loading: "rss-auto-classify",
			...config,
		},
	);
	return unwrapResponse(res);
};
