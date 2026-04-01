import request from "../utils/request";

const BASE_URL = "/v1/schedules";

export const getSchedules = async (params = {}, config = {}) => {
	return request.get(BASE_URL, {
		params,
		loading: "schedule-list",
		...config,
	});
};

export const getSchedule = async (id, config = {}) => {
	return request.get(`${BASE_URL}/${id}`, {
		loading: "schedule-detail",
		...config,
	});
};

export const createSchedule = async (data, config = {}) => {
	return request.post(BASE_URL, data, {
		loading: "schedule-create",
		...config,
	});
};

export const updateSchedule = async (id, data, config = {}) => {
	return request.put(`${BASE_URL}/${id}`, data, {
		loading: "schedule-update",
		...config,
	});
};

export const deleteSchedule = async (id, config = {}) => {
	return request.delete(`${BASE_URL}/${id}`, {
		loading: "schedule-delete",
		...config,
	});
};

export const getScheduleReminders = async (id, config = {}) => {
	return request.get(`${BASE_URL}/${id}/reminders`, {
		loading: "schedule-reminders",
		...config,
	});
};
