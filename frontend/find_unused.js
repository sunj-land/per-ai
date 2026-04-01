import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const srcDir = path.join(__dirname, "src");

function getAllFiles(dir, fileList = []) {
	const files = fs.readdirSync(dir);
	for (const file of files) {
		const filePath = path.join(dir, file);
		if (fs.statSync(filePath).isDirectory()) {
			getAllFiles(filePath, fileList);
		} else if (filePath.match(/\.(js|vue|ts)$/)) {
			fileList.push(filePath);
		}
	}
	return fileList;
}

const allFiles = getAllFiles(srcDir);
const fileContents = allFiles.map((f) => fs.readFileSync(f, "utf-8"));

for (const file of allFiles) {
	const relativePath = path.relative(srcDir, file).replace(/\\/g, "/");
	const baseName = path.basename(file, path.extname(file));

	if (
		file === __filename ||
		file.includes("main.js") ||
		file.includes("router.js") ||
		file.includes("App.vue")
	)
		continue;

	let isImported = false;
	for (const content of fileContents) {
		if (content.includes(baseName)) {
			isImported = true;
			break;
		}
	}
	if (!isImported) {
		console.log("Unused file:", relativePath);
	}
}
