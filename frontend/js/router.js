const Router = {
    routes: {
        'notebook': { viewId: 'workspace-notebook', title: 'V.NOTEBOOK - Notebook' },
        'assistant': { viewId: 'workspace-assistant', title: 'V.NOTEBOOK - Assistant' }
    },

    init() {
        window.addEventListener('hashchange', () => this.handleRoute());
        this.handleRoute(); // Initial load
    },

    handleRoute() {
        const hash = window.location.hash.slice(1) || 'notebook';
        const route = this.routes[hash] ? hash : 'notebook';

        State.setWorkspace(route);
        // Ensure hash matches
        if (window.location.hash.slice(1) !== route) {
            window.history.replaceState(null, null, `#${route}`);
        }

        document.title = (this.routes[route] && this.routes[route].title) || 'V.NOTEBOOK';
    },

    navigate(path) {
        window.location.hash = path;
    }
};

// UI Updater for Workspace
State.subscribe((key, value) => {
    if (key === 'currentWorkspace') {
        const notebookView = document.getElementById('workspace-notebook');
        const assistantView = document.getElementById('workspace-assistant');
        const btnNotebook = document.getElementById('btn-notebook');
        const btnAssistant = document.getElementById('btn-assistant');

        if (!notebookView || !assistantView) {
            console.error("Workspace views not found!");
            return;
        }

        // Active button classes
        const activeClasses = ['text-primary', 'font-bold', 'border-primary'];
        const inactiveClasses = ['text-[#1b1c18]/60', 'font-medium', 'border-transparent'];

        if (value === 'notebook') {
            notebookView.classList.add('active');
            assistantView.classList.remove('active');

            if (btnNotebook) {
                inactiveClasses.forEach(c => btnNotebook.classList.remove(c));
                activeClasses.forEach(c => btnNotebook.classList.add(c));
            }
            if (btnAssistant) {
                activeClasses.forEach(c => btnAssistant.classList.remove(c));
                inactiveClasses.forEach(c => btnAssistant.classList.add(c));
            }
        } else {
            assistantView.classList.add('active');
            notebookView.classList.remove('active');

            if (btnAssistant) {
                inactiveClasses.forEach(c => btnAssistant.classList.remove(c));
                activeClasses.forEach(c => btnAssistant.classList.add(c));
            }
            if (btnNotebook) {
                activeClasses.forEach(c => btnNotebook.classList.remove(c));
                inactiveClasses.forEach(c => btnNotebook.classList.add(c));
            }

            // Trigger AssistantUI init if not already done
            if (window.AssistantUI && !AssistantUI.chatContainer) {
                AssistantUI.init();
            }
        }
    }
});
