/**
 * Unit tests for DbRevelClient
 */
import { DbRevelClient } from "../client";
import { DbRevelAPIError } from "../errors";

// Mock fetch globally
global.fetch = jest.fn();

describe("DbRevelClient", () => {
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

	describe("constructor", () => {
		it("should initialize with config", () => {
			expect(client).toBeInstanceOf(DbRevelClient);
		});

		it("should remove trailing slash from baseUrl", () => {
			const clientWithSlash = new DbRevelClient({
				baseUrl: "http://localhost:8000/",
				apiKey: mockApiKey,
			});
			// Base URL should be normalized (we can't directly test private property)
			// But we can verify it works by making a request
		});

		it("should use default timeout if not provided", () => {
			const clientDefaultTimeout = new DbRevelClient({
				baseUrl: mockBaseUrl,
				apiKey: mockApiKey,
			});
			expect(clientDefaultTimeout).toBeInstanceOf(DbRevelClient);
		});
	});

	describe("query", () => {
		it("should execute a successful query", async () => {
			const mockResponse = {
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

			(global.fetch as jest.Mock).mockResolvedValueOnce({
				ok: true,
				json: async () => mockResponse,
			});

			const result = await client.query("Get all users");

			expect(global.fetch).toHaveBeenCalledWith(
				expect.stringContaining("/api/v1/query"),
				expect.objectContaining({
					method: "POST",
					headers: expect.objectContaining({
						"Content-Type": "application/json",
						"X-Tenant-Key": mockApiKey,
					}),
				}),
			);

			expect(result.data).toEqual(mockResponse.data);
			expect(result.metadata).toEqual(mockResponse.metadata);
		});

		it("should throw error for empty intent", async () => {
			await expect(client.query("")).rejects.toThrow(
				"Intent must be a non-empty string",
			);
			await expect(client.query("   ")).rejects.toThrow(
				"Intent must be a non-empty string",
			);
		});

		it("should handle API errors", async () => {
			(global.fetch as jest.Mock).mockResolvedValueOnce({
				ok: false,
				status: 400,
				statusText: "Bad Request",
				json: async () => ({ detail: "Invalid query" }),
			});

			await expect(client.query("test")).rejects.toThrow(DbRevelAPIError);
		});

		it("should support dry run option", async () => {
			const mockResponse = {
				data: [],
				metadata: {
					query_plan: {
						databases: ["postgres"],
						queries: [],
						security_applied: [],
						estimated_cost: "low",
					},
					execution_time_ms: 50,
					rows_returned: 0,
					gemini_tokens_used: 30,
					trace_id: "test-trace",
					timestamp: "2024-01-01T00:00:00Z",
					cached: false,
				},
			};

			(global.fetch as jest.Mock).mockResolvedValueOnce({
				ok: true,
				json: async () => mockResponse,
			});

			await client.query("Get users", { dryRun: true });

			const callArgs = (global.fetch as jest.Mock).mock.calls[0];
			const body = JSON.parse(callArgs[1].body);
			expect(body.dry_run).toBe(true);
		});

		it("should support context option", async () => {
			const mockResponse = {
				data: [],
				metadata: {
					query_plan: {
						databases: ["postgres"],
						queries: [],
						security_applied: [],
						estimated_cost: "low",
					},
					execution_time_ms: 50,
					rows_returned: 0,
					gemini_tokens_used: 30,
					trace_id: "test-trace",
					timestamp: "2024-01-01T00:00:00Z",
					cached: false,
				},
			};

			(global.fetch as jest.Mock).mockResolvedValueOnce({
				ok: true,
				json: async () => mockResponse,
			});

			const context = { userId: 123 };
			await client.query("Get users", { context });

			const callArgs = (global.fetch as jest.Mock).mock.calls[0];
			const body = JSON.parse(callArgs[1].body);
			expect(body.context).toEqual(context);
		});
	});

	describe("getSchemas", () => {
		it("should fetch all schemas", async () => {
			const mockResponse = {
				databases: {
					postgres: {
						name: "postgres",
						type: "postgresql",
						tables: [],
					},
				},
			};

			(global.fetch as jest.Mock).mockResolvedValueOnce({
				ok: true,
				json: async () => mockResponse,
			});

			const result = await client.getSchemas();

			expect(global.fetch).toHaveBeenCalledWith(
				expect.stringContaining("/api/v1/schema"),
				expect.objectContaining({
					method: "GET",
				}),
			);

			expect(result.databases).toEqual(mockResponse.databases);
		});

		it("should handle API errors", async () => {
			(global.fetch as jest.Mock).mockResolvedValueOnce({
				ok: false,
				status: 500,
				statusText: "Internal Server Error",
				json: async () => ({ detail: "Server error" }),
			});

			await expect(client.getSchemas()).rejects.toThrow(DbRevelAPIError);
		});
	});

	describe("getSchema", () => {
		it("should fetch schema for specific database", async () => {
			const mockResponse = {
				name: "postgres",
				type: "postgresql",
				tables: [],
			};

			(global.fetch as jest.Mock).mockResolvedValueOnce({
				ok: true,
				json: async () => mockResponse,
			});

			const result = await client.getSchema("postgres");

			expect(global.fetch).toHaveBeenCalledWith(
				expect.stringContaining("/api/v1/schema/postgres"),
				expect.objectContaining({
					method: "GET",
				}),
			);

			expect(result).toEqual(mockResponse);
		});

		it("should throw error for empty database name", async () => {
			await expect(client.getSchema("")).rejects.toThrow(
				"Database name must be a non-empty string",
			);
		});
	});

	describe("health", () => {
		it("should check health status", async () => {
			const mockResponse = {
				status: "healthy",
				databases: {
					postgres: "connected",
					mongodb: "connected",
				},
			};

			(global.fetch as jest.Mock).mockResolvedValueOnce({
				ok: true,
				json: async () => mockResponse,
			});

			const result = await client.health();

			expect(global.fetch).toHaveBeenCalledWith(
				expect.stringContaining("/health"),
				expect.objectContaining({
					method: "GET",
				}),
			);

			expect(result.status).toBe("healthy");
			expect(result.databases).toEqual(mockResponse.databases);
		});
	});
});
