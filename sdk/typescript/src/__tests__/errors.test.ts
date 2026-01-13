/**
 * Unit tests for error classes
 */
import {
	DbRevelAPIError,
	DbRevelError,
	DbRevelNetworkError,
	DbRevelTimeoutError,
	DbRevelValidationError,
} from "../errors";

describe("Error Classes", () => {
	describe("DbRevelError", () => {
		it("should create error with message and code", () => {
			const error = new DbRevelError("Test error", "TEST_CODE");
			expect(error.message).toBe("Test error");
			expect(error.code).toBe("TEST_CODE");
			expect(error.name).toBe("DbRevelError");
		});

		it("should include status code and details", () => {
			const error = new DbRevelError("Test", "CODE", 400, { field: "value" });
			expect(error.statusCode).toBe(400);
			expect(error.details).toEqual({ field: "value" });
		});
	});

	describe("DbRevelTimeoutError", () => {
		it("should create timeout error with timeout value", () => {
			const error = new DbRevelTimeoutError(5000);
			expect(error.message).toContain("5000");
			expect(error.code).toBe("TIMEOUT");
			expect(error.name).toBe("DbRevelTimeoutError");
			expect(error.details?.timeout).toBe(5000);
		});
	});

	describe("DbRevelAPIError", () => {
		it("should create API error with status code", () => {
			const error = new DbRevelAPIError("API error", 404);
			expect(error.message).toBe("API error");
			expect(error.statusCode).toBe(404);
			expect(error.code).toBe("API_ERROR");
			expect(error.name).toBe("DbRevelAPIError");
		});

		it("should include response in details", () => {
			const response = { detail: "Not found" };
			const error = new DbRevelAPIError("Error", 404, response);
			expect(error.response).toEqual(response);
		});
	});

	describe("DbRevelValidationError", () => {
		it("should create validation error", () => {
			const error = new DbRevelValidationError("Validation failed");
			expect(error.message).toBe("Validation failed");
			expect(error.code).toBe("VALIDATION_ERROR");
			expect(error.name).toBe("DbRevelValidationError");
		});

		it("should include details", () => {
			const details = { field: "email", reason: "invalid format" };
			const error = new DbRevelValidationError("Invalid", details);
			expect(error.details).toEqual(details);
		});
	});

	describe("DbRevelNetworkError", () => {
		it("should create network error", () => {
			const error = new DbRevelNetworkError("Network failed");
			expect(error.message).toBe("Network failed");
			expect(error.code).toBe("NETWORK_ERROR");
			expect(error.name).toBe("DbRevelNetworkError");
		});

		it("should include original error", () => {
			const originalError = new Error("Original");
			const error = new DbRevelNetworkError("Network failed", originalError);
			expect(error.details?.originalError).toBe("Original");
		});
	});
});
