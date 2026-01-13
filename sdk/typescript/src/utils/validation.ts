/**
 * Response validation utilities
 */
import { DbRevelValidationError } from "../errors";
import type {
	HealthResponse,
	QueryMetadata,
	QueryPlan,
	QueryResult,
	SchemasResponse,
} from "../types";

/**
 * Validate that a value is an object
 */
function isObject(value: any): value is Record<string, any> {
	return typeof value === "object" && value !== null && !Array.isArray(value);
}

/**
 * Validate that a value is an array
 */
function isArray(value: any): value is any[] {
	return Array.isArray(value);
}

/**
 * Validate that a value is a string
 */
function isString(value: any): value is string {
	return typeof value === "string";
}

/**
 * Validate that a value is a number
 */
function isNumber(value: any): value is number {
	return typeof value === "number" && !isNaN(value);
}

/**
 * Validate QueryPlan structure
 */
function validateQueryPlan(plan: any): QueryPlan {
	if (!isObject(plan)) {
		throw new DbRevelValidationError("QueryPlan must be an object");
	}

	if (!isArray(plan.databases) || !plan.databases.every(isString)) {
		throw new DbRevelValidationError(
			"QueryPlan.databases must be an array of strings",
		);
	}

	if (!isArray(plan.queries)) {
		throw new DbRevelValidationError("QueryPlan.queries must be an array");
	}

	if (!isString(plan.estimated_cost)) {
		throw new DbRevelValidationError(
			"QueryPlan.estimated_cost must be a string",
		);
	}

	if (
		!isArray(plan.security_applied) ||
		!plan.security_applied.every(isString)
	) {
		throw new DbRevelValidationError(
			"QueryPlan.security_applied must be an array of strings",
		);
	}

	return plan as QueryPlan;
}

/**
 * Validate QueryMetadata structure
 */
function validateQueryMetadata(metadata: any): QueryMetadata {
	if (!isObject(metadata)) {
		throw new DbRevelValidationError("QueryMetadata must be an object");
	}

	if (!isNumber(metadata.execution_time_ms)) {
		throw new DbRevelValidationError(
			"QueryMetadata.execution_time_ms must be a number",
		);
	}

	if (!isNumber(metadata.rows_returned)) {
		throw new DbRevelValidationError(
			"QueryMetadata.rows_returned must be a number",
		);
	}

	if (!isNumber(metadata.gemini_tokens_used)) {
		throw new DbRevelValidationError(
			"QueryMetadata.gemini_tokens_used must be a number",
		);
	}

	if (!isString(metadata.trace_id)) {
		throw new DbRevelValidationError("QueryMetadata.trace_id must be a string");
	}

	if (!isString(metadata.timestamp)) {
		throw new DbRevelValidationError(
			"QueryMetadata.timestamp must be a string",
		);
	}

	if (typeof metadata.cached !== "boolean") {
		throw new DbRevelValidationError("QueryMetadata.cached must be a boolean");
	}

	if (!metadata.query_plan) {
		throw new DbRevelValidationError("QueryMetadata.query_plan is required");
	}

	metadata.query_plan = validateQueryPlan(metadata.query_plan);

	return metadata as QueryMetadata;
}

/**
 * Validate QueryResult structure
 */
export function validateQueryResult<T = any>(data: any): QueryResult<T> {
	if (!isObject(data)) {
		throw new DbRevelValidationError("QueryResult must be an object");
	}

	if (!isArray(data.data)) {
		throw new DbRevelValidationError("QueryResult.data must be an array");
	}

	if (!data.metadata) {
		throw new DbRevelValidationError("QueryResult.metadata is required");
	}

	data.metadata = validateQueryMetadata(data.metadata);

	return data as QueryResult<T>;
}

/**
 * Validate SchemasResponse structure
 */
export function validateSchemasResponse(data: any): SchemasResponse {
	if (!isObject(data)) {
		throw new DbRevelValidationError("SchemasResponse must be an object");
	}

	if (!isObject(data.databases)) {
		throw new DbRevelValidationError(
			"SchemasResponse.databases must be an object",
		);
	}

	return data as SchemasResponse;
}

/**
 * Validate HealthResponse structure
 */
export function validateHealthResponse(data: any): HealthResponse {
	if (!isObject(data)) {
		throw new DbRevelValidationError("HealthResponse must be an object");
	}

	if (!isString(data.status)) {
		throw new DbRevelValidationError("HealthResponse.status must be a string");
	}

	if (!isObject(data.databases)) {
		throw new DbRevelValidationError(
			"HealthResponse.databases must be an object",
		);
	}

	return data as HealthResponse;
}
