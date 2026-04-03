/**
 * V.NOTEBOOK — Settings UI
 * Manages the settings modal: API keys, memory, preferences, integrations.
 */
const SettingsUI = {
    modal: null,
    isOpen: false,

    // ── Bootstrap ────────────────────────────────────────────────
    init() {
        this.modal = document.getElementById('settings-modal');
        if (!this.modal) return;

        // Close on backdrop click
        this.modal.addEventListener('click', (e) => {
            if (e.target === this.modal) this.close();
        });

        // Close on Escape
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape' && this.isOpen) this.close();
        });

        // Tab navigation
        this.modal.querySelectorAll('.settings-tab-btn').forEach(btn => {
            btn.addEventListener('click', () => this._switchTab(btn.dataset.tab));
        });

        // Wire up buttons
        document.getElementById('btn-save-keys')?.addEventListener('click', () => this.saveKeys());
        document.getElementById('btn-save-prefs')?.addEventListener('click', () => this.savePreferences());
        document.getElementById('btn-wipe-archive')?.addEventListener('click', () => this.wipeArchive());
        document.getElementById('btn-close-settings')?.addEventListener('click', () => this.close());

        // Toggle visibility buttons for API key fields
        this.modal.querySelectorAll('.toggle-visibility-btn').forEach(btn => {
            btn.addEventListener('click', () => {
                const input = btn.parentElement.querySelector('input');
                if (input.type === 'password') {
                    input.type = 'text';
                    btn.textContent = 'visibility_off';
                } else {
                    input.type = 'password';
                    btn.textContent = 'visibility';
                }
            });
        });

        // Handle OAuth success callback
        if (window.location.hash === '#settings-success') {
            window.location.hash = '';
            setTimeout(() => {
                this.open();
                this._switchTab('integrations');
                this._flash('Google integration authorized successfully!', 'success');
            }, 500);
        }
    },

    // ── Open / Close ─────────────────────────────────────────────
    async open() {
        // Lazy-init if init() hasn't run yet
        if (!this.modal) {
            this.modal = document.getElementById('settings-modal');
            if (this.modal) this.init();
        }
        if (!this.modal) {
            console.error('[Settings] Modal element not found');
            return;
        }
        this.modal.classList.add('active');
        this.isOpen = true;
        document.body.style.overflow = 'hidden';

        // Load data
        await Promise.all([
            this._loadKeysStatus(),
            this._loadMemoryStats(),
            this._loadPreferences(),
            this._loadAuthStatus(),
        ]);
    },

    async _loadAuthStatus() {
        const btn = document.getElementById('btn-google-login');
        const statusEl = document.getElementById('google-auth-status');
        if (!btn || !statusEl) return;

        try {
            const res = await fetch('/api/auth/google/status');
            const data = await res.json();

            if (!data.is_configured) {
                statusEl.innerHTML = '<span class="key-status unset">Not Configured</span> <br><span style="font-size:10px;color:#727785">Missing `credentials.json` on server.</span>';
                btn.style.opacity = '0.5';
                btn.style.pointerEvents = 'none';
                btn.title = 'credentials.json is required on the server to enable OAuth';
            } else if (data.is_authenticated) {
                statusEl.innerHTML = '<span class="key-status set">Authenticated</span> <br><span style="font-size:10px;color:#727785">Connected to Gmail & Calendar.</span>';
                btn.innerHTML = 'Reconnect Account';
            } else {
                statusEl.innerHTML = '<span class="key-status unset">Not Connected</span> <br><span style="font-size:10px;color:#727785">Ready for login.</span>';
                btn.innerHTML = `
                    <svg width="18" height="18" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 48 48"><path fill="#EA4335" d="M24 9.5c3.54 0 6.71 1.22 9.21 3.6l6.85-6.85C35.9 2.38 30.47 0 24 0 14.62 0 6.51 5.38 2.56 13.22l7.98 6.19C12.43 13.7 17.74 9.5 24 9.5z"/><path fill="#4285F4" d="M46.98 24.55c0-1.57-.15-3.09-.38-4.55H24v9.02h12.94c-.58 2.96-2.26 5.48-4.78 7.18l7.73 6c4.51-4.18 7.09-10.36 7.09-17.65z"/><path fill="#FBBC05" d="M10.53 28.59c-.48-1.45-.76-2.99-.76-4.59s.27-3.14.76-4.59l-7.98-6.19C.92 16.46 0 20.12 0 24c0 3.88.92 7.54 2.56 10.78l7.97-6.19z"/><path fill="#34A853" d="M24 48c6.48 0 11.93-2.13 15.89-5.81l-7.73-6c-2.15 1.45-4.92 2.3-8.16 2.3-6.26 0-11.57-4.22-13.47-9.91l-7.98 6.19C6.51 42.62 14.62 48 24 48z"/></svg>
                    Sign in with Google
                `;
            }
        } catch (e) {
            statusEl.textContent = 'Failed to check status.';
        }
    },

    close() {
        if (!this.modal) return;
        this.modal.classList.remove('active');
        this.isOpen = false;
        document.body.style.overflow = '';
    },

    // ── Tab Switching ────────────────────────────────────────────
    _switchTab(tabId) {
        // Deactivate all tabs & panels
        this.modal.querySelectorAll('.settings-tab-btn').forEach(b => b.classList.remove('active'));
        this.modal.querySelectorAll('.settings-panel').forEach(p => p.classList.remove('active'));

        // Activate selected
        this.modal.querySelector(`.settings-tab-btn[data-tab="${tabId}"]`)?.classList.add('active');
        document.getElementById(`settings-panel-${tabId}`)?.classList.add('active');
    },

    // ── Load API Key Status ──────────────────────────────────────
    async _loadKeysStatus() {
        try {
            const data = await API.getKeysStatus();
            this._setKeyIndicator('groq_api_key', data.groq_api_key);
            this._setKeyIndicator('gemini_api_key', data.gemini_api_key);
            this._setKeyIndicator('openai_api_key', data.openai_api_key);
            this._setKeyIndicator('anthropic_api_key', data.anthropic_api_key);
            this._setKeyIndicator('tavily_api_key', data.tavily_api_key);
            this._setKeyIndicator('whatsapp_api_token', data.whatsapp_api_token);

            // URL fields (not masked)
            const waUrl = document.getElementById('input-whatsapp_api_url');
            if (waUrl && data.whatsapp_api_url) waUrl.placeholder = data.whatsapp_api_url;
            const waPhone = document.getElementById('input-whatsapp_phone_number_id');
            if (waPhone && data.whatsapp_phone_number_id) waPhone.placeholder = data.whatsapp_phone_number_id;
        } catch (e) {
            console.warn('[Settings] Could not load key status:', e);
        }
    },

    _setKeyIndicator(keyName, maskedValue) {
        const indicator = document.getElementById(`status-${keyName}`);
        if (!indicator) return;

        if (maskedValue) {
            indicator.textContent = maskedValue;
            indicator.className = 'key-status set';
        } else {
            indicator.textContent = 'Not configured';
            indicator.className = 'key-status unset';
        }
    },

    // ── Save API Keys ────────────────────────────────────────────
    async saveKeys() {
        const btn = document.getElementById('btn-save-keys');
        const origText = btn.textContent;
        btn.textContent = 'Saving...';
        btn.disabled = true;

        const payload = {};
        const fields = [
            'groq_api_key', 'gemini_api_key', 'openai_api_key', 'anthropic_api_key',
            'tavily_api_key', 'whatsapp_api_url', 'whatsapp_api_token', 'whatsapp_phone_number_id'
        ];

        for (const f of fields) {
            const input = document.getElementById(`input-${f}`);
            if (input && input.value.trim()) {
                payload[f] = input.value.trim();
            }
        }

        if (Object.keys(payload).length === 0) {
            btn.textContent = origText;
            btn.disabled = false;
            this._flash('No changes to save.', 'warn');
            return;
        }

        try {
            const result = await API.saveKeys(payload);
            this._flash(`Saved ${result.updated_keys.length} key(s) successfully!`, 'success');
            // Clear inputs and reload status
            fields.forEach(f => {
                const input = document.getElementById(`input-${f}`);
                if (input) input.value = '';
            });
            await this._loadKeysStatus();
        } catch (e) {
            this._flash(`Error: ${e.message}`, 'error');
        } finally {
            btn.textContent = origText;
            btn.disabled = false;
        }
    },

    // ── Memory Stats ─────────────────────────────────────────────
    async _loadMemoryStats() {
        try {
            const data = await API.getMemoryStats();
            const el = document.getElementById('memory-stats-content');
            if (!el) return;

            const sourceCount = Object.keys(data.sources || {}).length;
            const sourceList = Object.entries(data.sources || {})
                .map(([name, chunks]) => `<div class="memory-source-item"><span class="source-name">${name}</span><span class="source-chunks">${chunks} chunks</span></div>`)
                .join('');

            el.innerHTML = `
                <div class="memory-stat-grid">
                    <div class="memory-stat-card">
                        <span class="material-symbols-outlined stat-icon">database</span>
                        <div class="stat-value">${data.total_chunks}</div>
                        <div class="stat-label">Knowledge Chunks</div>
                    </div>
                    <div class="memory-stat-card">
                        <span class="material-symbols-outlined stat-icon">description</span>
                        <div class="stat-value">${sourceCount}</div>
                        <div class="stat-label">Documents</div>
                    </div>
                    <div class="memory-stat-card">
                        <span class="material-symbols-outlined stat-icon">data_array</span>
                        <div class="stat-value">${data.index_size}</div>
                        <div class="stat-label">FAISS Vectors</div>
                    </div>
                </div>
                ${sourceList ? `<div class="memory-source-list"><h4>Indexed Sources</h4>${sourceList}</div>` : '<p class="empty-state">No documents indexed yet.</p>'}
            `;
        } catch (e) {
            console.warn('[Settings] Could not load memory stats:', e);
        }
    },

    async wipeArchive() {
        if (!confirm('⚠️ This will permanently delete ALL knowledge chunks from your archive. This cannot be undone.\n\nAre you sure?')) return;

        const btn = document.getElementById('btn-wipe-archive');
        btn.textContent = 'Wiping...';
        btn.disabled = true;

        try {
            await API.wipeMemory();
            this._flash('Archive wiped successfully.', 'success');
            await this._loadMemoryStats();
        } catch (e) {
            this._flash(`Error: ${e.message}`, 'error');
        } finally {
            btn.textContent = 'Wipe All Data';
            btn.disabled = false;
        }
    },

    // ── Preferences ──────────────────────────────────────────────
    async _loadPreferences() {
        try {
            const data = await API.getPreferences();
            const modelSel = document.getElementById('pref-default-model');
            if (modelSel) modelSel.value = data.default_model || 'llama-3.3-70b-versatile';

            const goalToggle = document.getElementById('pref-auto-goals');
            if (goalToggle) goalToggle.checked = data.auto_goal_inference !== false;

            const workspaceSel = document.getElementById('pref-default-workspace');
            if (workspaceSel) workspaceSel.value = data.default_workspace || 'notebook';

            const compactToggle = document.getElementById('pref-compact-mode');
            if (compactToggle) compactToggle.checked = !!data.compact_mode;
        } catch (e) {
            console.warn('[Settings] Could not load preferences:', e);
        }
    },

    async savePreferences() {
        const btn = document.getElementById('btn-save-prefs');
        const origText = btn.textContent;
        btn.textContent = 'Saving...';
        btn.disabled = true;

        const payload = {
            default_model: document.getElementById('pref-default-model')?.value,
            auto_goal_inference: document.getElementById('pref-auto-goals')?.checked,
            default_workspace: document.getElementById('pref-default-workspace')?.value,
            compact_mode: document.getElementById('pref-compact-mode')?.checked,
        };

        try {
            await API.savePreferences(payload);
            this._flash('Preferences saved!', 'success');
        } catch (e) {
            this._flash(`Error: ${e.message}`, 'error');
        } finally {
            btn.textContent = origText;
            btn.disabled = false;
        }
    },

    // ── Toast Flash ──────────────────────────────────────────────
    _flash(message, type = 'info') {
        const toast = document.getElementById('settings-toast');
        if (!toast) return;
        toast.textContent = message;
        toast.className = `settings-toast visible ${type}`;
        setTimeout(() => toast.classList.remove('visible'), 3000);
    }
};
