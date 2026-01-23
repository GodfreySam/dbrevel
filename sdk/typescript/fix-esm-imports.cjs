/**
 * Post-build script: add .js extensions to relative imports in dist/esm
 * so Node ESM can resolve them. (Node ESM requires explicit extensions.)
 * Lives in package root (not scripts/) so it is not gitignored.
 */
const fs = require("fs");
const path = require("path");

const ESM_DIR = path.join(__dirname, "dist", "esm");

function* walk(dir) {
	const entries = fs.readdirSync(dir, { withFileTypes: true });
	for (const e of entries) {
		const full = path.join(dir, e.name);
		if (e.isDirectory()) {
			yield* walk(full);
		} else if (e.isFile() && e.name.endsWith(".js")) {
			yield full;
		}
	}
}

function fixImports(filePath) {
	let content = fs.readFileSync(filePath, "utf8");
	const dir = path.dirname(filePath);
	let changed = false;

	// Match from "./X" or from '../X' or from "./X/Y" etc — but not already .js
	const re = /from\s+["'](\.\.[^"']*|\.\/[^"']*)["']/g;
	content = content.replace(re, (full, imp) => {
		if (imp.endsWith(".js")) return full;
		const resolved = path.resolve(dir, imp);
		const asFile = resolved + ".js";
		const asIndex = path.join(resolved, "index.js");
		let replacement = imp;
		if (fs.existsSync(asFile)) {
			replacement = imp + ".js";
			changed = true;
		} else if (fs.existsSync(asIndex)) {
			replacement = imp.replace(/\/?$/, "") + "/index.js";
			changed = true;
		}
		return `from "${replacement}"`;
	});

	if (changed) {
		fs.writeFileSync(filePath, content, "utf8");
	}
}

if (!fs.existsSync(ESM_DIR)) {
	console.warn("fix-esm-imports: dist/esm not found, skipping");
	process.exit(0);
}

for (const f of walk(ESM_DIR)) {
	fixImports(f);
}

console.log("fix-esm-imports: done");
