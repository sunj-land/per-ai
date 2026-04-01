import { Message } from "@arco-design/web-vue";
import axios from "axios";

const API_BASE_URL = "http://localhost:8000/api/v1";

const api = axios.create({
	baseURL: API_BASE_URL,
});

api.interceptors.request.use((config) => {
	if (
		config.method === "post" ||
		config.method === "put" ||
		config.method === "patch"
	) {
		if (!config.headers["Content-Type"]) {
			config.headers["Content-Type"] = "application/json";
		}
	}
	return config;
});

api.interceptors.response.use(
	(response) => response,
	(error) => {
		if (error.response) {
			const { status } = error.response;
			let msg = "请求失败";
			if (status >= 500) msg = "服务器内部错误";
			Message.error(msg);
		} else {
			Message.error("网络错误，请检查连接");
		}
		return Promise.reject(error);
	},
);

// Notes API
export const createNote = async (data) => {
	const response = await api.post("/notes", data);
	return response.data;
};

export const getNotesByArticle = async (articleId) => {
	const response = await api.get(`/notes/article/${articleId}`);
	return response.data;
};

export const updateNote = async (id, data) => {
	// Use POST alias
	const response = await api.post(`/notes/${id}/update`, data);
	return response.data;
};

export const deleteNote = async (id) => {
	// Use POST alias
	const response = await api.post(`/notes/${id}/delete`);
	return response.data;
};

// Summaries API
export const saveSummary = async (data) => {
	const response = await api.post("/notes/summaries", data);
	return response.data;
};

export const getSummaryByArticle = async (articleId) => {
	const response = await api.get(`/notes/summaries/article/${articleId}`);
	return response.data;
};

export const deleteSummary = async (id) => {
	const response = await api.post(`/notes/summaries/${id}/delete`);
	return response.data;
};
