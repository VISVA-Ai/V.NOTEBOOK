const StudioUI = {
    init() {
        const cards = document.querySelectorAll('.studio-card');

        cards.forEach(card => {
            card.onclick = () => {
                const label = card.querySelector('.label').innerText.trim();
                this.handleAction(label);
            };
        });
    },

    async handleAction(label) {
        console.log("Studio Action:", label);

        let sessionId = State.data.currentSessionId;
        if (!sessionId) {
            sessionId = localStorage.getItem('last_session_id');
            if (sessionId) {
                State.data.currentSessionId = sessionId;
            }
        }

        if (!sessionId) {
            alert("No active session found. Please click 'New Chat' or select a history item.");
            return;
        }

        NotebookUI.updateStatus(`Generating ${label}...`);

        try {
            switch (label.toLowerCase()) {
                case 'brief':
                    await this.generateBrief(sessionId);
                    break;
                case 'flashcards':
                    await this.generateFlashcards(sessionId);
                    break;
                case 'quiz':
                    await this.generateQuiz(sessionId);
                    break;
                case 'audio':
                    await this.generateAudio();
                    break;
                case 'video':
                    await this.generateVideo();
                    break;
                case 'mind map':
                    await this.generateMindMap(sessionId);
                    break;
                case 'draft':
                case 'reports':
                    await this.generateReport(sessionId);
                    break;
                default:
                    console.warn("Unknown studio action:", label);
                    NotebookUI.appendMessage('system', `Feature '${label}' is not yet implemented.`);
            }
        } catch (e) {
            console.error(e);
            alert(`Failed to generate ${label}: ${e.message}`);
        } finally {
            NotebookUI.updateStatus("Ready");
        }
    },

    // ── BRIEF ──────────────────────────────────────────────────
    async generateBrief(sessionId) {
        NotebookUI.appendMessage('system', '📋 Generating executive brief from your sources...');

        const result = await API.generateBrief(sessionId);

        // Build beautiful brief HTML and inject it into chat
        const chatContainer = document.getElementById('chat-messages');
        if (!chatContainer) return;

        const wrapper = document.createElement('div');
        wrapper.className = 'nb-msg-wrapper system-wrapper';
        wrapper.style.maxWidth = '100%';

        const title = this.escapeHtml(result.title || 'Executive Brief');
        const summary = this.escapeHtml(result.summary || 'No summary available.');

        const findingsHTML = (result.key_findings || []).map((f, i) => `
            <div class="flex items-start gap-3 py-2">
                <div class="w-6 h-6 rounded-lg bg-primary/10 flex items-center justify-center flex-shrink-0">
                    <span class="text-[10px] font-bold text-primary">${i + 1}</span>
                </div>
                <span class="text-sm text-on-surface leading-relaxed">${this.escapeHtml(f)}</span>
            </div>
        `).join('');

        const entitiesHTML = (result.entities || []).map(e => `
            <span class="px-3 py-1.5 text-xs font-medium bg-primary/8 text-primary border border-primary/15 rounded-full">${this.escapeHtml(e)}</span>
        `).join('');

        const questionsHTML = (result.open_questions || []).map(q => `
            <div class="flex items-start gap-2 py-1.5">
                <span class="material-symbols-outlined text-amber-500 text-sm mt-0.5" style="font-variation-settings: 'FILL' 1;">help</span>
                <span class="text-sm text-on-surface-variant leading-relaxed">${this.escapeHtml(q)}</span>
            </div>
        `).join('');

        wrapper.innerHTML = `
            <div class="bg-surface-container-lowest rounded-2xl border border-outline-variant/20 shadow-lg overflow-hidden">
                <!-- Header -->
                <div class="bg-gradient-to-r from-primary/10 via-primary/5 to-transparent p-6 border-b border-outline-variant/10">
                    <div class="flex items-center gap-3 mb-2">
                        <div class="w-10 h-10 rounded-xl bg-primary/10 flex items-center justify-center">
                            <span class="material-symbols-outlined text-primary text-xl" style="font-variation-settings: 'FILL' 1;">summarize</span>
                        </div>
                        <div>
                            <h3 class="text-lg font-headline text-on-surface">${title}</h3>
                            <p class="text-[10px] font-mono text-on-surface-variant/50 uppercase tracking-widest">Executive Brief</p>
                        </div>
                    </div>
                </div>

                <!-- Summary -->
                <div class="p-6">
                    <p class="text-sm text-on-surface leading-[1.8] whitespace-pre-line">${summary}</p>
                </div>

                ${findingsHTML ? `
                <!-- Key Findings -->
                <div class="px-6 pb-4">
                    <h4 class="text-[10px] font-mono font-bold uppercase tracking-widest text-on-surface-variant/50 mb-3 flex items-center gap-2">
                        <span class="material-symbols-outlined text-xs text-primary" style="font-variation-settings: 'FILL' 1;">lightbulb</span>
                        Key Findings
                    </h4>
                    <div class="bg-surface-container-low/50 rounded-xl p-4 border border-outline-variant/10">
                        ${findingsHTML}
                    </div>
                </div>
                ` : ''}

                ${entitiesHTML ? `
                <!-- Key Entities -->
                <div class="px-6 pb-4">
                    <h4 class="text-[10px] font-mono font-bold uppercase tracking-widest text-on-surface-variant/50 mb-3 flex items-center gap-2">
                        <span class="material-symbols-outlined text-xs text-primary" style="font-variation-settings: 'FILL' 1;">category</span>
                        Key Entities
                    </h4>
                    <div class="flex flex-wrap gap-2">
                        ${entitiesHTML}
                    </div>
                </div>
                ` : ''}

                ${questionsHTML ? `
                <!-- Open Questions -->
                <div class="px-6 pb-6">
                    <h4 class="text-[10px] font-mono font-bold uppercase tracking-widest text-on-surface-variant/50 mb-3 flex items-center gap-2">
                        <span class="material-symbols-outlined text-xs text-amber-500" style="font-variation-settings: 'FILL' 1;">help</span>
                        Open Questions
                    </h4>
                    <div class="bg-amber-50/50 rounded-xl p-4 border border-amber-200/30">
                        ${questionsHTML}
                    </div>
                </div>
                ` : ''}
            </div>
        `;

        chatContainer.appendChild(wrapper);
        wrapper.scrollIntoView({ behavior: 'smooth', block: 'start' });
    },

    // ── QUIZ ──────────────────────────────────────────────────
    async generateQuiz(sessionId) {
        // Step 1: Fetch available topics and show selection dialog
        NotebookUI.updateStatus('Analyzing topics...');

        let topics = [];
        try {
            const topicResult = await API.getTopics(sessionId);
            topics = topicResult.topics || [];
        } catch (e) {
            console.warn('Topic extraction failed, showing dialog without topics:', e);
        }

        this.showQuizConfigDialog(sessionId, topics);
        NotebookUI.updateStatus('Ready');
    },

    showQuizConfigDialog(sessionId, topics) {
        const chatContainer = document.getElementById('chat-messages');
        if (!chatContainer) return;

        // Remove any existing config dialog
        const existing = document.getElementById('quiz-config-dialog');
        if (existing) existing.remove();

        const topicChipsHTML = topics.length > 0 
            ? topics.map(t => `
                <button class="quiz-topic-chip px-3 py-1.5 text-xs font-medium rounded-full border border-outline-variant/30 bg-surface-container-lowest text-on-surface hover:bg-primary/10 hover:border-primary/40 hover:text-primary transition-all cursor-pointer"
                        onclick="StudioUI.selectQuizTopic(this, '${this.escapeHtml(t).replace(/'/g, "\\'")}')"
                        data-topic="${this.escapeHtml(t)}">
                    ${this.escapeHtml(t)}
                </button>
            `).join('')
            : '<p class="text-xs text-on-surface-variant/50 italic">No specific topics detected — quiz will cover all content.</p>';

        const wrapper = document.createElement('div');
        wrapper.id = 'quiz-config-dialog';
        wrapper.className = 'nb-msg-wrapper system-wrapper';
        wrapper.style.maxWidth = '100%';

        wrapper.innerHTML = `
            <div class="bg-surface-container-lowest rounded-2xl border border-outline-variant/20 shadow-lg overflow-hidden">
                <!-- Header -->
                <div class="bg-gradient-to-r from-primary/10 via-primary/5 to-transparent p-5 border-b border-outline-variant/10">
                    <div class="flex items-center gap-3">
                        <div class="w-9 h-9 rounded-xl bg-primary/10 flex items-center justify-center">
                            <span class="material-symbols-outlined text-primary text-lg" style="font-variation-settings: 'FILL' 1;">quiz</span>
                        </div>
                        <div>
                            <h3 class="text-sm font-bold text-on-surface">Configure Your Quiz</h3>
                            <p class="text-[10px] font-mono text-on-surface-variant/60 uppercase tracking-wider">Choose topic & number of questions</p>
                        </div>
                    </div>
                </div>

                <div class="p-5 space-y-5">
                    <!-- Topic Selection -->
                    <div>
                        <label class="text-[10px] font-mono font-bold uppercase tracking-widest text-on-surface-variant/50 mb-3 block">
                            Select Topic
                        </label>
                        <div class="flex flex-wrap gap-2 mb-2">
                            <button class="quiz-topic-chip selected px-3 py-1.5 text-xs font-medium rounded-full border border-primary bg-primary/10 text-primary transition-all cursor-pointer"
                                    onclick="StudioUI.selectQuizTopic(this, 'all')"
                                    data-topic="all">
                                📚 All Topics
                            </button>
                            ${topicChipsHTML}
                        </div>
                    </div>

                    <!-- Number of Questions -->
                    <div>
                        <label class="text-[10px] font-mono font-bold uppercase tracking-widest text-on-surface-variant/50 mb-3 block">
                            Number of Questions
                        </label>
                        <div class="flex gap-2">
                            ${[3, 5, 7, 10].map(n => `
                                <button class="quiz-count-chip px-4 py-2 text-sm font-semibold rounded-xl border transition-all cursor-pointer
                                    ${n === 5 ? 'border-primary bg-primary/10 text-primary' : 'border-outline-variant/30 bg-surface-container-lowest text-on-surface hover:bg-primary/10 hover:border-primary/40 hover:text-primary'}"
                                    onclick="StudioUI.selectQuizCount(this, ${n})"
                                    data-count="${n}">
                                    ${n}
                                </button>
                            `).join('')}
                        </div>
                    </div>

                    <!-- Generate Button -->
                    <button id="quiz-generate-btn"
                            class="w-full py-3 bg-primary text-white font-semibold rounded-xl hover:bg-primary-container transition-all shadow-lg shadow-primary/20 flex items-center justify-center gap-2"
                            onclick="StudioUI.startQuizGeneration('${sessionId}')">
                        <span class="material-symbols-outlined text-sm">play_arrow</span>
                        Generate Quiz
                    </button>
                </div>
            </div>
        `;

        chatContainer.appendChild(wrapper);
        wrapper.scrollIntoView({ behavior: 'smooth', block: 'start' });

        // Store selection state
        this._quizTopic = 'all';
        this._quizCount = 5;
    },

    selectQuizTopic(btn, topic) {
        // Deselect all topic chips
        document.querySelectorAll('.quiz-topic-chip').forEach(c => {
            c.classList.remove('selected', 'border-primary', 'bg-primary/10', 'text-primary');
            c.classList.add('border-outline-variant/30', 'bg-surface-container-lowest', 'text-on-surface');
        });
        // Select this one
        btn.classList.remove('border-outline-variant/30', 'bg-surface-container-lowest', 'text-on-surface');
        btn.classList.add('selected', 'border-primary', 'bg-primary/10', 'text-primary');
        this._quizTopic = topic;
    },

    selectQuizCount(btn, count) {
        document.querySelectorAll('.quiz-count-chip').forEach(c => {
            c.classList.remove('border-primary', 'bg-primary/10', 'text-primary');
            c.classList.add('border-outline-variant/30', 'bg-surface-container-lowest', 'text-on-surface');
        });
        btn.classList.remove('border-outline-variant/30', 'bg-surface-container-lowest', 'text-on-surface');
        btn.classList.add('border-primary', 'bg-primary/10', 'text-primary');
        this._quizCount = count;
    },

    async startQuizGeneration(sessionId) {
        const topic = this._quizTopic || 'all';
        const count = this._quizCount || 5;

        // Remove config dialog
        const dialog = document.getElementById('quiz-config-dialog');
        if (dialog) dialog.remove();

        NotebookUI.appendMessage('system', `📝 Generating ${count}-question quiz${topic !== 'all' ? ` on "${topic}"` : ''}... This may take a moment.`);
        NotebookUI.updateStatus(`Generating quiz...`);

        try {
            const result = await API.generateQuiz(sessionId, topic, count);

            if (window.QuizUI && result.questions) {
                QuizUI.loadQuiz(result.questions);
            } else {
                NotebookUI.appendMessage('system', 'Quiz generation failed. Please try again.');
            }
        } catch (e) {
            console.error(e);
            NotebookUI.appendMessage('system', `Failed to generate quiz: ${e.message}`);
        } finally {
            NotebookUI.updateStatus('Ready');
        }
    },

    // ── FLASHCARDS ────────────────────────────────────────────
    async generateFlashcards(sessionId) {
        const result = await API.generateFlashcards(sessionId);
        NotebookUI.appendMessage('system', '🗂️ Flashcards generated! Check the Flashcards panel on the right.');

        if (window.FlashcardsUI) {
            FlashcardsUI.loadCards(result.cards);
        }
    },

    // ── AUDIO ─────────────────────────────────────────────────
    async generateAudio() {
        NotebookUI.appendMessage('system', 'Generating audio overview... This may take a moment.');

        const data = await API.generateAudioOverview();

        if (!AudioPlayerUI.container) {
            AudioPlayerUI.init('#audio-player-container');
        }

        const rawSentences = (data.transcript || '').match(/[^.!?]+[.!?]+/g) || [(data.transcript || 'Audio generated.')];
        const transcriptData = rawSentences.map(text => ({ text: text.trim(), startTime: 0, endTime: 0 }));

        await AudioPlayerUI.load(data.audio, transcriptData);

        NotebookUI.appendMessage('system', '🎧 Audio overview ready! Use the player controls on the right.');
    },

    // ── PLACEHOLDERS ──────────────────────────────────────────
    async generateVideo() {
        NotebookUI.appendMessage('system', '📹 Video Overview coming soon! This feature will generate a video summary of your research.');
    },

    async generateMindMap(sessionId) {
        NotebookUI.appendMessage('system', '🕸️ Mind Map generation coming soon! This feature will visualize connections between concepts.');
    },

    async generateReport(sessionId) {
        NotebookUI.appendMessage('system', '📊 Report generation coming soon! This feature will create a structured research report.');
    },

    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
};

window.StudioUI = StudioUI;

document.addEventListener('DOMContentLoaded', () => {
    setTimeout(() => StudioUI.init(), 500);
});
