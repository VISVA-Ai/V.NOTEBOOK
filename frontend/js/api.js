const API = {
    baseUrl: 'http://127.0.0.1:8000/api',

    // Helper for requests
    async request(endpoint, options = {}) {
        const url = `${this.baseUrl}${endpoint}`;
        const defaultHeaders = {
            'Content-Type': 'application/json'
        };

        const config = {
            ...options,
            headers: {
                ...defaultHeaders,
                ...options.headers
            }
        };

        try {
            const response = await fetch(url, config);
            if (!response.ok) {
                const errorBody = await response.json().catch(() => ({}));
                throw new Error(errorBody.detail || `HTTP Error: ${response.status}`);
            }
            return await response.json();
        } catch (error) {
            console.error(`API Error (${endpoint}):`, error);
            throw error;
        }
    },

    // === COMMON ===
    async healthCheck() {
        return this.request('/health');
    },

    async getSessions() {
        return this.request('/sessions');
    },

    async createSession(title) {
        return this.request('/sessions', {
            method: 'POST',
            body: JSON.stringify({ title })
        });
    },

    async getSession(sessionId) {
        return this.request(`/sessions/${sessionId}`);
    },

    async deleteSession(sessionId) {
        return this.request(`/sessions/${sessionId}`, {
            method: 'DELETE'
        });
    },

    // === NOTEBOOK ===
    async query(text, mode, sessionId, intent = 'Explore', doNotLearn = false) {
        return this.request('/notebook/query', {
            method: 'POST',
            body: JSON.stringify({
                query: text,
                mode: mode,
                session_id: sessionId,
                intent: intent,
                do_not_learn: doNotLearn
            })
        });
    },

    async uploadDocument(file, sessionId) {
        const formData = new FormData();
        formData.append('file', file);
        if (sessionId) formData.append('session_id', sessionId);

        const response = await fetch(`${this.baseUrl}/notebook/upload`, {
            method: 'POST',
            body: formData
        });

        if (!response.ok) {
            const errorBody = await response.json().catch(() => ({}));
            throw new Error(errorBody.detail || `Upload failed: ${response.status}`);
        }

        return await response.json();
    },

    async getSources() {
        return this.request('/notebook/sources');
    },

    async deleteSource(sourceId) {
        return this.request(`/notebook/sources/${encodeURIComponent(sourceId)}`, {
            method: 'DELETE'
        });
    },

    async getGraph() {
        return this.request('/notebook/graph');
    },

    // === COGNITIVE ===
    async getGoals(status = 'active', sessionId = null) {
        let url = `/notebook/goals?status=${status}`;
        if (sessionId) {
            url += `&session_id=${sessionId}`;
        }
        return this.request(url);
    },

    async createGoal(title, description, sessionId = "default") {
        return this.request('/notebook/goals', {
            method: 'POST',
            body: JSON.stringify({ title, description, source: 'user_declared', session_id: sessionId })
        });
    },

    async generateFlashcards(sessionId) {
        return this.request(`/notebook/flashcards?session_id=${sessionId}`, {
            method: 'POST'
        });
    },

    async generateAudioOverview() {
        const response = await fetch(`${this.baseUrl}/notebook/audio/overview`, {
            method: 'POST'
        });
        if (!response.ok) {
            const err = await response.json().catch(() => ({}));
            throw new Error(err.detail || 'Audio generation failed');
        }
        return response.json();
    },

    // === V.ASSISTANT ===
    async assistantChat(message, sessionId = 'default', threadContext = null) {
        return this.request('/assistant/chat', {
            method: 'POST',
            body: JSON.stringify({
                message: message,
                session_id: sessionId,
                thread_context: threadContext,
            })
        });
    },

    async getDashboard() {
        return this.request('/assistant/dashboard');
    },

    async getActions(status = null) {
        const query = status ? `?status=${status}` : '';
        return this.request(`/assistant/actions${query}`);
    },

    async getAction(actionId) {
        return this.request(`/assistant/actions/${actionId}`);
    },

    async approveAction(actionId) {
        return this.request(`/assistant/actions/${actionId}/approve`, {
            method: 'POST'
        });
    },

    async executeAction(actionId) {
        return this.request(`/assistant/actions/${actionId}/execute`, {
            method: 'POST'
        });
    },

    async cancelAction(actionId) {
        return this.request(`/assistant/actions/${actionId}/cancel`, {
            method: 'POST'
        });
    },

    async editAction(actionId, parameters) {
        return this.request(`/assistant/actions/${actionId}`, {
            method: 'PATCH',
            body: JSON.stringify({ parameters })
        });
    },

    async getProviderStatus() {
        return this.request('/assistant/status');
    },

    async resetAssistantSession(sessionId = 'assistant-default') {
        return this.request(`/assistant/reset?session_id=${sessionId}`, {
            method: 'POST'
        });
    }
};
