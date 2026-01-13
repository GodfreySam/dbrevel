/**
 * Query-related types
 */

export interface DatabaseQuery {
	database: string;
	query_type: "sql" | "mongodb" | "cross-db";
	query: string | Array<Record<string, any>>;
	parameters?: any[];
	estimated_rows?: number;
	collection?: string;
}

export interface QueryPlan {
	databases: string[];
	queries: DatabaseQuery[];
	join_strategy?: string;
	reasoning?: string;
	security_applied: string[];
	estimated_cost: string;
}

export interface QueryMetadata {
	query_plan: QueryPlan;
	execution_time_ms: number;
	rows_returned: number;
	gemini_tokens_used: number;
	trace_id: string;
	timestamp: string;
	cached: boolean;
}

export interface QueryResult<T = any> {
	data: T[];
	metadata: QueryMetadata;
}
