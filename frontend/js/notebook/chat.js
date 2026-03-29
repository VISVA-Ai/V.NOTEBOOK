const NotebookUI = {
    // State
    isProcessing: false,
    currentMode: 'Fast Mode',

    init() {
        console.log('NotebookUI Initializing...');

        // Cache DOM elements
        this.container = document.getElementById('chat-messages');
        this.input = document.getElementById('chat-input');
        this.sendBtn = document.getElementById('chat-send-btn');
        this.statusIndicator = document.getElementById('status-indicator');
        this.modeSelector = document.getElementById('mode-selector');

        if (!this.container || !this.input) {
            console.error("Critical: Chat UI elements not found!");
            return;
        }

        this.bindEvents();
        this.initModes();
    },

    bindEvents() {
        if (this.sendBtn) this.sendBtn.onclick = () => this.handleSend();
        if (this.input) {
            this.input.onkeydown = (e) => {
                if (e.key === 'Enter' && !e.shiftKey) {
                    e.preventDefault();
                    this.handleSend();
                }
            };
        }

        // Attach file button — triggers the existing sidebar PDF upload input
        const attachBtn = document.getElementById('btn-attach-file');
        const fileInput = document.getElementById('file-upload');
        if (attachBtn && fileInput) {
            attachBtn.onclick = () => fileInput.click();
        }

        // Voice input button — uses browser Web Speech API
        const voiceBtn = document.getElementById('btn-voice-input');
        if (voiceBtn) {
            voiceBtn.onclick = () => this.handleVoiceInput(voiceBtn);
        }
    },

    handleVoiceInput(btn) {
        const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
        if (!SpeechRecognition) {
            alert('Voice input is not supported in this browser. Try Chrome or Edge.');
            return;
        }

        const recognition = new SpeechRecognition();
        recognition.lang = 'en-US';
        recognition.interimResults = false;
        recognition.maxAlternatives = 1;

        // Visual feedback — turn icon red while listening
        const icon = btn.querySelector('.material-symbols-outlined');
        btn.classList.add('text-red-500');
        if (icon) icon.style.color = '#ef4444';

        recognition.onresult = (event) => {
            const transcript = event.results[0][0].transcript;
            if (this.input) {
                this.input.value += (this.input.value ? ' ' : '') + transcript;
                this.input.focus();
            }
        };

        recognition.onerror = (event) => {
            console.error('Speech recognition error:', event.error);
            if (event.error === 'not-allowed') {
                alert('Microphone access denied. Please allow microphone access in your browser settings.');
            }
        };

        recognition.onend = () => {
            btn.classList.remove('text-red-500');
            if (icon) icon.style.color = '';
        };

        recognition.start();
    },

    initModes() {
        if (!this.modeSelector) return;

        const modes = ['Fast Mode', 'Grounded Mode', 'Deep Research'];

        const renderModes = () => {
            const isLocked = State.isModeLocked();
            const lockedMode = State.getLockedMode();

            // If locked, show locked indicator
            const lockIndicator = isLocked
                ? `<span class="mode-lock-indicator" title="Mode locked for this session">🔒 ${lockedMode}</span>`
                : '';

            const modePills = modes.map(m => {
                const isActive = this.currentMode === m ? 'active' : '';
                const isDisabled = isLocked && m !== this.currentMode ? 'disabled' : '';
                return `<button class="mode-pill ${isActive} ${isDisabled}" 
                    onclick="NotebookUI.setMode('${m}')"
                    ${isDisabled ? 'disabled' : ''}>${m}</button>`;
            }).join('');

            const lockButton = isLocked
                ? `<button class="mode-lock-btn unlocked" onclick="NotebookUI.toggleModeLock()" title="Unlock mode">🔓</button>`
                : `<button class="mode-lock-btn locked" onclick="NotebookUI.toggleModeLock()" title="Lock mode for session">🔒</button>`;

            this.modeSelector.innerHTML = `
                ${lockIndicator}
                <div class="mode-pills-container">${modePills}</div>
                ${lockButton}
            `;
        };
        renderModes();
        this.renderModes = renderModes;

        // Subscribe to mode lock changes
        State.subscribe((key) => {
            if (key === 'sessionMode') this.renderModes();
        });
    },

    setMode(mode) {
        // Prevent mode change if locked
        if (State.isModeLocked()) {
            return;
        }
        this.currentMode = mode;
        if (this.renderModes) this.renderModes();
    },

    toggleModeLock() {
        if (State.isModeLocked()) {
            State.unlockSessionMode();
        } else {
            State.lockSessionMode(this.currentMode);
        }
    },

    async handleSend() {
        const query = this.input.value.trim();
        if (!query || this.isProcessing) return;

        // Clear input
        this.input.value = '';
        this.isProcessing = true;
        this.updateStatus('Thinking...');

        // Add User Message
        this.appendMessage('user', query);

        // Get Context
        const sessionId = State.data.currentSessionId;
        const mode = this.currentMode;

        const intentSelect = document.getElementById('session-intent');
        const intent = intentSelect ? intentSelect.value : 'Explore';
        const doNotLearnCheck = document.getElementById('do-not-learn-flag');
        const doNotLearn = doNotLearnCheck ? doNotLearnCheck.checked : false;

        try {
            // Send to Backend
            const result = await API.query(query, mode, sessionId, intent, doNotLearn);

            // Add AI Response with metadata for evidence
            const metadata = {
                sources: result.sources || [],
                confidence: result.confidence || 'medium',
                chunks: result.chunks || []
            };
            this.appendMessage('assistant', result.response, result.sources, metadata);

            // Add follow-up question chips (if provided by API)
            const followUps = result.follow_ups || this.generateFollowUps(result.response);
            if (followUps && followUps.length > 0) {
                this.showFollowUpChips(followUps);
            }

        } catch (e) {
            console.error("Query failed:", e);
            this.appendMessage('system', `Error: ${e.message}`);
        } finally {
            this.isProcessing = false;
            this.updateStatus('Ready');

            // Goals Update Trigger (if GoalsUI exists)
            if (window.GoalsUI) GoalsUI.refresh();
        }
    },

    generateFollowUps(response) {
        // Simple heuristic: generate follow-up questions based on keywords
        // In production, this would come from the AI backend
        const keywords = response.match(/\b(blockchain|consensus|security|energy|IoT|framework)\b/gi) || [];
        const unique = [...new Set(keywords.map(k => k.toLowerCase()))];

        if (unique.length >= 2) {
            return [
                `How does ${unique[0]} relate to ${unique[1]}?`,
                `What are the main challenges with ${unique[0]}?`,
                `Explain more about ${unique[1]} implementation.`
            ].slice(0, 3);
        }
        return [];
    },

    showFollowUpChips(questions) {
        const container = document.getElementById('chat-messages');
        if (!container) return;

        const chipsDiv = document.createElement('div');
        chipsDiv.className = 'follow-up-chips';
        chipsDiv.innerHTML = questions.map(q =>
            `<button class="follow-up-chip" onclick="NotebookUI.askFollowUp('${this.escapeAttr(q)}')">${q}</button>`
        ).join('');

        container.appendChild(chipsDiv);
        this.scrollToBottom();
    },

    askFollowUp(question) {
        // Remove chips
        document.querySelectorAll('.follow-up-chips').forEach(c => c.remove());

        // Set input and send
        this.input.value = question;
        this.handleSend();
    },

    escapeAttr(text) {
        return String(text).replace(/'/g, "\\'").replace(/"/g, '\\"');
    },

    appendMessage(role, content, sources = [], metadata = {}) {
        // Create the outer wrapper that controls layout
        const wrapper = document.createElement('div');
        wrapper.className = `nb-msg-wrapper ${role === 'user' ? 'user-wrapper' : role === 'assistant' ? 'assistant-wrapper' : 'system-wrapper'}`;
        wrapper.dataset.messageId = metadata.id || Date.now();

        // The actual message bubble
        const msgDiv = document.createElement('div');
        msgDiv.className = `message message-${role}`;

        // Try parsing JSON contract
        let parsed = null;
        let formattedContent = '';

        try {
            // Strip possible markdown ticks
            const cleanContent = content.replace(/```json/g, '').replace(/```javascript/g, '').replace(/```/g, '').trim();
            parsed = JSON.parse(cleanContent);
        } catch (e) {
            // Fallback to text if parsing fails
        }

        if (parsed && typeof parsed === 'object' && parsed.summary) {
            const summaryHtml = `<div class="block-summary">${this.escapeHtml(parsed.summary)}</div>`;
            const pointsHtml = parsed.key_points && parsed.key_points.length
                ? `<ul class="block-points">${parsed.key_points.map(p => `<li>${this.escapeHtml(p)}</li>`).join('')}</ul>`
                : '';
            const gapsHtml = parsed.gaps && parsed.gaps.length && parsed.gaps[0] !== ""
                ? `<div class="block-gaps"><strong>Gaps / Uncertainty:</strong> <ul>${parsed.gaps.map(g => `<li>${this.escapeHtml(g)}</li>`).join('')}</ul></div>`
                : '';

            formattedContent = summaryHtml + pointsHtml + gapsHtml;

            // Re-route evidence if provided tightly in JSON
            if (parsed.evidence && parsed.evidence.length > 0) {
                metadata.chunks = parsed.evidence;
                // If the backend didn't pass explicit sources, we can derive them.
                if (!sources || sources.length === 0) {
                    sources = [...new Set(parsed.evidence.map(e => e.source))];
                }
            }
        } else {
            // Markdown-to-HTML renderer
            let html = content.replace(/</g, "&lt;").replace(/>/g, "&gt;");

            // Headings (### before ## before #)
            html = html.replace(/^### (.+)$/gm, '<h4>$1</h4>');
            html = html.replace(/^## (.+)$/gm, '<h3>$1</h3>');
            html = html.replace(/^# (.+)$/gm, '<h2>$1</h2>');

            // Bold (**text**) — must run before italic
            html = html.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>');

            // Italic (*text*) — single asterisk not preceded/followed by another
            html = html.replace(/(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)/g, '<em>$1</em>');

            // Inline code (`text`)
            html = html.replace(/`([^`]+)`/g, '<code>$1</code>');

            // Numbered lists (1. item)
            html = html.replace(/^\d+\.\s+(.+)$/gm, '<ol><li>$1</li></ol>');
            html = html.replace(/<\/ol>\s*<ol>/g, '');

            // Bullet lists (* item or - item) — only match lines starting with * or - followed by space
            html = html.replace(/^[\*\-]\s+(.+)$/gm, '<ul><li>$1</li></ul>');
            html = html.replace(/<\/ul>\s*<ul>/g, '');

            // Line breaks
            formattedContent = html.replace(/\n/g, '<br>');
        }

        // Sanitize sources to prevent [object Object] from displaying
        const safeSources = (sources || []).map(s => {
            if (typeof s === 'string') return s;
            if (s && typeof s === 'object') return s.source || s.name || s.title || 'Unknown Source';
            return String(s);
        });
        const uniqueSources = [...new Set(safeSources)];

        // Evidence panel for Grounded / Deep Research modes (when we have sources)
        const showEvidence = role === 'assistant' && uniqueSources && uniqueSources.length > 0;
        const evidenceHtml = showEvidence ? this.buildEvidencePanel(uniqueSources, metadata) : '';

        // Source Citations (simple list)
        const sourcesHtml = uniqueSources && uniqueSources.length > 0
            ? `<div class="sources-list-item">Sources: ${uniqueSources.join(', ')}</div>`
            : '';

        // Save to Note + Feedback (for assistant messages only)
        const feedbackHtml = role === 'assistant' ? `
            <div class="message-actions">
                <button class="msg-action-btn save-to-note" onclick="NotebookUI.saveToNote(${wrapper.dataset.messageId})">
                    📌 Save to note
                </button>
                <button class="msg-action-btn feedback-btn" onclick="NotebookUI.sendFeedback(${wrapper.dataset.messageId}, 'up')" title="Helpful">👍</button>
                <button class="msg-action-btn feedback-btn" onclick="NotebookUI.sendFeedback(${wrapper.dataset.messageId}, 'down')" title="Not helpful">👎</button>
            </div>
        ` : '';

        msgDiv.innerHTML = `
            <div class="msg-content">${formattedContent}</div>
            ${sourcesHtml}
            ${feedbackHtml}
            ${evidenceHtml}
        `;

        // Build the wrapper with labels
        if (role === 'assistant') {
            const label = document.createElement('div');
            label.className = 'nb-msg-label';
            label.textContent = 'Assistant';
            wrapper.appendChild(label);
        }

        wrapper.appendChild(msgDiv);

        if (role === 'user') {
            const ts = document.createElement('span');
            ts.className = 'nb-msg-timestamp';
            const now = new Date();
            ts.textContent = `${now.toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'})}`;
            wrapper.appendChild(ts);
        }

        this.container.appendChild(wrapper);
        this.scrollToBottom();
    },

    buildEvidencePanel(sources, metadata = {}) {
        const confidence = metadata.confidence || 'medium';
        const chunks = metadata.chunks || [];

        const confidenceBadge = {
            high: '<span class="evidence-confidence high">High Confidence</span>',
            medium: '<span class="evidence-confidence medium">Medium Confidence</span>',
            low: '<span class="evidence-confidence low">Low Confidence</span>'
        }[confidence] || '';

        const chunksHtml = chunks.length > 0
            ? chunks.map((c, i) => `
                <div class="evidence-chunk">
                    <div class="evidence-chunk-header">
                        <span class="evidence-chunk-source">${this.escapeHtml(c.source || `Source ${i + 1}`)}</span>
                        ${c.score ? `<span class="evidence-chunk-score">${Math.round(c.score * 100)}% match</span>` : ''}
                    </div>
                    <div class="evidence-chunk-text">"${this.escapeHtml(c.text || c.content || c.quote || '')}"</div>
                    <div class="evidence-chunk-actions">
                        <button class="btn btn-small" onclick="NotebookUI.convertEvidenceToFlashcard(this)">Convert to Flashcard</button>
                        <button class="btn btn-small" onclick="NotebookUI.saveEvidenceToNote(this)">Save to Notes</button>
                    </div>
                </div>
            `).join('')
            : sources.map((s, i) => `
                <div class="evidence-chunk">
                    <div class="evidence-chunk-header">
                        <span class="evidence-chunk-source">${this.escapeHtml(s)}</span>
                    </div>
                     <div class="evidence-chunk-actions">
                        <button class="btn btn-small" onclick="NotebookUI.saveEvidenceToNote(this)">Save to Notes</button>
                    </div>
                </div>
            `).join('');

        return `
            <div class="evidence-section">
                <button class="evidence-toggle" onclick="NotebookUI.toggleEvidence(this)">
                    Show Evidence ▼
                </button>
                <div class="evidence-panel hidden">
                    <div class="evidence-header">
                        ${confidenceBadge}
                        <span class="evidence-count">${sources.length} source${sources.length > 1 ? 's' : ''} used</span>
                    </div>
                    <div class="evidence-chunks">
                        ${chunksHtml}
                    </div>
                </div>
            </div>
        `;
    },

    toggleEvidence(btn) {
        const panel = btn.nextElementSibling;
        if (panel) {
            const isHidden = panel.classList.contains('hidden');
            panel.classList.toggle('hidden');
            btn.textContent = isHidden ? 'Hide Evidence ▲' : 'Show Evidence ▼';
        }
    },

    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    },

    renderMessages(messages) {
        this.container.innerHTML = '';
        if (!messages) return;
        messages.forEach(m => {
            // Handle metadata for sources
            const sources = m.metadata?.sources || [];
            this.appendMessage(m.role, m.content, sources);
        });
        this.scrollToBottom();
    },

    scrollToBottom() {
        this.container.scrollTop = this.container.scrollHeight;
    },

    updateStatus(text) {
        // Optional status update
        if (this.statusIndicator) this.statusIndicator.innerText = text;
    },

    saveToNote(messageId) {
        const msgEl = document.querySelector(`[data-message-id="${messageId}"]`);
        if (!msgEl) return;

        const content = msgEl.querySelector('.msg-content')?.textContent || '';

        // Use NotesUI if available
        if (window.NotesUI && content) {
            NotesUI.createNote('Saved from response');
            alert('Saved to notes!');
        } else {
            // Fallback: copy to clipboard
            navigator.clipboard.writeText(content);
            alert('Content copied to clipboard!');
        }
    },

    sendFeedback(messageId, type) {
        console.log(`Feedback: ${type} for message ${messageId}`);
        // In production, send to backend
        const btn = event.target;
        btn.classList.add('feedback-sent');
        btn.disabled = true;
    },

    convertEvidenceToFlashcard(btn) {
        const chunkEl = btn.closest('.evidence-chunk');
        if (!chunkEl) return;
        const source = chunkEl.querySelector('.evidence-chunk-source')?.textContent || '';
        const text = chunkEl.querySelector('.evidence-chunk-text')?.textContent.replace(/^"|"$/g, '') || '';

        if (window.FlashcardsUI && text) {
            FlashcardsUI.createSingleCard(text, source);
            alert('Created flashcard from evidence!');
        } else {
            console.log("FlashcardsUI not ready", { source, text });
            alert('Flashcard from evidence feature triggered!');
        }
    },

    saveEvidenceToNote(btn) {
        const chunkEl = btn.closest('.evidence-chunk');
        if (!chunkEl) return;
        const source = chunkEl.querySelector('.evidence-chunk-source')?.textContent || '';
        const text = chunkEl.querySelector('.evidence-chunk-text')?.textContent || '';

        if (window.NotesUI && text) {
            NotesUI.createStandaloneNote(`Evidence from ${source}\n\n${text}`);
            alert('Evidence saved to notes!');
        } else {
            navigator.clipboard.writeText(`Source: ${source}\n\n${text}`);
            alert('Evidence copied to clipboard!');
        }
    },

    setupResultHandler() {
        // Listen for global events if needed
    }
};

window.NotebookUI = NotebookUI;

