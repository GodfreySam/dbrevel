import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import { visualizer } from "rollup-plugin-visualizer";

// https://vitejs.dev/config/
export default defineConfig({
	plugins: [
		react(),
		visualizer({
			open: true, // Automatically open the report in the browser
			filename: "bundle-analysis.html", // Output report file name
		}),
	],
	server: {
		port: 3000,
		proxy: {
			// Proxy API requests to avoid CORS issues in dev
			"/api": {
				target: "http://localhost:8000",
				changeOrigin: true,
			},
		},
	},
});
