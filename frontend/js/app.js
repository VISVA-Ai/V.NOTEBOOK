const App = {
    async init() {
        console.log('V.NOTEBOOK Initializing...');

        // 1. Initialize API & State
        // (API is global, State is global)

        // 2. Initialize Views
        NotebookUI.init();
        AssistantUI.init();

        // Initialize Sub-components
        if (window.GoalsUI) GoalsUI.init();
        if (window.SourcesUI) SourcesUI.init();
        if (window.FlashcardsUI) FlashcardsUI.init();
        if (window.HistoryUI) HistoryUI.init();
        if (window.StudioUI) StudioUI.init();
        if (window.SettingsUI) SettingsUI.init();

        // 3. Initialize Router & Bind Global Events (Immediate response)
        Router.init();
        this.bindEvents();

        // 4. Session Management (Async restoration)
        await this.restoreSession();

        console.log('V.NOTEBOOK Ready.');
    },

    async restoreSession() {
        // Try to get last session from backend or local state
        // Current implementation of API.getSessions() returns list.
        // We might need an endpoint to get "current" or just load the most recent.

        try {
            const sessions = await API.getSessions();
            if (sessions && sessions.length > 0) {
                // Load most recent
                const lastSession = sessions[0];
                await this.loadSession(lastSession.session_id);
            } else {
                // No sessions, create new
                console.log("No sessions found, creating new...");
                const newSession = await API.createSession("New Research");
                await this.loadSession(newSession.session_id);
                // Refresh history since we just created one
                if (window.HistoryUI) HistoryUI.loadHistory();
            }
        } catch (e) {
            console.error("Failed to restore session:", e);
            // Fallback
            try {
                const newSession = await API.createSession("New Research");
                await this.loadSession(newSession.session_id);
                if (window.HistoryUI) HistoryUI.loadHistory();
            } catch (err2) {
                console.error("Critical: Cannot create session", err2);
            }
        }
    },

    async loadSession(sessionId) {
        try {
            const session = await API.getSession(sessionId);

            State.setSession(session.session_id, session.title);
            localStorage.setItem('last_session_id', session.session_id);

            // Update UI
            NotebookUI.renderMessages(session.messages || []);

            // Explicitly refresh session-scoped panels
            if (window.SourcesUI) SourcesUI.refresh();
            if (window.GoalsUI) GoalsUI.refresh();

        } catch (e) {
            console.error("Failed to load session:", e);
            if (e.message.includes("404")) {
                localStorage.removeItem('last_session_id');
            }
        }
    },

    bindEvents() {
        document.getElementById('btn-notebook').onclick = () => {
            console.log("Navigating to Notebook");
            Router.navigate('notebook');
        };
        document.getElementById('btn-assistant').onclick = () => {
            console.log("Navigating to Assistant");
            Router.navigate('assistant');
        };

        const newChatBtn = document.getElementById('btn-new-chat');
        if (newChatBtn) {
            newChatBtn.onclick = async () => {
                // If on assistant page, reset assistant context
                if (State.data.currentWorkspace === 'assistant') {
                    try {
                        await API.resetAssistantSession();
                        // Re-init the assistant UI
                        if (window.AssistantUI) {
                            await AssistantUI.init();
                        }
                    } catch (e) {
                        console.error("Failed to reset assistant session:", e);
                    }
                    return;
                }
                // Removed confirm prompt for better UX
                try {
                    const newSession = await API.createSession("New Research");
                    await this.loadSession(newSession.session_id);
                    if (window.HistoryUI) HistoryUI.loadHistory();
                } catch (e) {
                    alert("Failed to create new session: " + e.message);
                }
            };
        }

        // Theme Toggle
        const themeBtn = document.getElementById('theme-btn');
        if (themeBtn) {
            themeBtn.onclick = () => {
                State.toggleTheme();
                themeBtn.textContent = State.data.theme === 'dark' ? 'light_mode' : 'dark_mode';
            };
            // Set initial icon based on current theme
            themeBtn.textContent = State.data.theme === 'dark' ? 'light_mode' : 'dark_mode';
        }
    }
};

window.App = App;
// Ensure DOM content is loaded before init
document.addEventListener('DOMContentLoaded', () => {
    // Wait for other scripts (like StudioUI) to load
    setTimeout(() => App.init(), 100);
});
