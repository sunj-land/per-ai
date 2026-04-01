/*
 * @Author: Channel API
 * @Date: 2026-03-16
 * @Description: Channel Management API
 */
import request from "@/utils/request";

const BASE_URL = "/v1/channels";

/**
 * Get Channel List
 * @param {Object} params - Query parameters
 * @param {Number} params.skip - Skip count
 * @param {Number} params.limit - Limit count
 * @param {Object} [config] - Request configuration
 * @returns {Promise<Array>} Channel List
 */
export const getChannels = (params = {}, config = {}) => {
	return request.get(`${BASE_URL}/`, {
		params,
		loading: "channel-list",
		...config,
	});
};

/**
 * Create Channel
 * @param {Object} data - Channel data
 * @param {Object} [config] - Request configuration
 * @returns {Promise<Object>} Created Channel
 */
export const createChannel = (data, config = {}) => {
	return request.post(`${BASE_URL}/`, data, {
		loading: "channel-create",
		...config,
	});
};

/**
 * Update Channel
 * @param {String} id - Channel ID
 * @param {Object} data - Updated data
 * @param {Object} [config] - Request configuration
 * @returns {Promise<Object>} Updated Channel
 */
export const updateChannel = (id, data, config = {}) => {
	return request.put(`${BASE_URL}/${id}`, data, {
		loading: "channel-update",
		...config,
	});
};

/**
 * Delete Channel
 * @param {String} id - Channel ID
 * @param {Object} [config] - Request configuration
 * @returns {Promise<Boolean>} Success status
 */
export const deleteChannel = (id, config = {}) => {
	return request.delete(`${BASE_URL}/${id}`, {
		loading: "channel-delete",
		...config,
	});
};

/**
 * Send Message
 * @param {String} id - Channel ID
 * @param {Object} data - Message content { content, title }
 * @param {Object} [config] - Request configuration
 * @returns {Promise<Object>} Message record
 */
export const sendMessage = (id, data, config = {}) => {
	return request.post(`${BASE_URL}/${id}/send`, data, {
		loading: "channel-send",
		silent: true, // Suppress global error message to handle it locally in components
		...config,
	});
};

/**
 * Get Channel Message History
 * @param {String} id - Channel ID
 * @param {Object} params - Query parameters { skip, limit }
 * @param {Object} [config] - Request configuration
 * @returns {Promise<Array>} Message list
 */
export const getChannelMessages = (id, params = {}, config = {}) => {
	return request.get(`${BASE_URL}/${id}/messages`, {
		params,
		loading: "channel-messages",
		...config,
	});
};

/**
 * Get Global Messages (Search)
 * @param {Object} params - Query parameters
 * @param {Object} [config] - Request configuration
 * @returns {Promise<Object>} Message list { items, total }
 */
export const getMessages = (params = {}, config = {}) => {
	return request.get(`${BASE_URL}/messages`, {
		params,
		loading: "message-search",
		...config,
	});
};
