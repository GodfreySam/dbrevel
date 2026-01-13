/// <reference types="vite/client" />

interface ImportMetaEnv {
	readonly VITE_API_URL?: string;
	readonly VITE_API_DOCS_URL?: string;
	readonly VITE_TENANT_KEY?: string;
	readonly VITE_TIMEOUT?: string;
}

interface ImportMeta {
	readonly env: ImportMetaEnv;
}
