/*
 * @Author: Project Rules
 * @Date: 2024-03-14
 * @Description: User Management API
 */
import request from "@/utils/request";

const BASE_URL = "/v1/users";

/**
 * Get user list
 * @param {Object} params - { skip, limit, query, status }
 * @param {Object} [config]
 * @returns {Promise} { items: [], total: 0 }
 */
export const getUsers = (params, config = {}) =>
	request.get(`${BASE_URL}/`, {
		params,
		loading: "user-list",
		...config,
	});

/**
 * Create user
 * @param {Object} data - { username, password, email, phone, role_ids, status }
 * @param {Object} [config]
 * @returns {Promise} User object
 */
export const createUser = (data, config = {}) =>
	request.post(`${BASE_URL}/`, data, {
		loading: "user-create",
		...config,
	});

/**
 * Update user
 * @param {Number} id
 * @param {Object} data - { email, phone, role_ids, status, password (optional) }
 * @param {Object} [config]
 * @returns {Promise} User object
 */
export const updateUser = (id, data, config = {}) =>
	request.put(`${BASE_URL}/${id}`, data, {
		loading: "user-update",
		...config,
	});

/**
 * Delete user
 * @param {Number} id
 * @param {Object} [config]
 * @returns {Promise}
 */
export const deleteUser = (id, config = {}) =>
	request.delete(`${BASE_URL}/${id}`, {
		loading: "user-delete",
		...config,
	});

/**
 * Batch delete users
 * @param {Array<Number>} ids
 * @param {Object} [config]
 * @returns {Promise}
 */
export const batchDeleteUsers = (ids, config = {}) =>
	request.delete(`${BASE_URL}/`, {
		params: { user_ids: ids },
		loading: "user-batch-delete",
		...config,
	});

/**
 * Get all roles
 * @param {Object} [config]
 * @returns {Promise} List of roles
 */
export const getRoles = (config = {}) =>
	request.get(`${BASE_URL}/roles`, {
		loading: false,
		...config,
	});
