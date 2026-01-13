/**
 * Frontend configuration from environment variables
 * Vite exposes env vars prefixed with VITE_ via import.meta.env
 */

// Derive API base URL and docs URL
const apiBaseUrl =
	import.meta.env.VITE_API_URL || "http://localhost:8000/api/v1";
const baseUrl = apiBaseUrl.replace("/api/v1", "");

export const config = {
	apiUrl: apiBaseUrl,
	apiDocsUrl: import.meta.env.VITE_API_DOCS_URL || `${baseUrl}/docs`, // External backend docs URL (used for iframes)
	internalDocsUrl: "/docs", // Internal frontend route for documentation page
	baseUrl: baseUrl,
	accountKey: import.meta.env.VITE_ACCOUNT_KEY || "dbrevel_demo_project_key",
	timeout: parseInt(import.meta.env.VITE_TIMEOUT || "30000", 10),
} as const;

// Validate required config
if (!config.apiUrl) {
	throw new Error("VITE_API_URL is required");
}

if (!config.accountKey) {
	console.warn("VITE_ACCOUNT_KEY not set, using default account key");
}
