import request from "../utils/request";

const BASE_URL = "/v1/attachments";

export const uploadAttachment = async (formData, config = {}) => {
	return request.post(`${BASE_URL}/upload`, formData, {
		headers: {
			"Content-Type": "multipart/form-data",
		},
		loading: "attachment-upload",
		...config,
	});
};

export const searchAttachments = async (params, config = {}) => {
	return request.get(`${BASE_URL}/search`, {
		params,
		loading: "attachment-list",
		...config,
	});
};

export const deleteAttachment = async (uuid, config = {}) => {
	return request.delete(`${BASE_URL}/${uuid}`, {
		loading: "attachment-delete",
		...config,
	});
};

export const getPreviewUrl = (uuid) => {
	return `${request.defaults.baseURL}${BASE_URL}/${uuid}/preview`;
};

export const getDownloadUrl = (uuid) => {
	return `${request.defaults.baseURL}${BASE_URL}/${uuid}/download`;
};
