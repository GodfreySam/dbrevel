/**
 * Unit tests for retry logic
 */
import {
	DbRevelAPIError,
	DbRevelNetworkError,
	DbRevelTimeoutError,
} from "../errors";
import { withRetry } from "../utils/retry";

// Mock sleep
jest.useFakeTimers();

describe("Retry Logic", () => {
	beforeEach(() => {
		jest.clearAllTimers();
		jest.clearAllMocks();
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

		const promise = withRetry(fn, { maxRetries: 2 });
		jest.advanceTimersByTime(1000);
		const result = await promise;

		expect(result).toBe("success");
		expect(fn).toHaveBeenCalledTimes(2);
	});

	it("should retry on timeout error", async () => {
		const fn = jest
			.fn()
			.mockRejectedValueOnce(new DbRevelTimeoutError(5000))
			.mockResolvedValue("success");

		const promise = withRetry(fn, { maxRetries: 2 });
		jest.advanceTimersByTime(1000);
		const result = await promise;

		expect(result).toBe("success");
		expect(fn).toHaveBeenCalledTimes(2);
	});

	it("should retry on retryable status codes", async () => {
		const fn = jest
			.fn()
			.mockRejectedValueOnce(new DbRevelAPIError("Server error", 500))
			.mockResolvedValue("success");

		const promise = withRetry(fn, {
			maxRetries: 2,
			retryableStatusCodes: [500, 502, 503],
		});
		jest.advanceTimersByTime(1000);
		const result = await promise;

		expect(result).toBe("success");
		expect(fn).toHaveBeenCalledTimes(2);
	});

	it("should not retry on non-retryable status codes", async () => {
		const fn = jest
			.fn()
			.mockRejectedValue(new DbRevelAPIError("Bad request", 400));

		const promise = withRetry(fn, {
			maxRetries: 3,
			retryableStatusCodes: [500, 502, 503],
		});
		jest.advanceTimersByTime(1000);

		await expect(promise).rejects.toThrow(DbRevelAPIError);
		expect(fn).toHaveBeenCalledTimes(1);
	});

	it("should respect max retries", async () => {
		const fn = jest
			.fn()
			.mockRejectedValue(new DbRevelNetworkError("Network error"));

		const promise = withRetry(fn, { maxRetries: 2 });
		jest.advanceTimersByTime(5000);

		await expect(promise).rejects.toThrow(DbRevelNetworkError);
		expect(fn).toHaveBeenCalledTimes(3); // Initial + 2 retries
	});

	it("should use exponential backoff", async () => {
		const fn = jest
			.fn()
			.mockRejectedValue(new DbRevelNetworkError("Network error"));

		const promise = withRetry(fn, {
			maxRetries: 3,
			retryDelay: 1000,
			backoffMultiplier: 2,
		});

		// First retry after 1000ms
		jest.advanceTimersByTime(1000);
		await Promise.resolve();
		// Second retry after 2000ms
		jest.advanceTimersByTime(2000);
		await Promise.resolve();
		// Third retry after 4000ms
		jest.advanceTimersByTime(4000);
		await Promise.resolve();

		// Should have attempted 4 times (initial + 3 retries)
		expect(fn).toHaveBeenCalledTimes(4);
	});

	it("should respect max retry delay", async () => {
		const fn = jest
			.fn()
			.mockRejectedValue(new DbRevelNetworkError("Network error"));

		const promise = withRetry(fn, {
			maxRetries: 2,
			retryDelay: 1000,
			maxRetryDelay: 2000,
			backoffMultiplier: 10, // Would exceed maxRetryDelay
		});

		jest.advanceTimersByTime(5000);
		await expect(promise).rejects.toThrow();

		// Verify delays were capped at maxRetryDelay
		expect(fn).toHaveBeenCalledTimes(3);
	});

	it("should use custom shouldRetry function", async () => {
		const fn = jest
			.fn()
			.mockRejectedValueOnce(new Error("Custom error"))
			.mockResolvedValue("success");

		const shouldRetry = jest.fn().mockReturnValue(true);

		const promise = withRetry(fn, {
			maxRetries: 2,
			shouldRetry,
		});
		jest.advanceTimersByTime(1000);
		const result = await promise;

		expect(result).toBe("success");
		expect(shouldRetry).toHaveBeenCalled();
		expect(fn).toHaveBeenCalledTimes(2);
	});

	it("should not retry if shouldRetry returns false", async () => {
		const fn = jest.fn().mockRejectedValue(new Error("Custom error"));

		const promise = withRetry(fn, {
			maxRetries: 3,
			shouldRetry: () => false,
		});
		jest.advanceTimersByTime(1000);

		await expect(promise).rejects.toThrow();
		expect(fn).toHaveBeenCalledTimes(1);
	});
});
