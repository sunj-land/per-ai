import request from "../utils/request";

const BASE_URL = "/v1/plans";

export const generatePlan = async (goalText, config = {}) => {
	return request.post(`${BASE_URL}/generate`, null, {
		params: { goal_text: goalText },
		loading: "plan-generate",
		timeout: 120000, // Generation might take time
		...config,
	});
};

export const createPlan = async (planData, config = {}) => {
	return request.post(BASE_URL, planData, {
		loading: "plan-create",
		...config,
	});
};

export const listPlans = async (config = {}) => {
	return request.get(BASE_URL, {
		loading: "plan-list",
		...config,
	});
};

export const getPlan = async (planId, config = {}) => {
	return request.get(`${BASE_URL}/${planId}`, {
		loading: "plan-detail",
		...config,
	});
};
