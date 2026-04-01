describe("Chat Streaming E2E Test", () => {
	beforeEach(() => {
		// Intercept backend API calls to mock stream behavior
		cy.intercept("GET", "/api/v1/chat/models", {
			statusCode: 200,
			body: [{ id: "mock-model", name: "Mock Model" }],
		}).as("getModels");

		cy.intercept("POST", "/api/v1/chat/sessions", {
			statusCode: 200,
			body: { id: "session-123", title: "New Session" },
		}).as("createSession");

		cy.intercept("GET", "/api/v1/chat/sessions/session-123/messages", {
			statusCode: 200,
			body: [],
		}).as("getMessages");

		cy.visit("/");
		cy.wait("@getModels");
	});

	it("handles normal streaming correctly", () => {
		// Mock a normal stream response
		cy.intercept("POST", "/api/v1/chat/sessions/session-123/send", (req) => {
			req.reply({
				statusCode: 200,
				headers: {
					"Content-Type": "text/event-stream",
					"Cache-Control": "no-cache",
					Connection: "keep-alive",
				},
				body: 'data: {"content": "Hello "}\n\ndata: {"content": "World"}\n\n[DONE]\n\n',
			});
		}).as("sendMessage");

		// Type and send message
		cy.get("textarea.custom-textarea").type("Hi{enter}");

		cy.wait("@createSession");
		cy.wait("@getMessages");
		cy.wait("@sendMessage");

		// Wait for typewriter animation to complete
		// Speed is ~30-60ms per char, "Hello World" is 11 chars -> ~600ms
		cy.wait(1000);

		// Check if message is rendered
		cy.get(".message-wrapper.assistant")
			.last()
			.within(() => {
				cy.get(".markdown-body").should("contain.text", "Hello World");
			});
	});

	it("handles stream interruption when a new message is sent", () => {
		// Mock a slow stream
		cy.intercept("POST", "/api/v1/chat/sessions/session-123/send", (req) => {
			req.on("response", (res) => {
				res.setDelay(500); // delay to simulate slow network
			});
			req.reply({
				statusCode: 200,
				body: 'data: {"content": "Slow "}\n\ndata: {"content": "Response"}\n\n[DONE]\n\n',
			});
		}).as("sendMessageSlow");

		// Send first message
		cy.get("textarea.custom-textarea").type("First{enter}");
		cy.wait("@createSession");
		cy.wait("@getMessages");

		// While first message is streaming, send second message
		cy.get("textarea.custom-textarea").type("Second{enter}");

		// Wait for second message
		cy.wait("@sendMessageSlow");

		// Check that the first message stream was aborted/interrupted
		// and we have the new message showing
		cy.get(".message-wrapper.user").should("have.length", 2);
	});

	it("handles stream errors gracefully", () => {
		// Mock an error response
		cy.intercept("POST", "/api/v1/chat/sessions/session-123/send", {
			statusCode: 500,
			body: { detail: "Internal Server Error" },
		}).as("sendMessageError");

		// Send message
		cy.get("textarea.custom-textarea").type("Error{enter}");
		cy.wait("@createSession");
		cy.wait("@getMessages");
		cy.wait("@sendMessageError");

		// Arco design modal or message should appear
		cy.get(".arco-modal").should("contain.text", "Message Send Failed");
	});
});
