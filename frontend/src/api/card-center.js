import request from "../utils/request";

const BASE_URL = "/v1/cards";

export const getCards = (params, config = {}) => {
	return request.get(BASE_URL, {
		params,
		loading: "card-list",
		...config,
	});
};

export const getCard = (id, config = {}) => {
	return request.get(`${BASE_URL}/${id}`, {
		loading: "card-detail",
		...config,
	});
};

export const createCard = (data, config = {}) => {
	return request.post(BASE_URL, data, {
		loading: "card-create",
		...config,
	});
};

export const updateCard = (id, data, config = {}) => {
	return request.put(`${BASE_URL}/${id}`, data, {
		loading: "card-update",
		...config,
	});
};

export const deleteCard = (id, config = {}) => {
	return request.delete(`${BASE_URL}/${id}`, {
		loading: "card-delete",
		...config,
	});
};

export const getVersions = (id, config = {}) => {
	return request.get(`${BASE_URL}/${id}/versions`, {
		loading: "card-versions",
		...config,
	});
};

export const createVersion = (id, data, config = {}) => {
	return request.post(`${BASE_URL}/${id}/versions`, data, {
		loading: "card-version-create",
		...config,
	});
};

export const generateCardCode = (prompt, config = {}) => {
	return request.post(`${BASE_URL}/generate`, null, {
		params: { prompt, ...config },
		loading: "card-generate",
		timeout: 60000, // Generation might take time
	});
};

export const publishCard = (id, version, config = {}) => {
	return request.post(`${BASE_URL}/${id}/publish/${version}`, null, {
		loading: "card-publish",
		...config,
	});
};
