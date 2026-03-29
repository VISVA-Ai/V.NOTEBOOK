/**
 * NotesUI - Inline notes system for annotating chat messages
 * Allows users to highlight text and attach notes
 */
const NotesUI = {
    notes: [],
    sessionNotes: {},  // Grouped by sessionId
    currentSelection: null,

    init() {
        this.loadNotes();
        this.bindEvents();
    },

    bindEvents() {
        // Listen for text selection in chat messages
        const chatMessages = document.getElementById('chat-messages');
        if (!chatMessages) return;

        // On mouseup, check if there's a selection
        chatMessages.addEventListener('mouseup', (e) => {
            const selection = window.getSelection();
            if (selection && selection.toString().trim().length > 0) {
                this.showNoteTooltip(selection, e);
            }
        });

        // Close tooltip when clicking elsewhere
        document.addEventListener('click', (e) => {
            if (!e.target.closest('.note-tooltip') && !e.target.closest('.note-highlight')) {
                this.hideTooltip();
            }
        });
    },

    showNoteTooltip(selection, event) {
        const text = selection.toString().trim();
        if (text.length < 3) return; // Minimum selection length

        // Get the parent message element
        const messageEl = event.target.closest('.message');
        if (!messageEl) return;

        const messageId = messageEl.dataset.messageId;
        if (!messageId) return;

        this.currentSelection = {
            text,
            messageId,
            range: selection.getRangeAt(0).cloneRange()
        };

        // Remove existing tooltip
        this.hideTooltip();

        // Create tooltip
        const tooltip = document.createElement('div');
        tooltip.className = 'note-tooltip';
        tooltip.innerHTML = `
            <div class="note-tooltip-header">Add Note</div>
            <div class="note-quick-actions">
                <button class="note-quick-btn" onclick="NotesUI.addQuickNote('Important')">⭐ Important</button>
                <button class="note-quick-btn" onclick="NotesUI.addQuickNote('Verify later')">🔍 Verify</button>
                <button class="note-quick-btn" onclick="NotesUI.addQuickNote('Weak point')">⚠️ Weak</button>
            </div>
            <textarea class="note-input" placeholder="Add a custom note..." rows="2"></textarea>
            <div class="note-actions">
                <button class="btn btn-primary btn-sm" onclick="NotesUI.saveNote()">Save</button>
                <button class="btn btn-secondary btn-sm" onclick="NotesUI.hideTooltip()">Cancel</button>
            </div>
        `;

        // Position tooltip near selection
        const rect = this.currentSelection.range.getBoundingClientRect();
        tooltip.style.position = 'fixed';
        tooltip.style.top = `${rect.bottom + 10}px`;
        tooltip.style.left = `${Math.min(rect.left, window.innerWidth - 250)}px`;

        document.body.appendChild(tooltip);
    },

    addQuickNote(noteText) {
        if (!this.currentSelection) return;
        this.createNote(noteText);
    },

    saveNote() {
        const textarea = document.querySelector('.note-tooltip .note-input');
        if (!textarea || !this.currentSelection) return;

        const noteText = textarea.value.trim();
        if (!noteText) {
            alert('Please enter a note');
            return;
        }
        this.createNote(noteText);
    },

    createNote(noteText) {
        if (!this.currentSelection) return;

        const sessionId = State.data.currentSessionId || 'default';
        const note = {
            id: Date.now(),
            messageId: this.currentSelection.messageId,
            selectedText: this.currentSelection.text,
            note: noteText,
            createdAt: new Date().toISOString(),
            sessionId
        };

        // Add to notes array
        this.notes.push(note);

        // Group by session
        if (!this.sessionNotes[sessionId]) {
            this.sessionNotes[sessionId] = [];
        }
        this.sessionNotes[sessionId].push(note);

        // Save to localStorage
        this.saveNotes();

        // Highlight the text in the message
        this.highlightText(note);

        // Hide tooltip
        this.hideTooltip();

        // Notify state for InsightMemory integration (future)
        State.notify('noteAdded', note);
    },

    createStandaloneNote(noteText) {
        const sessionId = State.data.currentSessionId || 'default';
        const note = {
            id: Date.now(),
            messageId: 'standalone',
            selectedText: 'Evidence block',
            note: noteText,
            createdAt: new Date().toISOString(),
            sessionId
        };

        this.notes.push(note);
        if (!this.sessionNotes[sessionId]) {
            this.sessionNotes[sessionId] = [];
        }
        this.sessionNotes[sessionId].push(note);
        this.saveNotes();

        State.notify('noteAdded', note);
    },

    highlightText(note) {
        const messageEl = document.querySelector(`[data-message-id="${note.messageId}"]`);
        if (!messageEl) return;

        const msgContent = messageEl.querySelector('.msg-content');
        if (!msgContent) return;

        // Create highlighted span (simple approach - replace text)
        const escapedText = note.selectedText.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
        const regex = new RegExp(`(${escapedText})`, 'i');

        if (msgContent.innerHTML.match(regex)) {
            msgContent.innerHTML = msgContent.innerHTML.replace(
                regex,
                `<span class="note-highlight" data-note-id="${note.id}" onclick="NotesUI.showNote(${note.id})">$1</span>`
            );
        }
    },

    showNote(noteId) {
        const note = this.notes.find(n => n.id === noteId);
        if (!note) return;

        // Show note popup
        const popup = document.createElement('div');
        popup.className = 'note-popup';
        popup.innerHTML = `
            <div class="note-popup-header">
                <span>Your Note</span>
                <button onclick="this.closest('.note-popup').remove()">×</button>
            </div>
            <div class="note-popup-content">${this.escapeHtml(note.note)}</div>
            <div class="note-popup-meta">${new Date(note.createdAt).toLocaleDateString()}</div>
            <button class="btn btn-danger btn-sm" onclick="NotesUI.deleteNote(${noteId})">Delete Note</button>
        `;

        // Position near the highlight
        const highlight = document.querySelector(`[data-note-id="${noteId}"]`);
        if (highlight) {
            const rect = highlight.getBoundingClientRect();
            popup.style.position = 'fixed';
            popup.style.top = `${rect.bottom + 10}px`;
            popup.style.left = `${rect.left}px`;
        }

        // Remove any existing popup
        document.querySelectorAll('.note-popup').forEach(p => p.remove());
        document.body.appendChild(popup);
    },

    deleteNote(noteId) {
        // Remove from arrays
        this.notes = this.notes.filter(n => n.id !== noteId);

        for (const sessionId in this.sessionNotes) {
            this.sessionNotes[sessionId] = this.sessionNotes[sessionId].filter(n => n.id !== noteId);
        }

        // Remove highlight
        const highlight = document.querySelector(`[data-note-id="${noteId}"]`);
        if (highlight) {
            highlight.outerHTML = highlight.innerHTML;
        }

        // Remove popup
        document.querySelectorAll('.note-popup').forEach(p => p.remove());

        // Save
        this.saveNotes();
    },

    hideTooltip() {
        document.querySelectorAll('.note-tooltip').forEach(t => t.remove());
        this.currentSelection = null;
    },

    saveNotes() {
        try {
            localStorage.setItem('vnb_notes', JSON.stringify(this.notes));
        } catch (e) {
            console.error('Failed to save notes:', e);
        }
    },

    loadNotes() {
        try {
            const saved = localStorage.getItem('vnb_notes');
            if (saved) {
                this.notes = JSON.parse(saved);
                // Group by session
                this.notes.forEach(note => {
                    if (!this.sessionNotes[note.sessionId]) {
                        this.sessionNotes[note.sessionId] = [];
                    }
                    this.sessionNotes[note.sessionId].push(note);
                });
            }
        } catch (e) {
            console.error('Failed to load notes:', e);
        }
    },

    // Re-apply highlights when messages are rendered
    applyHighlights(sessionId) {
        const sessionNotes = this.sessionNotes[sessionId || State.data.currentSessionId] || [];
        sessionNotes.forEach(note => {
            this.highlightText(note);
        });
    },

    getSessionNotes(sessionId) {
        return this.sessionNotes[sessionId || State.data.currentSessionId] || [];
    },

    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
};

window.NotesUI = NotesUI;

// Initialize when DOM ready
document.addEventListener('DOMContentLoaded', () => {
    setTimeout(() => NotesUI.init(), 500);
});
