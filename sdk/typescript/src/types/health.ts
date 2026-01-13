/**
 * Health check types
 */

export interface HealthResponse {
	status: string;
	databases: Record<string, string>;
}
