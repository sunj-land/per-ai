/*
 * @Author: User Profile API
 * @Date: 2026-03-16
 * @Description: User Profile Management API
 */
import request from "@/utils/request";

const BASE_URL = "/v1/profile";

/**
 * Get User Profile
 * @param {Object} [config] - Request configuration
 * @returns {Promise<Object>} User Profile
 */
export const getUserProfile = (config = {}) => {
	return request.get(`${BASE_URL}/`, {
		loading: "profile-get",
		...config,
	});
};

/**
 * Update User Profile
 * @param {Object} data - Update data
 * @param {String} data.identity - Soul Identity
 * @param {String} data.rules - Personal Rules
 * @param {Object} [config] - Request configuration
 * @returns {Promise<Object>} Updated User Profile
 */
export const updateUserProfile = (data, config = {}) => {
	return request.post(`${BASE_URL}/`, data, {
		loading: "profile-update",
		...config,
	});
};

/**
 * Get User Profile History
 * @param {Number} limit - Limit count
 * @param {Object} [config] - Request configuration
 * @returns {Promise<Array>} History List
 */
export const getUserProfileHistory = (limit = 10, config = {}) => {
	return request.get(`${BASE_URL}/history`, {
		params: { limit },
		loading: "profile-history",
		...config,
	});
};
