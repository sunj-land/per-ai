import BlockLoading from "./BlockLoading.vue";
import GlobalLoading from "./GlobalLoading.vue";
import SkeletonLoading from "./SkeletonLoading.vue";

export { GlobalLoading, BlockLoading, SkeletonLoading };

export default {
	install(app) {
		app.component("GlobalLoading", GlobalLoading);
		app.component("BlockLoading", BlockLoading);
		app.component("SkeletonLoading", SkeletonLoading);
	},
};
