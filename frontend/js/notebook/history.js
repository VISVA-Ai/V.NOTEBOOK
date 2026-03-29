/**
 * HistoryUI - Chat session history with improved visual hierarchy
 */
const HistoryUI = {
    listContainer: null,
    tabBtn: null,
    sourcesTabBtn: null,
    panelHistory: null,
    panelSources: null,

    init() {
        this.listContainer = document.getElementById('history-list');
        this.tabBtn = document.getElementById('tab-btn-history');
        this.sourcesTabBtn = document.getElementById('tab-btn-sources');
        this.panelHistory = document.getElementById('panel-history');
        this.panelSources = document.getElementById('panel-sources');

        // Tab Switching Logic
        this.tabBtn.onclick = () => this.switchTab('history');
        this.sourcesTabBtn.onclick = () => this.switchTab('sources');

        // Event Delegation for history items
        if (this.listContainer) {
            this.listContainer.addEventListener('click', (e) => {
                // Delete button
                const deleteBtn = e.target.closest('.history-item-delete');
                if (deleteBtn) {
                    e.stopPropagation();
                    const item = deleteBtn.closest('.history-item');
                    const sessionId = item?.dataset?.sessionId;
                    if (sessionId) this.deleteSession(sessionId);
                    return;
                }

                // Session item click
                const item = e.target.closest('.history-item');
                if (item) {
                    const sessionId = item.dataset.sessionId;
                    const title = item.dataset.sessionTitle || 'Untitled';
                    if (sessionId) this.switchSession(sessionId, title);
                }
            });
        }

        // Initial Fetch
        this.loadHistory();
    },

    switchTab(tab) {
        if (tab === 'history') {
            this.tabBtn.classList.add('active');
            this.sourcesTabBtn.classList.remove('active');
            this.panelHistory.classList.add('active');
            this.panelHistory.classList.remove('hidden');
            this.panelSources.classList.remove('active');
            this.panelSources.classList.add('hidden');
            this.loadHistory();
        } else {
            this.sourcesTabBtn.classList.add('active');
            this.tabBtn.classList.remove('active');
            this.panelSources.classList.add('active');
            this.panelSources.classList.remove('hidden');
            this.panelHistory.classList.remove('active');
            this.panelHistory.classList.add('hidden');
        }
    },

    async loadHistory() {
        try {
            const sessions = await API.getSessions();
            this.renderList(sessions);
        } catch (e) {
            console.error("Failed to load history:", e);
            this.listContainer.innerHTML = `<div class="history-error">Failed to load history: ${e.message}</div>`;
        }
    },

    renderList(sessions) {
        if (!sessions || sessions.length === 0) {
            this.listContainer.innerHTML = `
                <div class="history-empty">
                    <div class="history-empty-icon">📁</div>
                    <div class="history-empty-text">No previous chats</div>
                </div>
            `;
            return;
        }

        const currentId = State.data.currentSessionId;

        // Group sessions by date
        const groups = this.groupByDate(sessions);

        let html = '';
        for (const [groupLabel, groupSessions] of Object.entries(groups)) {
            html += `
                <div class="history-group">
                    <div class="history-group-title">${groupLabel}</div>
                    ${groupSessions.map(s => this.renderItem(s, currentId)).join('')}
                </div>
            `;
        }

        this.listContainer.innerHTML = html;
    },

    renderItem(session, currentId) {
        const isActive = session.session_id === currentId;
        const timestamp = this.formatRelativeTime(new Date(session.created_at));
        const safeTitle = this.escapeHtml(session.title || 'Untitled');

        return `
            <div class="history-item ${isActive ? 'active' : ''}" 
                 data-session-id="${session.session_id}"
                 data-session-title="${safeTitle}"
                 style="cursor:pointer;">
                <div class="history-item-content">
                    <div class="history-item-title">${safeTitle}</div>
                    <div class="history-item-timestamp">${timestamp}</div>
                </div>
                <button class="history-item-delete" 
                        title="Delete permanently">
                    🗑️
                </button>
            </div>
        `;
    },

    groupByDate(sessions) {
        const groups = {
            'Today': [],
            'Yesterday': [],
            'This Week': [],
            'Older': []
        };

        const now = new Date();
        const today = new Date(now.getFullYear(), now.getMonth(), now.getDate());
        const yesterday = new Date(today);
        yesterday.setDate(yesterday.getDate() - 1);
        const weekAgo = new Date(today);
        weekAgo.setDate(weekAgo.getDate() - 7);

        sessions.forEach(s => {
            const date = new Date(s.created_at);
            const sessionDate = new Date(date.getFullYear(), date.getMonth(), date.getDate());

            if (sessionDate >= today) {
                groups['Today'].push(s);
            } else if (sessionDate >= yesterday) {
                groups['Yesterday'].push(s);
            } else if (sessionDate >= weekAgo) {
                groups['This Week'].push(s);
            } else {
                groups['Older'].push(s);
            }
        });

        // Remove empty groups
        const result = {};
        for (const [label, items] of Object.entries(groups)) {
            if (items.length > 0) {
                result[label] = items;
            }
        }
        return result;
    },

    formatRelativeTime(date) {
        const now = new Date();
        const diffMs = now - date;
        const diffMins = Math.floor(diffMs / 60000);
        const diffHours = Math.floor(diffMs / 3600000);
        const diffDays = Math.floor(diffMs / 86400000);

        if (diffMins < 1) return 'Just now';
        if (diffMins < 60) return `${diffMins}m ago`;
        if (diffHours < 24) return `${diffHours}h ago`;
        if (diffDays < 7) return `${diffDays}d ago`;

        return date.toLocaleDateString(undefined, { month: 'short', day: 'numeric' });
    },

    async switchSession(sessionId, title) {
        if (sessionId === State.data.currentSessionId) return;

        // Update State
        State.setSession(sessionId, title);

        // Clear current chat
        if (window.NotebookUI && NotebookUI.container) {
            NotebookUI.container.innerHTML = '';
        }

        // Load messages for this session
        await App.loadSession(sessionId);

        // Re-render list to update active state
        this.loadHistory();
    },

    async deleteSession(sessionId) {
        if (!confirm('Permanently delete this chat?')) {
            return;
        }

        console.log(`[HistoryUI] Attempting to delete session: ${sessionId}`);

        try {
            // Call the delete API
            await API.deleteSession(sessionId);
            console.log(`[HistoryUI] Session ${sessionId} deleted from backend.`);

            // Remove from UI immediately
            const itemEl = this.listContainer.querySelector(`[data-session-id="${sessionId}"]`);
            if (itemEl) {
                itemEl.classList.add('deleting');
                setTimeout(() => {
                    itemEl.remove();
                    // Check if group is now empty
                    this.cleanupEmptyGroups();
                }, 200);
            }

            // If this was the active session, clear and restore
            if (window.State && State.data.currentSessionId === sessionId) {
                console.log(`[HistoryUI] Active session deleted, resetting state...`);
                State.setSession(null, 'New Research');
                if (window.NotebookUI && NotebookUI.container) {
                    NotebookUI.container.innerHTML = '';
                    console.log(`[HistoryUI] Cleared chat container.`);
                }

                // Properly reset by loading the next available session or creating a new one
                if (window.App && window.App.restoreSession) {
                    console.log(`[HistoryUI] Restoring next available session...`);
                    await window.App.restoreSession();
                }
            } else {
                console.log(`[HistoryUI] Deleted session was not active. Active: ${State.data.currentSessionId}`);
            }

        } catch (e) {
            console.error('[HistoryUI] Failed to delete session:', e);
            alert('Failed to delete session: ' + e.message);
        }
    },

    cleanupEmptyGroups() {
        const groups = this.listContainer.querySelectorAll('.history-group');
        groups.forEach(group => {
            const items = group.querySelectorAll('.history-item');
            if (items.length === 0) {
                group.remove();
            }
        });

        // Check if all groups are gone
        if (this.listContainer.children.length === 0) {
            this.listContainer.innerHTML = `
                <div class="history-empty">
                    <div class="history-empty-icon">📁</div>
                    <div class="history-empty-text">No previous chats</div>
                </div>
            `;
        }
    },

    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    },

    escapeAttr(text) {
        return text.replace(/'/g, "\\'").replace(/"/g, '\\"');
    }
};

window.HistoryUI = HistoryUI;
