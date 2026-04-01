import request from "../utils/request";

const BASE_URL = "/v1/tasks";

export const getTasks = async (config = {}) => {
	return request.get(BASE_URL, {
		loading: "task-list",
		...config,
	});
};

export const createTask = async (data, config = {}) => {
	return request.post(BASE_URL, data, {
		loading: "task-create",
		...config,
	});
};

export const updateTask = async (id, data, config = {}) => {
	return request.put(`${BASE_URL}/${id}`, data, {
		loading: "task-update",
		...config,
	});
};

export const deleteTask = async (id, config = {}) => {
	return request.delete(`${BASE_URL}/${id}`, {
		loading: "task-delete",
		...config,
	});
};

export const runTask = async (id, config = {}) => {
	return request.post(`${BASE_URL}/${id}/run`, null, {
		loading: `task-run-${id}`,
		...config,
	});
};

export const pauseTask = async (id, config = {}) => {
	return request.post(`${BASE_URL}/${id}/pause`, null, {
		loading: `task-status-${id}`,
		...config,
	});
};

export const resumeTask = async (id, config = {}) => {
	return request.post(`${BASE_URL}/${id}/resume`, null, {
		loading: `task-status-${id}`,
		...config,
	});
};

export const getTaskLogs = async (id, limit = 20, config = {}) => {
	return request.get(`${BASE_URL}/${id}/logs`, {
		params: { limit },
		loading: "task-logs",
		...config,
	});
};
