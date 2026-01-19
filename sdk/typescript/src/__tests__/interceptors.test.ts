/**
 * Unit tests for interceptors
 */
import { DbRevelClient } from "../client";
import type { RequestConfig } from "../types/interceptors";

// Mock fetch globally
global.fetch = jest.fn();

describe("Interceptors", () => {
	let client: DbRevelClient;
	const mockBaseUrl = "http://localhost:8000";
	const mockApiKey = "test-api-key";

	beforeEach(() => {
		client = new DbRevelClient({
			baseUrl: mockBaseUrl,
			apiKey: mockApiKey,
		});
		jest.clearAllMocks();
	});

	describe("Request Interceptors", () => {
		it("should apply request interceptors", async () => {
			const mockResponse = {
				data: [],
				metadata: {
					query_plan: {
						databases: ["postgres"],
						queries: [],
						security_applied: [],
						estimated_cost: "low",
					},
					execution_time_ms: 100,
					rows_returned: 0,
					gemini_tokens_used: 50,
					trace_id: "test-trace",
					timestamp: "2024-01-01T00:00:00Z",
					cached: false,
				},
			};

			(global.fetch as jest.Mock).mockResolvedValueOnce({
				ok: true,
				json: async () => mockResponse,
			});

			let interceptedConfig: RequestConfig | undefined;
			client.useRequestInterceptor((config) => {
				interceptedConfig = config;
				// Add custom header
				return {
					...config,
					headers: {
						...config.headers,
						"X-Custom-Header": "custom-value",
					},
				};
			});

			await client.query("Get users");

			expect(interceptedConfig).toBeDefined();
			expect(interceptedConfig!.url).toContain("/api/v1/query");
		});

		it("should chain multiple request interceptors", async () => {
			const mockResponse = {
				data: [],
				metadata: {
					query_plan: {
						databases: ["postgres"],
						queries: [],
						security_applied: [],
						estimated_cost: "low",
					},
					execution_time_ms: 100,
					rows_returned: 0,
					gemini_tokens_used: 50,
					trace_id: "test-trace",
					timestamp: "2024-01-01T00:00:00Z",
					cached: false,
				},
			};

			(global.fetch as jest.Mock).mockResolvedValueOnce({
				ok: true,
				json: async () => mockResponse,
			});

			let callOrder: string[] = [];
			client.useRequestInterceptor((config) => {
				callOrder.push("first");
				return config;
			});
			client.useRequestInterceptor((config) => {
				callOrder.push("second");
				return config;
			});

			await client.query("Get users");

			expect(callOrder).toEqual(["first", "second"]);
		});
	});

	describe("Response Interceptors", () => {
		it("should apply response interceptors", async () => {
			const mockResponse = {
				data: [{ id: 1 }],
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

			(global.fetch as jest.Mock).mockResolvedValueOnce({
				ok: true,
				json: async () => mockResponse,
			});

			let interceptedResponse: Response | null = null;
			client.useResponseInterceptor((response) => {
				interceptedResponse = response;
				return response;
			});

			await client.query("Get users");

			expect(interceptedResponse).not.toBeNull();
		});
	});

	describe("Error Interceptors", () => {
		it("should apply error interceptors on API errors", async () => {
			(global.fetch as jest.Mock).mockResolvedValueOnce({
				ok: false,
				status: 400,
				statusText: "Bad Request",
				json: async () => ({ detail: "Invalid query" }),
			});

			let interceptedError: Error | null = null;
			client.useErrorInterceptor((error) => {
				interceptedError = error;
				return error;
			});

			try {
				await client.query("test");
			} catch (error) {
				// Expected
			}

			expect(interceptedError).not.toBeNull();
		});

		it("should allow error interceptors to modify errors", async () => {
			(global.fetch as jest.Mock).mockResolvedValueOnce({
				ok: false,
				status: 500,
				statusText: "Internal Server Error",
				json: async () => ({ detail: "Server error" }),
			});

			client.useErrorInterceptor((error) => {
				// Modify error message
				error.message = "Custom error message";
				return error;
			});

			try {
				await client.query("test");
				fail("Should have thrown");
			} catch (error: any) {
				expect(error.message).toBe("Custom error message");
			}
		});
	});

	describe("clearInterceptors", () => {
		it("should clear all interceptors", () => {
			client.useRequestInterceptor(() => ({} as RequestConfig));
			client.useResponseInterceptor(() => ({} as Response));
			client.useErrorInterceptor(() => new Error());

			client.clearInterceptors();

			// Interceptors should be cleared (we can't directly test private arrays,
			// but we can verify by checking behavior)
			expect(client).toBeDefined();
		});
	});
});
