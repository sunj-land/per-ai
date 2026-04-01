// Auto-register all .vue components in this directory
const modules = import.meta.glob("./*.vue", { eager: true });
const cards = {};

for (const path in modules) {
	// Extract filename without extension
	const name = path.match(/\.\/(.*)\.vue$/)[1];
	// Skip internal components
	if (name !== "DynamicCardPreview" && name !== "AsyncCardRenderer") {
		cards[name] = modules[path].default;
	}
}

export default cards;
