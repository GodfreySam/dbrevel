/**
 * Unit tests for retry logic
 */
import {
	DbRevelAPIError,
	DbRevelNetworkError,
	DbRevelTimeoutError,
} from "../errors";
import { withRetry } from "../utils/retry";

describe("Retry Logic", () => {
	beforeEach(() => {
		jest.clearAllMocks();
		jest.useRealTimers();
	});

	it("should succeed on first attempt", async () => {
		const fn = jest.fn().mockResolvedValue("success");
		const result = await withRetry(fn);
		expect(result).toBe("success");
		expect(fn).toHaveBeenCalledTimes(1);
	});

	it("should retry on network error", async () => {
		const fn = jest
			.fn()
			.mockRejectedValueOnce(new DbRevelNetworkError("Network error"))
			.mockResolvedValue("success");

		// Use short delays for tests
		const result = await withRetry(fn, { maxRetries: 2, retryDelay: 10 });

		expect(result).toBe("success");
		expect(fn).toHaveBeenCalledTimes(2);
	}, 10000);

	it("should retry on timeout error", async () => {
		const fn = jest
			.fn()
			.mockRejectedValueOnce(new DbRevelTimeoutError(5000))
			.mockResolvedValue("success");

		const result = await withRetry(fn, { maxRetries: 2, retryDelay: 10 });

		expect(result).toBe("success");
		expect(fn).toHaveBeenCalledTimes(2);
	}, 10000);

	it("should retry on retryable status codes", async () => {
		const fn = jest
			.fn()
			.mockRejectedValueOnce(new DbRevelAPIError("Server error", 500))
			.mockResolvedValue("success");

		const result = await withRetry(fn, {
			maxRetries: 2,
			retryDelay: 10,
			retryableStatusCodes: [500, 502, 503],
		});

		expect(result).toBe("success");
		expect(fn).toHaveBeenCalledTimes(2);
	}, 10000);

	it("should not retry on non-retryable status codes", async () => {
		const fn = jest
			.fn()
			.mockRejectedValue(new DbRevelAPIError("Bad request", 400));

		await expect(
			withRetry(fn, {
				maxRetries: 3,
				retryDelay: 10,
				retryableStatusCodes: [500, 502, 503],
			}),
		).rejects.toThrow(DbRevelAPIError);
		expect(fn).toHaveBeenCalledTimes(1);
	});

	it("should respect max retries", async () => {
		const fn = jest
			.fn()
			.mockRejectedValue(new DbRevelNetworkError("Network error"));

		await expect(
			withRetry(fn, { maxRetries: 2, retryDelay: 10 }),
		).rejects.toThrow(DbRevelNetworkError);
		expect(fn).toHaveBeenCalledTimes(3); // Initial + 2 retries
	}, 10000);

	it("should use exponential backoff", async () => {
		const delays: number[] = [];
		let lastTime = Date.now();

		const fn = jest.fn().mockImplementation(async () => {
			const now = Date.now();
			if (fn.mock.calls.length > 1) {
				delays.push(now - lastTime);
			}
			lastTime = now;
			if (fn.mock.calls.length < 4) {
				throw new DbRevelNetworkError("Network error");
			}
			return "success";
		});

		const result = await withRetry(fn, {
			maxRetries: 3,
			retryDelay: 50,
			backoffMultiplier: 2,
		});

		expect(result).toBe("success");
		expect(fn).toHaveBeenCalledTimes(4);
		// Verify exponential backoff pattern (with some tolerance)
		expect(delays[0]).toBeGreaterThanOrEqual(40);
		expect(delays[1]).toBeGreaterThanOrEqual(90);
		expect(delays[2]).toBeGreaterThanOrEqual(180);
	}, 10000);

	it("should respect max retry delay", async () => {
		const delays: number[] = [];
		let lastTime = Date.now();

		const fn = jest.fn().mockImplementation(async () => {
			const now = Date.now();
			if (fn.mock.calls.length > 1) {
				delays.push(now - lastTime);
			}
			lastTime = now;
			if (fn.mock.calls.length < 3) {
				throw new DbRevelNetworkError("Network error");
			}
			return "success";
		});

		const result = await withRetry(fn, {
			maxRetries: 2,
			retryDelay: 50,
			maxRetryDelay: 75,
			backoffMultiplier: 10, // Would be 500ms without cap
		});

		expect(result).toBe("success");
		expect(fn).toHaveBeenCalledTimes(3);
		// Verify delays were capped at maxRetryDelay
		delays.forEach((delay) => {
			expect(delay).toBeLessThanOrEqual(100); // maxRetryDelay + tolerance
		});
	}, 10000);

	it("should use custom shouldRetry function", async () => {
		const fn = jest
			.fn()
			.mockRejectedValueOnce(new Error("Custom error"))
			.mockResolvedValue("success");

		const shouldRetry = jest.fn().mockReturnValue(true);

		const result = await withRetry(fn, {
			maxRetries: 2,
			retryDelay: 10,
			shouldRetry,
			retryableErrorCodes: [], // Clear default retryable codes
		});

		expect(result).toBe("success");
		expect(shouldRetry).toHaveBeenCalled();
		expect(fn).toHaveBeenCalledTimes(2);
	}, 10000);

	it("should not retry if shouldRetry returns false", async () => {
		const fn = jest.fn().mockRejectedValue(new Error("Custom error"));

		await expect(
			withRetry(fn, {
				maxRetries: 3,
				retryDelay: 10,
				shouldRetry: () => false,
			}),
		).rejects.toThrow();
		expect(fn).toHaveBeenCalledTimes(1);
	});
});
