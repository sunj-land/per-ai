import { createPinia, setActivePinia } from "pinia";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { useLoadingStore } from "../loading";

describe("Loading Store", () => {
	let store;

	beforeEach(() => {
		setActivePinia(createPinia());
		store = useLoadingStore();
		vi.useFakeTimers();
	});

	it("should initialize with default state", () => {
		expect(store.globalLoading).toBe(false);
		expect(store.requestCount).toBe(0);
	});

	it("should handle global loading start/stop", () => {
		store.startLoading();
		expect(store.globalLoading).toBe(true);
		expect(store.requestCount).toBe(1);

		store.stopLoading();
		expect(store.requestCount).toBe(0);
		// Should still be true due to min loading time
		expect(store.globalLoading).toBe(true);

		// Advance time
		vi.advanceTimersByTime(300);
		expect(store.globalLoading).toBe(false);
	});

	it("should handle local loading", () => {
		const key = "test-key";
		store.startLoading(key);
		expect(store.isLoading(key)).toBe(true);
		expect(store.globalLoading).toBe(false); // Should not affect global

		store.stopLoading(key);
		expect(store.isLoading(key)).toBe(false);
	});

	it("should handle nested/parallel global requests", () => {
		store.startLoading();
		store.startLoading();
		expect(store.requestCount).toBe(2);
		expect(store.globalLoading).toBe(true);

		store.stopLoading();
		expect(store.requestCount).toBe(1);
		expect(store.globalLoading).toBe(true);

		store.stopLoading();
		expect(store.requestCount).toBe(0);
	});

	it("should force stop global loading", () => {
		store.startLoading();
		store.stopLoading(null, true); // force = true
		expect(store.globalLoading).toBe(false);
		expect(store.requestCount).toBe(0);
	});

	it("should manage active requests for cancellation", () => {
		const id = "req-1";
		const controller = new AbortController();
		const abortSpy = vi.spyOn(controller, "abort");

		store.addRequest(id, controller);
		// Access internal state via any (testing implementation detail)
		// or just test cancelAll behavior

		store.cancelAll();
		expect(abortSpy).toHaveBeenCalled();
	});
});
