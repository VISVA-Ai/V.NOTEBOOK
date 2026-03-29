/**
 * V.ASSISTANT — Decision Cockpit Frontend
 * Conversational command center with action previews,
 * recommendation cards, approval flow, and edit-before-send.
 */

const AssistantUI = {
    chatContainer: null,
    inputField: null,
    sessionId: 'assistant-default',

    async init() {
        const container = document.getElementById('workspace-assistant');
        if (!container) return;

        container.innerHTML = `
            <div class="assistant-workspace">
                <!-- Scrollable content area -->
                <div class="assistant-scroll hide-scrollbar">
                    <div style="max-width:48rem;margin:0 auto;padding:0 1.5rem;">
                        <!-- Hero Header -->
                        <section class="assistant-hero">
                            <h2>
                                <span class="material-symbols-outlined" style="font-size:2rem;color:#f59e0b;font-variation-settings:'FILL' 1">bolt</span>
                                V.ASSISTANT
                            </h2>
                            <p style="color:#414754;max-width:24rem;font-size:0.875rem;line-height:1.6;">
                                Your digital archivist and executive partner. Connected to your scholarly ecosystem.
                            </p>
                            <div id="provider-badges" style="display:flex;gap:0.5rem;margin-top:0.5rem;flex-wrap:wrap;justify-content:center;"></div>
                        </section>

                        <!-- Chat Feed -->
                        <div class="assistant-chat-feed" id="assistant-chat">
                            <div class="chat-message assistant">
                                <div class="assistant-avatar">
                                    <span class="material-symbols-outlined" style="font-variation-settings:'FILL' 1">bolt</span>
                                </div>
                                <div class="msg-bubble">
                                    Welcome to V.ASSISTANT — your controlled execution system.<br><br>
                                    I can help you <strong>send emails</strong>, <strong>manage calendar events</strong>,
                                    <strong>send WhatsApp messages</strong>, and more.<br><br>
                                    Every action requires your explicit approval before execution. Try something like:
                                    <ul style="margin:12px 0;padding-left:24px;line-height:1.8;">
                                        <li>"Send an email to john@example.com"</li>
                                        <li>"Create a meeting tomorrow at 3pm"</li>
                                        <li>"Check my inbox"</li>
                                    </ul>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>

                <!-- Fixed Bottom Input Area -->
                <div class="assistant-bottom">
                    <div class="assistant-bottom-inner">
                        <!-- Quick Action Chips -->
                        <div id="quick-actions" style="display:flex;gap:0.5rem;margin-bottom:1rem;overflow-x:auto;" class="hide-scrollbar">
                            <button class="quick-action-chip" onclick="AssistantUI.quickAction('Check my inbox')">
                                <span class="material-symbols-outlined" style="font-size:18px;color:#005bbf">mail</span>
                                Check Inbox
                            </button>
                            <button class="quick-action-chip" onclick="AssistantUI.quickAction('List my events today')">
                                <span class="material-symbols-outlined" style="font-size:18px;color:#005bbf">calendar_today</span>
                                Today's Events
                            </button>
                            <button class="quick-action-chip" onclick="AssistantUI.quickAction('Draft an email')">
                                <span class="material-symbols-outlined" style="font-size:18px;color:#005bbf">task</span>
                                Summarize Notes
                            </button>
                            <button class="quick-action-chip" onclick="AssistantUI.quickAction('Send a WhatsApp message')">
                                <span class="material-symbols-outlined" style="font-size:18px;color:#005bbf">history</span>
                                Recent Sources
                            </button>
                        </div>

                        <!-- Input Bar -->
                        <div class="assistant-input-wrap">
                            <button style="padding:12px;color:#8A8680;background:none;border:none;cursor:pointer;">
                                <span class="material-symbols-outlined">attachment</span>
                            </button>
                            <input type="text" class="assistant-input" id="assistant-input"
                                   placeholder="Instruct your digital assistant..."
                                   autocomplete="off" />
                            <button class="assistant-send-btn" id="assistant-send" onclick="AssistantUI.send()">Send</button>
                        </div>
                        <p style="text-align:center;font-family:'JetBrains Mono',monospace;font-size:8px;text-transform:uppercase;letter-spacing:0.2em;color:rgba(138,134,128,0.7);margin-top:12px;">
                            Shift + Enter for new line • V.ASSISTANT 1.0.4-BETA
                        </p>
                    </div>
                </div>
            </div>
        `;

        this.chatContainer = document.getElementById('assistant-chat');
        this.inputField = document.getElementById('assistant-input');

        // Enter key handler
        this.inputField.addEventListener('keydown', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                this.send();
            }
        });

        // Check provider status
        this.checkProviders();
    },

    // ── Send Message ─────────────────────────────────────────────

    async send() {
        const text = this.inputField.value.trim();
        if (!text) return;

        // Show user message
        this.addMessage('user', text);
        this.inputField.value = '';
        this.inputField.disabled = true;

        // Show typing indicator
        this.showTyping();

        try {
            const response = await API.assistantChat(text, this.sessionId);
            this.hideTyping();
            this.handleResponse(response);
        } catch (err) {
            this.hideTyping();
            this.addMessage('assistant', `Error: ${err.message}`);
        }

        this.inputField.disabled = false;
        this.inputField.focus();
    },

    quickAction(text) {
        this.inputField.value = text;
        this.send();
    },

    // ── Response Handler ─────────────────────────────────────────

    handleResponse(response) {
        switch (response.type) {
            case 'question':
                this.renderQuestion(response);
                break;
            case 'recommendation':
                this.renderRecommendations(response);
                break;
            case 'action_preview':
                this.renderActionPreview(response);
                break;
            case 'multi_action_preview':
                this.renderMultiActionPreview(response);
                break;
            case 'result':
                this.renderResult(response);
                break;
            case 'error':
                this.addMessage('assistant', `⚠️ ${response.message || response.error}`);
                break;
            default:
                this.addMessage('assistant', response.message || 'Response received.');
        }
    },

    // ── Render: Question ─────────────────────────────────────────

    renderQuestion(data) {
        let msgContent = this.escapeHtml(data.message);

        if (data.missing_fields && data.missing_fields.length > 0) {
            msgContent += `<div style="margin-top: 8px; font-size: 12px; color: #727785;">
                Missing: ${data.missing_fields.join(', ')}
            </div>`;
        }

        this.addMessage('assistant', msgContent);
    },

    // ── Render: Action Preview ───────────────────────────────────

    renderActionPreview(data) {
        const params = data.parameters || data.action_preview?.parameters || {};
        const actionId = data.action_id || data.action_preview?.action_id;
        const intent = data.intent || data.action_preview?.intent || 'unknown';
        const summary = data.summary || data.action_preview?.summary || '';
        const confLevel = data.confirmation_level || 'normal';

        let paramsHtml = '';
        const displayFields = ['to', 'subject', 'body', 'title', 'datetime', 'datetime_str',
            'attendees', 'location', 'message', 'contact_name'];
        for (const [key, val] of Object.entries(params)) {
            if (val && displayFields.includes(key)) {
                const displayVal = Array.isArray(val) ? val.join(', ') : String(val);
                paramsHtml += `
                    <div class="action-param">
                        <span class="action-param-label">${key}:</span>
                        <span class="action-param-value">${this.escapeHtml(displayVal)}</span>
                    </div>`;
            }
        }

        // Recommendations attached to preview
        let recsHtml = '';
        if (data.recommendations && data.recommendations.length > 0) {
            recsHtml = data.recommendations.map(r => `
                <div class="recommendation-card" style="margin-top: 8px;">
                    <div class="recommendation-kind">💡 ${r.kind}</div>
                    <div class="recommendation-reason">${this.escapeHtml(r.reason)}</div>
                    ${r.suggested_delay ? `<div style="font-size: 12px; color: var(--text-secondary);">Suggested: ${r.suggested_delay}</div>` : ''}
                </div>
            `).join('');
        }

        const confirmText = confLevel === 'strong'
            ? '⚠️ This is a destructive action. Are you sure?'
            : '';

        const html = `
            <div class="action-card" data-action-id="${actionId}">
                <div class="action-card-header">
                    <span class="action-intent-badge">${intent.replace(/_/g, ' ')}</span>
                    <span style="font-size: 11px; color: var(--text-secondary);">ID: ${actionId ? actionId.slice(0, 8) : '?'}...</span>
                </div>
                <div class="action-card-body">
                    <div class="action-summary">${this.escapeHtml(summary)}</div>
                    <div class="action-params">${paramsHtml}</div>
                    ${confirmText ? `<div style="margin-top: 8px; color: #ef4444; font-size: 12px;">${confirmText}</div>` : ''}
                    ${recsHtml}
                </div>
                <div class="action-card-actions">
                    <button class="btn-approve" onclick="AssistantUI.approveAction('${actionId}')">✓ Approve & Execute</button>
                    <button class="btn-edit" onclick="AssistantUI.editAction('${actionId}', ${JSON.stringify(params).replace(/"/g, '&quot;')})">✎ Edit</button>
                    <button class="btn-cancel" onclick="AssistantUI.cancelAction('${actionId}')">✕ Cancel</button>
                </div>
            </div>`;

        this.chatContainer.insertAdjacentHTML('beforeend', html);
        this.scrollToBottom();
    },

    // ── Render: Multi Action Preview ─────────────────────────────

    renderMultiActionPreview(data) {
        const preview = data.multi_action_preview || data;
        const actions = preview.actions || [];

        this.addMessage('assistant', preview.message || `${actions.length} actions ready for review:`);

        actions.forEach(a => this.renderActionPreview(a));

        if (preview.can_approve_all) {
            const groupId = preview.group_id;
            const html = `
                <div style="padding: 8px 0;">
                    <button class="btn-approve" onclick="AssistantUI.approveAll('${groupId}')">
                        ✓ Approve All (${actions.length})
                    </button>
                </div>`;
            this.chatContainer.insertAdjacentHTML('beforeend', html);
        }

        this.scrollToBottom();
    },

    // ── Render: Recommendations ──────────────────────────────────

    renderRecommendations(data) {
        if (data.message) {
            this.addMessage('assistant', data.message);
        }

        const recs = data.recommendations || [];
        recs.forEach(rec => {
            const html = `
                <div class="recommendation-card">
                    <div class="recommendation-kind">${this.getKindIcon(rec.kind)} ${rec.kind}</div>
                    <div class="recommendation-reason">${this.escapeHtml(rec.reason)}</div>
                    ${rec.suggested_delay ? `<div style="font-size: 12px; color: var(--text-secondary); margin-bottom: 8px;">⏱ ${rec.suggested_delay}</div>` : ''}
                    ${rec.confidence ? `
                        <div class="confidence-bar">
                            <div class="confidence-fill ${rec.confidence > 0.7 ? 'high' : rec.confidence > 0.4 ? 'medium' : 'low'}"
                                 style="width: ${rec.confidence * 100}%"></div>
                        </div>` : ''}
                    <div class="recommendation-actions" style="margin-top: 8px;">
                        <button class="btn-accept" onclick="AssistantUI.acceptRecommendation(${JSON.stringify(rec).replace(/"/g, '&quot;')})">Accept</button>
                        <button class="btn-dismiss">Dismiss</button>
                    </div>
                </div>`;
            this.chatContainer.insertAdjacentHTML('beforeend', html);
        });

        // Show analysis data if present
        if (data.data) {
            const d = data.data;
            let analysisHtml = '';

            if (d.action_items && d.action_items.length > 0) {
                analysisHtml += '<strong>Action Items:</strong><ul>' +
                    d.action_items.map(a => `<li>${this.escapeHtml(a.action)} ${a.deadline ? `(by ${a.deadline})` : ''}</li>`).join('') +
                    '</ul>';
            }
            if (d.deadlines && d.deadlines.length > 0) {
                analysisHtml += '<strong>Deadlines:</strong><ul>' +
                    d.deadlines.map(dl => `<li>${this.escapeHtml(dl.text)} → ${dl.parsed}</li>`).join('') +
                    '</ul>';
            }

            if (analysisHtml) {
                this.addMessage('assistant', analysisHtml);
            }
        }

        this.scrollToBottom();
    },

    // ── Render: Result ───────────────────────────────────────────

    renderResult(data) {
        const isSuccess = data.status === 'success';

        // Render rich data for lists if present
        let extraHtml = '';
        if (data.data?.emails && data.data.emails.length > 0) {
            extraHtml = '<div style="margin-top: 12px; display: flex; flex-direction: column; gap: 8px;">';
            data.data.emails.forEach(e => {
                const dateSplit = e.date ? e.date.split(' ')[0] : '';

                // Extract actual email address for the 'To' header
                let rawEmail = e.from;
                const emailMatch = e.from.match(/<([^>]+)>/);
                if (emailMatch) rawEmail = emailMatch[1];

                extraHtml += `
                    <div style="font-size: 13px; background: var(--bg-primary); padding: 8px 12px; border-radius: 6px; border: 1px solid var(--border-color);">
                        <div style="font-weight: 600; margin-bottom: 2px;">${this.escapeHtml(e.subject || '(No Subject)')}</div>
                        <div style="display: flex; justify-content: space-between; color: var(--text-secondary); font-size: 11px; margin-bottom: 6px;">
                            <span>${this.escapeHtml(e.from.split('<')[0].trim())}</span>
                            <span>${dateSplit}</span>
                        </div>
                        <div style="color: var(--text-primary); line-height: 1.4;">${this.escapeHtml(e.snippet)}...</div>
                        <div style="margin-top: 8px; display: flex; gap: 8px; flex-wrap: wrap;">
                            <button onclick="AssistantUI.fillQuickAction('reply', '${encodeURIComponent(rawEmail)}', '${encodeURIComponent(e.subject || '')}', '${encodeURIComponent(e.thread_id || '')}')" style="background: transparent; border: 1px solid var(--color-primary); color: var(--color-primary); padding: 4px 8px; font-size: 11px; border-radius: 4px; cursor: pointer;">✏️ Draft Reply</button>
                            <button onclick="AssistantUI.fillQuickAction('followup', '${encodeURIComponent(rawEmail)}', '${encodeURIComponent(e.subject || '')}', '${encodeURIComponent(e.thread_id || '')}')" style="background: transparent; border: 1px solid #f59e0b; color: #f59e0b; padding: 4px 8px; font-size: 11px; border-radius: 4px; cursor: pointer;">🔄 Follow Up</button>
                            <button onclick="AssistantUI.fillQuickAction('remind', '${encodeURIComponent(rawEmail)}', '${encodeURIComponent(e.subject || '')}', '')" style="background: transparent; border: 1px solid var(--text-secondary); color: var(--text-secondary); padding: 4px 8px; font-size: 11px; border-radius: 4px; cursor: pointer;">⏰ Remind Me</button>
                        </div>
                    </div>`;
            });
            extraHtml += '</div>';
        } else if (data.data?.events && data.data.events.length > 0) {
            extraHtml = '<div style="margin-top: 12px; display: flex; flex-direction: column; gap: 8px;">';
            data.data.events.forEach(e => {
                const dateObj = new Date(e.start);
                const timeStr = dateObj.toLocaleDateString() + ' ' + dateObj.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
                extraHtml += `
                    <div style="font-size: 13px; background: var(--bg-primary); padding: 8px 12px; border-radius: 6px; border: 1px solid var(--border-color);">
                        <div style="font-weight: 600; margin-bottom: 2px;">${this.escapeHtml(e.title || 'Untitled Event')}</div>
                        <div style="color: var(--text-secondary); font-size: 11px;">⏱ ${timeStr}</div>
                        ${e.location ? `<div style="color: var(--text-secondary); font-size: 11px; margin-top: 2px;">📍 ${this.escapeHtml(e.location)}</div>` : ''}
                        <div style="margin-top: 8px; display: flex; gap: 8px;">
                            <button onclick="AssistantUI.fillQuickAction('delete', '${encodeURIComponent(e.event_id || '')}', '')" style="background: transparent; border: 1px solid var(--color-danger, #ef4444); color: var(--color-danger, #ef4444); padding: 4px 8px; font-size: 11px; border-radius: 4px; cursor: pointer;">❌ Delete Event</button>
                        </div>
                    </div>`;
            });
            extraHtml += '</div>';
        }

        const html = `
            <div class="result-card ${isSuccess ? 'success' : 'failure'}">
                <div class="result-status">${isSuccess ? '✓ Success' : '✕ Failed'}</div>
                <div style="font-weight: 500;">${this.escapeHtml(data.message)}</div>
                ${extraHtml}
            </div>`;
        this.chatContainer.insertAdjacentHTML('beforeend', html);
        this.scrollToBottom();
    },

    // ── Actions ──────────────────────────────────────────────────

    fillQuickAction(type, senderEnc, subjectEnc, threadIdEnc) {
        const sender = decodeURIComponent(senderEnc);
        const subject = decodeURIComponent(subjectEnc);
        const threadId = threadIdEnc ? decodeURIComponent(threadIdEnc) : '';
        let msg;
        if (type === 'reply') {
            // Include thread_id for proper Gmail thread reply
            msg = threadId
                ? `Reply to thread ${threadId} from ${sender} regarding "${subject}"`
                : `Draft a reply to ${sender} regarding "${subject}"`;
        } else if (type === 'followup') {
            // Smart follow-up: auto-send for immediate LLM generation
            // Explicitly say "Draft a reply" so the NLP routes it as an ACTION,
            // and include body "follow up" so the backend vague-phrase detector triggers the LLM.
            msg = threadId
                ? `Draft a reply to thread ${threadId} from ${sender} regarding "${subject}" with the exact body: "follow up"`
                : `Draft a reply to ${sender} regarding "${subject}" with the exact body: "follow up"`;
            this.inputField.value = msg;
            this.inputField.focus();
            this.handleSend();
            return;
        } else if (type === 'remind') {
            msg = `Set a reminder tomorrow to reply to ${sender} about "${subject}"`;
        } else {
            msg = `Delete event with event_id: ${sender}`;
        }
        this.inputField.value = msg;
        this.inputField.focus();
    },

    async approveAction(actionId) {
        try {
            // Step 1: Approve
            await API.approveAction(actionId);
            this.addMessage('assistant', '✓ Action approved. Executing...');
            this.showTyping();

            // Step 2: Execute
            const result = await API.executeAction(actionId);
            this.hideTyping();

            if (result.success) {
                this.renderResult({ status: 'success', message: result.message || 'Action executed successfully.' });
            } else {
                this.renderResult({ status: 'failure', message: result.error || result.message || 'Execution failed.' });
            }

            // Remove the action card
            const card = this.chatContainer.querySelector(`[data-action-id="${actionId}"]`);
            if (card) card.style.opacity = '0.5';

        } catch (err) {
            this.hideTyping();
            this.addMessage('assistant', `⚠️ ${err.message}`);
        }
    },

    async cancelAction(actionId) {
        try {
            await API.cancelAction(actionId);
            this.addMessage('assistant', 'Action canceled.');
            const card = this.chatContainer.querySelector(`[data-action-id="${actionId}"]`);
            if (card) card.remove();
        } catch (err) {
            this.addMessage('assistant', `⚠️ ${err.message}`);
        }
    },

    editAction(actionId, params) {
        // Build edit modal
        const fields = ['to', 'subject', 'body', 'title', 'datetime', 'datetime_str',
            'message', 'location', 'attendees'];
        let fieldsHtml = '';
        for (const field of fields) {
            const val = params[field];
            if (val !== undefined && val !== null) {
                const isLong = field === 'body' || field === 'message';
                fieldsHtml += `
                    <div class="edit-field">
                        <label>${field}</label>
                        ${isLong
                        ? `<textarea id="edit-${field}">${this.escapeHtml(String(val))}</textarea>`
                        : `<input type="text" id="edit-${field}" value="${this.escapeHtml(String(val))}" />`
                    }
                    </div>`;
            }
        }

        const modalHtml = `
            <div class="edit-overlay" id="edit-overlay" onclick="if(event.target===this)this.remove()">
                <div class="edit-modal">
                    <h3>Edit Action</h3>
                    ${fieldsHtml}
                    <div class="edit-modal-actions">
                        <button class="btn-edit" onclick="document.getElementById('edit-overlay').remove()">Cancel</button>
                        <button class="btn-approve" onclick="AssistantUI.saveEdit('${actionId}')">Save Changes</button>
                    </div>
                </div>
            </div>`;

        document.body.insertAdjacentHTML('beforeend', modalHtml);
    },

    async saveEdit(actionId) {
        const fields = ['to', 'subject', 'body', 'title', 'datetime', 'datetime_str',
            'message', 'location'];
        const patch = {};

        for (const field of fields) {
            const el = document.getElementById(`edit-${field}`);
            if (el) {
                patch[field] = el.value;
            }
        }

        try {
            await API.editAction(actionId, patch);
            document.getElementById('edit-overlay')?.remove();
            this.addMessage('assistant', '✓ Action updated. Review the changes and approve when ready.');

            // Re-fetch and re-render
            const updated = await API.getAction(actionId);
            this.renderActionPreview({
                type: 'action_preview',
                action_id: updated.id,
                intent: updated.intent,
                parameters: updated.parameters,
                summary: `Updated: ${updated.intent.replace(/_/g, ' ')}`,
            });
        } catch (err) {
            this.addMessage('assistant', `⚠️ Edit failed: ${err.message}`);
        }
    },

    async approveAll(groupId) {
        // Approve all actions in a group
        try {
            const actions = await API.getActions('pending');
            const groupActions = actions.filter(a => a.parent_group_id === groupId);

            for (const action of groupActions) {
                await API.approveAction(action.id);
                const result = await API.executeAction(action.id);
                if (result.success) {
                    this.renderResult({ status: 'success', message: `${action.intent}: ${result.message}` });
                } else {
                    this.renderResult({ status: 'failure', message: `${action.intent}: ${result.error}` });
                }
            }
        } catch (err) {
            this.addMessage('assistant', `⚠️ ${err.message}`);
        }
    },

    acceptRecommendation(rec) {
        // Convert recommendation to a command
        const commands = {
            'follow_up': `Set a follow-up reminder for ${rec.suggested_delay || '2 days'}`,
            'reminder': `Set a reminder: ${rec.reason}`,
            'reply': 'Draft a reply',
            'calendar_event': 'Create a calendar event',
        };
        const cmd = commands[rec.kind] || `Act on: ${rec.reason}`;
        this.inputField.value = cmd;
        this.send();
    },

    // ── Provider Status ──────────────────────────────────────────

    async checkProviders() {
        try {
            const status = await API.request('/assistant/status');
            const container = document.getElementById('provider-badges');
            if (!container) return;

            const providers = [
                { name: 'Gmail', key: 'gmail', icon: '📧' },
                { name: 'Calendar', key: 'calendar', icon: '📅' },
                { name: 'WhatsApp', key: 'whatsapp', icon: '💬' },
            ];

            container.innerHTML = providers.map(p => `
                <span class="provider-badge ${status[p.key] ? 'connected' : ''}">
                    ${p.icon} ${p.name}
                </span>
            `).join('');
        } catch (err) {
            // Silently fail
        }
    },

    // ── Helpers ───────────────────────────────────────────────────

    addMessage(role, content) {
        const div = document.createElement('div');
        div.className = `chat-message ${role}`;

        if (role === 'user') {
            div.innerHTML = `<div class="msg-bubble">${content}</div>`;
        } else {
            div.innerHTML = `
                <div class="assistant-avatar">
                    <span class="material-symbols-outlined" style="font-variation-settings:'FILL' 1">bolt</span>
                </div>
                <div class="msg-bubble">${content}</div>
            `;
        }

        this.chatContainer.appendChild(div);
        this.scrollToBottom();
    },

    showTyping() {
        const html = `<div class="typing-indicator" id="typing-indicator">
            <div class="typing-dot"></div>
            <div class="typing-dot"></div>
            <div class="typing-dot"></div>
        </div>`;
        this.chatContainer.insertAdjacentHTML('beforeend', html);
        this.scrollToBottom();
    },

    hideTyping() {
        document.getElementById('typing-indicator')?.remove();
    },

    scrollToBottom() {
        const scrollContainer = document.querySelector('.assistant-scroll');
        if (scrollContainer) {
            scrollContainer.scrollTop = scrollContainer.scrollHeight;
        }
    },

    getKindIcon(kind) {
        const icons = {
            follow_up: '📨', reminder: '⏰', reply: '↩️',
            calendar_event: '📅', action_item: '✅',
        };
        return icons[kind] || '💡';
    },

    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    },
};

window.AssistantUI = AssistantUI;
