/**
 * Unit tests for validation utilities
 */
import { DbRevelValidationError } from "../errors";
import {
	validateHealthResponse,
	validateQueryResult,
	validateSchemasResponse,
} from "../utils/validation";

describe("Validation Utilities", () => {
	describe("validateQueryResult", () => {
		const validQueryResult = {
			data: [{ id: 1, name: "Test" }],
			metadata: {
				query_plan: {
					databases: ["postgres"],
					queries: [],
					security_applied: [],
					estimated_cost: "low",
				},
				execution_time_ms: 100,
				rows_returned: 1,
				gemini_tokens_used: 50,
				trace_id: "test-trace",
				timestamp: "2024-01-01T00:00:00Z",
				cached: false,
			},
		};

		it("should validate correct query result", () => {
			expect(() => validateQueryResult(validQueryResult)).not.toThrow();
			const result = validateQueryResult(validQueryResult);
			expect(result.data).toEqual(validQueryResult.data);
			expect(result.metadata).toEqual(validQueryResult.metadata);
		});

		it("should throw error for non-object", () => {
			expect(() => validateQueryResult(null)).toThrow(DbRevelValidationError);
			expect(() => validateQueryResult([])).toThrow(DbRevelValidationError);
			expect(() => validateQueryResult("string")).toThrow(DbRevelValidationError);
		});

		it("should throw error for missing data array", () => {
			const invalid = { ...validQueryResult, data: "not an array" };
			expect(() => validateQueryResult(invalid)).toThrow(DbRevelValidationError);
		});

		it("should throw error for missing metadata", () => {
			const invalid = { data: [] };
			expect(() => validateQueryResult(invalid)).toThrow(DbRevelValidationError);
		});

		it("should throw error for invalid metadata", () => {
			const invalid = {
				data: [],
				metadata: {
					execution_time_ms: "not a number",
					rows_returned: 1,
					gemini_tokens_used: 50,
					trace_id: "test",
					timestamp: "2024-01-01T00:00:00Z",
					cached: false,
					query_plan: {
						databases: ["postgres"],
						queries: [],
						security_applied: [],
						estimated_cost: "low",
					},
				},
			};
			expect(() => validateQueryResult(invalid)).toThrow(DbRevelValidationError);
		});
	});

	describe("validateSchemasResponse", () => {
		const validSchemasResponse = {
			databases: {
				postgres: {
					name: "postgres",
					type: "postgresql",
					tables: [],
				},
			},
		};

		it("should validate correct schemas response", () => {
			expect(() => validateSchemasResponse(validSchemasResponse)).not.toThrow();
			const result = validateSchemasResponse(validSchemasResponse);
			expect(result.databases).toEqual(validSchemasResponse.databases);
		});

		it("should throw error for non-object", () => {
			expect(() => validateSchemasResponse(null)).toThrow(DbRevelValidationError);
			expect(() => validateSchemasResponse([])).toThrow(DbRevelValidationError);
		});

		it("should throw error for missing databases", () => {
			const invalid = {};
			expect(() => validateSchemasResponse(invalid)).toThrow(DbRevelValidationError);
		});
	});

	describe("validateHealthResponse", () => {
		const validHealthResponse = {
			status: "healthy",
			databases: {
				postgres: "connected",
				mongodb: "connected",
			},
		};

		it("should validate correct health response", () => {
			expect(() => validateHealthResponse(validHealthResponse)).not.toThrow();
			const result = validateHealthResponse(validHealthResponse);
			expect(result.status).toBe("healthy");
			expect(result.databases).toEqual(validHealthResponse.databases);
		});

		it("should throw error for non-object", () => {
			expect(() => validateHealthResponse(null)).toThrow(DbRevelValidationError);
		});

		it("should throw error for missing status", () => {
			const invalid = { databases: {} };
			expect(() => validateHealthResponse(invalid)).toThrow(DbRevelValidationError);
		});

		it("should throw error for invalid status type", () => {
			const invalid = { status: 123, databases: {} };
			expect(() => validateHealthResponse(invalid)).toThrow(DbRevelValidationError);
		});
	});
});
