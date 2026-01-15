/**
 * API Type Definitions
 * Matches backend Pydantic models in backend/app/models/
 */

export interface User {
	id: string;
	email: string;
	account_id: string; // Critical for multi-tenant context
	full_name?: string;
	account_name: string;
	projects_count?: number;
	created_at: string;
	last_login?: string;
	email_verified?: boolean;
	role: "user" | "admin";
}

export interface AuthResponse {
	access_token: string;
	token_type: string;
	user: User;
}

// Matches ProjectListResponse (GET /api/v1/projects)
export interface ProjectSummary {
	id: string;
	name: string;
	is_active: boolean;
	created_at: string;
	updated_at?: string;
}

// Matches ProjectResponse (GET /api/v1/projects/:id)
export interface ProjectDetail extends ProjectSummary {
	account_id: string;
	api_key: string; // Masked (***) unless just created/revealed
	postgres_url: string; // Masked
	mongodb_url: string; // Masked
	updated_at: string;
}

// Matches AccountResponse (GET /api/v1/accounts/me/info-jwt)
export interface AccountDetail {
	id: string;
	name: string;
	api_key: string; // Account-level key (usually hidden/admin)
	postgres_url: string;
	mongodb_url: string;
	gemini_mode: "platform" | "byo";
	gemini_api_key?: string;
}

export interface ApiKeyRotateResponse {
	project_id?: string;
	account_id?: string;
	new_api_key: string;
	rotated_at: string;
}
