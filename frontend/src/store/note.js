import { defineStore } from "pinia";
import {
	createNote,
	deleteNote,
	deleteSummary,
	getNotesByArticle,
	getSummaryByArticle,
	saveSummary as apiSaveSummary,
	updateNote,
} from "../api/note";

export const useNoteStore = defineStore("note", {
	state: () => ({
		notes: [],
		summary: null,
		loading: false,
	}),
	actions: {
		async fetchNotes(articleId) {
			if (!articleId) {
				console.warn("fetchNotes called with invalid articleId:", articleId);
				return;
			}
			this.loading = true;
			try {
				const notes = await getNotesByArticle(articleId);
				this.notes = notes || [];
			} catch (error) {
				console.error("Failed to fetch notes:", error);
				// Do not block UI, just log
			} finally {
				this.loading = false;
			}
		},
		async addNote(noteData) {
			const note = await createNote(noteData);
			this.notes.push(note);
			return note;
		},
		async updateNote(id, data) {
			const updated = await updateNote(id, data);
			const index = this.notes.findIndex((n) => n.id === id);
			if (index !== -1) {
				this.notes[index] = updated;
			}
			return updated;
		},
		async removeNote(id) {
			await deleteNote(id);
			this.notes = this.notes.filter((n) => n.id !== id);
		},
		async fetchSummary(articleId) {
			try {
				const summary = await getSummaryByArticle(articleId);
				this.summary = summary;
			} catch (error) {
				console.error(error);
			}
		},
		async saveSummary(data) {
			const summary = await apiSaveSummary(data);
			this.summary = summary;
			return summary;
		},
		async removeSummary(id) {
			await deleteSummary(id);
			this.summary = null;
		},
	},
});
