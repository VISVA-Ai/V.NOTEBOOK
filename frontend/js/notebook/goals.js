const GoalsUI = {
    async init() {
        this.render();
        // Subscribe to goal updates and session updates
        State.subscribe((key, val) => {
            if (key === 'goals') this.updateList(val);
            if (key === 'session') this.refresh();
        });
    },

    updateList(goals) {
        const container = document.getElementById('goals-list');
        if (!container) return;

        if (goals.length === 0) {
            container.innerHTML = `
                <div class="flex flex-col items-center justify-center p-6 text-center border border-dashed border-border rounded-lg bg-structure/50">
                    <div class="text-xl mb-2 opacity-50">🎯</div>
                    <div class="text-sm font-medium text-secondary">No Active Goals</div>
                    <div class="text-xs text-tertiary mt-1">Start a conversation to infer goals automatically.</div>
                </div>`;
            return;
        }

        container.innerHTML = goals.map(g => `
            <div class="mb-3 p-3 bg-surface rounded-lg border border-border shadow-sm hover:shadow-md transition-shadow">
                <div class="flex justify-between items-start mb-1">
                    <span class="font-display font-medium text-primary text-sm">${g.title}</span>
                    <span class="text-xs ${g.confidence > 0.8 ? 'text-mode-grounded' : 'text-text-tertiary'}">${Math.round(g.confidence * 100)}%</span>
                </div>
                <div class="text-xs text-secondary leading-snug mb-2">${g.description || 'No description'}</div>
                <div class="flex justify-between items-center border-t border-border pt-2 mt-2">
                    <span class="badge badge-low text-[10px] px-1.5 py-0.5">${g.source}</span>
                    <span class="text-[10px] text-tertiary">${g.touch_count || 0} interactions</span>
                </div>
            </div>
        `).join('');
    },

    render() {
        // Initial render logic if needed beyond updateList
    },

    async refresh() {
        // Called after every chat exchange or session switch to pick up newly inferred goals
        try {
            const sessionId = window.State ? State.data.currentSessionId : null;
            if (!sessionId) {
                State.setGoals([]);
                return;
            }
            const goals = await API.getGoals('active', sessionId);
            State.setGoals(goals);
        } catch (e) {
            console.error("Failed to refresh goals:", e);
        }
    }
};

// Initialize when notebook view loads?
// We can hook into app initialization or manual call
// Let's hook into window load or simply expose it
window.GoalsUI = GoalsUI;

// In chat.js or app.js, call GoalsUI.init()
document.addEventListener('DOMContentLoaded', () => {
    // Wait for view to be rendered?
    // chat.js renders the grid. So we must wait for chat.js init.
    // simpler: chat.js calls GoalsUI.init() after rendering grid.
});
