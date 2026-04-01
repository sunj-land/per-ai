import { mount } from "@vue/test-utils";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import MessageContent from "./MessageContent.vue";

// Mock thinking display to avoid unneeded renders
vi.mock("./ThinkingDisplay.vue", () => ({
	default: {
		name: "ThinkingDisplay",
		template: "<div><slot></slot></div>",
	},
}));

describe("MessageContent.vue", () => {
	beforeEach(() => {
		vi.useFakeTimers();
	});

	afterEach(() => {
		vi.restoreAllMocks();
	});

	it("renders normal content immediately when animate is false", async () => {
		const wrapper = mount(MessageContent, {
			props: {
				content: "Hello World",
				animate: false,
			},
		});

		expect(wrapper.text()).toContain("Hello World");
	});

	it("purifies JSON content and displays extracted text", async () => {
		const jsonContent = JSON.stringify({ message: "JSON Text" });
		const wrapper = mount(MessageContent, {
			props: {
				content: jsonContent,
				animate: false,
			},
		});

		expect(wrapper.text()).toContain("JSON Text");
		expect(wrapper.text()).not.toContain('{"message":');
	});

	it("animates text character by character when animate is true", async () => {
		const wrapper = mount(MessageContent, {
			props: {
				content: "Test",
				animate: true,
				speed: 30,
			},
		});

		// Initial state (first char is typed immediately)
		expect(wrapper.text()).toBe("T");

		// Advance timer for next chars
		vi.advanceTimersByTime(100);
		await wrapper.vm.$nextTick();
		// Since delay is 30 + random(0, 30) (max 60ms per char), 100ms is enough for 1-3 chars
		// We can just advance a lot to get the full string
		vi.advanceTimersByTime(500);
		await wrapper.vm.$nextTick();
		expect(wrapper.text()).toBe("Test");
	});

	it("supports pause and resume during animation", async () => {
		const wrapper = mount(MessageContent, {
			props: {
				content: "Hello",
				animate: true,
				speed: 30,
			},
		});

		// Advance timer to let it type a bit
		vi.advanceTimersByTime(100);
		await wrapper.vm.$nextTick();
		const currentText = wrapper.text();
		expect(currentText.length).toBeGreaterThan(0);

		wrapper.vm.pause();
		vi.advanceTimersByTime(300);
		await wrapper.vm.$nextTick();
		expect(wrapper.text()).toBe(currentText); // Should not change

		wrapper.vm.resume();
		vi.advanceTimersByTime(400);
		await wrapper.vm.$nextTick();
		expect(wrapper.text()).toBe("Hello");
	});

	it("supports interrupt to immediately display full text", async () => {
		const wrapper = mount(MessageContent, {
			props: {
				content: "Interrupt Me",
				animate: true,
				speed: 30,
			},
		});

		vi.advanceTimersByTime(50);
		await wrapper.vm.$nextTick();
		expect(wrapper.text().length).toBeLessThan("Interrupt Me".length);

		wrapper.vm.interrupt();
		await wrapper.vm.$nextTick();
		expect(wrapper.text()).toBe("Interrupt Me");
	});

	it("clears timer on unmount to prevent memory leaks", async () => {
		const wrapper = mount(MessageContent, {
			props: {
				content: "Some long text that takes time",
				animate: true,
				speed: 30,
			},
		});

		vi.advanceTimersByTime(100);

		const clearTimeoutSpy = vi.spyOn(window, "clearTimeout");
		wrapper.unmount();

		expect(clearTimeoutSpy).toHaveBeenCalled();
	});
});
