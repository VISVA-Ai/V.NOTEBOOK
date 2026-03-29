const State = {
    data: {
        currentWorkspace: 'notebook', // 'notebook' | 'assistant'
        currentSessionId: null,
        sessionTitle: 'New Research',
        messages: [],
        sources: [],
        goals: [],
        dashboard: null, // Assistant dashboard data
        theme: 'dark',
        // Mode Lock
        sessionMode: null,         // Locked mode for current session
        sessionModeLocked: false   // Whether mode is locked
    },

    listeners: [],

    subscribe(listener) {
        this.listeners.push(listener);
        return () => {
            this.listeners = this.listeners.filter(l => l !== listener);
        };
    },

    notify(key, value) {
        this.listeners.forEach(listener => listener(key, value, this.data));
    },

    // Setters
    setWorkspace(workspace) {
        this.data.currentWorkspace = workspace;
        this.notify('currentWorkspace', workspace);
    },

    setSession(sessionId, title) {
        this.data.currentSessionId = sessionId;
        this.data.sessionTitle = title;
        // Reset mode lock on session change
        this.data.sessionMode = null;
        this.data.sessionModeLocked = false;
        this.notify('session', { id: sessionId, title });
    },

    addMessage(role, content, metadata = {}) {
        const msg = { role, content, metadata, timestamp: new Date() };
        this.data.messages.push(msg);
        this.notify('messages', this.data.messages);
    },

    setSources(sources) {
        this.data.sources = sources;
        this.notify('sources', sources);
    },

    setGoals(goals) {
        this.data.goals = goals;
        this.notify('goals', goals);
    },

    setDashboard(data) {
        this.data.dashboard = data;
        this.notify('dashboard', data);
    },

    toggleTheme() {
        this.data.theme = this.data.theme === 'dark' ? 'light' : 'dark';
        document.documentElement.setAttribute('data-theme', this.data.theme);
        // Tailwind darkMode: "class" requires toggling the 'dark' class on <html>
        document.documentElement.classList.toggle('dark', this.data.theme === 'dark');
        // Persist choice
        localStorage.setItem('vnotebook-theme', this.data.theme);
        this.notify('theme', this.data.theme);
    },

    // Mode Lock Methods
    lockSessionMode(mode) {
        this.data.sessionMode = mode;
        this.data.sessionModeLocked = true;
        this.notify('sessionMode', { mode, locked: true });
    },

    unlockSessionMode() {
        this.data.sessionModeLocked = false;
        this.notify('sessionMode', { mode: this.data.sessionMode, locked: false });
    },

    isModeLocked() {
        return this.data.sessionModeLocked;
    },

    getLockedMode() {
        return this.data.sessionModeLocked ? this.data.sessionMode : null;
    }
};

// CRITICAL: Make State available globally
window.State = State;

// Initialize Theme from localStorage or system preference
(function () {
    var savedTheme = localStorage.getItem('vnotebook-theme');
    if (savedTheme) {
        State.data.theme = savedTheme;
    } else if (window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches) {
        State.data.theme = 'dark';
    }
    document.documentElement.setAttribute('data-theme', State.data.theme);
    document.documentElement.classList.toggle('dark', State.data.theme === 'dark');
})();
