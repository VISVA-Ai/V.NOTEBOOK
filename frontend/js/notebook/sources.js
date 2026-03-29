const SourcesUI = {
    init() {
        this.list = document.getElementById('sources-list');
        this.uploadBtn = document.getElementById('btn-upload');
        this.fileInput = document.getElementById('file-upload');

        this.bindEvents();

        State.subscribe((key, val) => {
            if (key === 'sources') this.render(val);
        });

        this.refresh();
    },

    bindEvents() {
        if (!this.uploadBtn || !this.fileInput) return;

        this.uploadBtn.onclick = () => this.fileInput.click();

        this.fileInput.onchange = async (e) => {
            const file = e.target.files[0];
            if (!file) return;

            // Basic validation
            if (file.type !== 'application/pdf') {
                alert("Only PDF files are supported currently.");
                return;
            }

            // Update UI
            const originalText = this.uploadBtn.innerText;
            this.uploadBtn.innerText = "Wait...";
            this.uploadBtn.disabled = true;

            try {
                const sessionId = State.data.currentSessionId;
                // Actually upload
                await API.uploadDocument(file, sessionId);

                // Refresh list
                const data = await API.getSources();
                State.setSources(data.sources || []);

                alert("Uploaded successfully!");
            } catch (err) {
                console.error("Upload error", err);
                alert("Upload failed: " + err.message);
            } finally {
                this.uploadBtn.innerText = originalText;
                this.uploadBtn.disabled = false;
                this.fileInput.value = '';
            }
        };
    },

    async refresh() {
        try {
            const data = await API.getSources();
            // Handle both Array return or { sources: [...] } return
            const sourcesList = Array.isArray(data) ? data : (data.sources || []);
            State.setSources(sourcesList);
        } catch (e) {
            console.error("Failed to fetch sources", e);
        }
    },

    render(sources) {
        const container = document.getElementById('sources-list');
        if (!container) return;

        // Defensive check
        if (!Array.isArray(sources)) {
            console.warn("Render expected array, got:", sources);
            container.innerHTML = `<div class="text-error text-xs p-2">Error loading sources.</div>`;
            return;
        }

        if (sources.length === 0) {
            container.innerHTML = `<div class="text-sm text-tertiary p-2">No sources uploaded.</div>`;
            return;
        }

        container.innerHTML = sources.map(s => {
            const sourceId = s.id || s.source || s.filename;
            const sourceName = s.source || s.filename || 'Unknown';
            return `
                <div class="source-item" data-source-id="${this.escapeAttr(sourceId)}">
                    <div class="source-info">
                        <div class="font-medium truncate" style="max-width: 160px;" title="${this.escapeAttr(sourceName)}">
                            ${this.escapeHtml(sourceName)}
                        </div>
                        <div class="text-xs text-secondary flex justify-between">
                            <span>${s.chunk_count || 0} chunks</span>
                            <span>PDF</span>
                        </div>
                    </div>
                    <button class="source-delete-btn" 
                            onclick="SourcesUI.deleteSource('${this.escapeAttr(sourceId)}', event)"
                            title="Delete source">×</button>
                </div>
            `;
        }).join('');
    },

    async deleteSource(sourceId, event) {
        if (event) event.stopPropagation();

        if (!confirm('Delete this source?\n\nThis will remove the document and all its data.')) {
            return;
        }

        try {
            await API.deleteSource(sourceId);

            // Remove from UI immediately
            const item = document.querySelector(`[data-source-id="${sourceId}"]`);
            if (item) {
                item.style.opacity = '0';
                item.style.transform = 'translateX(-10px)';
                setTimeout(() => item.remove(), 200);
            }

            // Refresh sources list
            setTimeout(() => this.refresh(), 250);

        } catch (e) {
            console.error('Failed to delete source:', e);
            alert('Failed to delete source: ' + e.message);
        }
    },

    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    },

    escapeAttr(text) {
        return String(text).replace(/'/g, "\\'").replace(/"/g, '\\"');
    }
};

window.SourcesUI = SourcesUI;

