import request from "@/utils/request";

const BASE_URL = "/v1/vector";

export const getStats = (config = {}) =>
	request.get(`${BASE_URL}/stats`, {
		loading: "vector-stats",
		...config,
	});

export const rebuildIndex = (config = {}) =>
	request.post(
		`${BASE_URL}/rebuild`,
		{},
		{
			loading: "vector-rebuild",
			...config,
		},
	);

export const syncVectors = (config = {}) =>
	request.post(
		`${BASE_URL}/sync`,
		{},
		{
			loading: "vector-sync",
			...config,
		},
	);

export const searchVectors = (query, limit = 10, config = {}) =>
	request.get(`${BASE_URL}/search`, {
		loading: "vector-search",
		params: { q: query, limit },
		...config,
	});
