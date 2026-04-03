/**
 * QuizUI - Interactive multiple-choice quiz component
 * Renders directly into the chat container as a rich block
 */
const QuizUI = {
    questions: [],
    currentIndex: 0,
    answers: {},       // { questionIndex: selectedOptionIndex }
    revealed: {},      // { questionIndex: true }  — answer has been checked
    score: 0,
    quizComplete: false,

    /**
     * Load questions and render the quiz into the chat feed
     */
    loadQuiz(questions) {
        this.questions = questions || [];
        this.currentIndex = 0;
        this.answers = {};
        this.revealed = {};
        this.score = 0;
        this.quizComplete = false;
        this.renderInChat();
    },

    /**
     * Inject the quiz block into the main chat container
     */
    renderInChat() {
        const chatContainer = document.getElementById('chat-messages');
        if (!chatContainer) return;

        // Remove any previous quiz block
        const existing = document.getElementById('quiz-block');
        if (existing) existing.remove();

        const wrapper = document.createElement('div');
        wrapper.id = 'quiz-block';
        wrapper.className = 'nb-msg-wrapper system-wrapper';
        wrapper.style.maxWidth = '100%';

        wrapper.innerHTML = this.buildQuizHTML();
        chatContainer.appendChild(wrapper);

        // Scroll to quiz
        wrapper.scrollIntoView({ behavior: 'smooth', block: 'start' });
    },

    /**
     * Build the complete quiz HTML
     */
    buildQuizHTML() {
        if (this.questions.length === 0) {
            return `<div class="p-6 text-center text-on-surface-variant">No quiz questions available.</div>`;
        }

        if (this.quizComplete) {
            return this.buildResultsHTML();
        }

        const q = this.questions[this.currentIndex];
        const totalQ = this.questions.length;
        const currentNum = this.currentIndex + 1;
        const isAnswered = this.answers[this.currentIndex] !== undefined;
        const isRevealed = this.revealed[this.currentIndex] === true;
        const selectedIdx = this.answers[this.currentIndex];

        // Difficulty color
        const diffColors = {
            easy: { bg: 'bg-emerald-50', text: 'text-emerald-700', border: 'border-emerald-200' },
            medium: { bg: 'bg-amber-50', text: 'text-amber-700', border: 'border-amber-200' },
            hard: { bg: 'bg-red-50', text: 'text-red-700', border: 'border-red-200' }
        };
        const diff = diffColors[q.difficulty] || diffColors.medium;

        const optionsHTML = (q.options || []).map((opt, idx) => {
            let optionClasses = 'quiz-option group flex items-start gap-3 p-4 rounded-xl border-2 cursor-pointer transition-all duration-200';
            let indicatorClasses = 'w-7 h-7 rounded-full border-2 flex items-center justify-center flex-shrink-0 transition-all duration-200 text-xs font-bold';
            let iconInner = String.fromCharCode(65 + idx); // A, B, C, D
            
            if (isRevealed) {
                if (idx === q.correct) {
                    // Correct answer
                    optionClasses += ' border-emerald-400 bg-emerald-50';
                    indicatorClasses += ' border-emerald-500 bg-emerald-500 text-white';
                    iconInner = '✓';
                } else if (idx === selectedIdx && idx !== q.correct) {
                    // Wrong selection
                    optionClasses += ' border-red-400 bg-red-50';
                    indicatorClasses += ' border-red-500 bg-red-500 text-white';
                    iconInner = '✗';
                } else {
                    optionClasses += ' border-outline-variant/20 bg-surface-container-lowest/50 opacity-50';
                    indicatorClasses += ' border-outline-variant/40 text-on-surface-variant/40';
                }
            } else if (isAnswered && idx === selectedIdx) {
                // Selected but not yet revealed
                optionClasses += ' border-primary bg-primary/5 shadow-sm';
                indicatorClasses += ' border-primary bg-primary text-white';
            } else {
                optionClasses += ' border-outline-variant/20 bg-surface-container-lowest hover:border-primary/40 hover:bg-primary/5 hover:shadow-sm';
                indicatorClasses += ' border-outline-variant/40 text-on-surface-variant group-hover:border-primary/60 group-hover:text-primary';
            }

            return `
                <div class="${optionClasses}" onclick="QuizUI.selectOption(${idx})" role="button" tabindex="0">
                    <div class="${indicatorClasses}">${iconInner}</div>
                    <span class="text-sm leading-relaxed text-on-surface pt-0.5">${this.escapeHtml(opt)}</span>
                </div>
            `;
        }).join('');

        // Explanation (shown after reveal)
        const explanationHTML = isRevealed ? `
            <div class="mt-4 p-4 rounded-xl ${selectedIdx === q.correct ? 'bg-emerald-50 border border-emerald-200' : 'bg-amber-50 border border-amber-200'}">
                <div class="flex items-center gap-2 mb-2">
                    <span class="material-symbols-outlined text-sm ${selectedIdx === q.correct ? 'text-emerald-600' : 'text-amber-600'}" style="font-variation-settings: 'FILL' 1;">
                        ${selectedIdx === q.correct ? 'check_circle' : 'info'}
                    </span>
                    <span class="text-xs font-bold uppercase tracking-wider ${selectedIdx === q.correct ? 'text-emerald-700' : 'text-amber-700'}">
                        ${selectedIdx === q.correct ? 'Correct!' : 'Not quite'}
                    </span>
                </div>
                <p class="text-sm text-on-surface-variant leading-relaxed">${this.escapeHtml(q.explanation || 'No explanation provided.')}</p>
            </div>
        ` : '';

        // Action buttons
        let actionsHTML = '';
        if (!isRevealed && isAnswered) {
            actionsHTML = `
                <button class="w-full py-3 bg-primary text-white font-semibold rounded-xl hover:bg-primary-container transition-all shadow-lg shadow-primary/20 flex items-center justify-center gap-2"
                        onclick="QuizUI.checkAnswer()">
                    <span class="material-symbols-outlined text-sm">task_alt</span>
                    Check Answer
                </button>
            `;
        } else if (isRevealed) {
            if (this.currentIndex < totalQ - 1) {
                actionsHTML = `
                    <button class="w-full py-3 bg-primary text-white font-semibold rounded-xl hover:bg-primary-container transition-all shadow-lg shadow-primary/20 flex items-center justify-center gap-2"
                            onclick="QuizUI.nextQuestion()">
                        Next Question
                        <span class="material-symbols-outlined text-sm">arrow_forward</span>
                    </button>
                `;
            } else {
                actionsHTML = `
                    <button class="w-full py-3 bg-emerald-600 text-white font-semibold rounded-xl hover:bg-emerald-700 transition-all shadow-lg shadow-emerald-600/20 flex items-center justify-center gap-2"
                            onclick="QuizUI.showResults()">
                        <span class="material-symbols-outlined text-sm">emoji_events</span>
                        See Results
                    </button>
                `;
            }
        }

        // Progress dots
        const dotsHTML = this.questions.map((_, i) => {
            let dotClass = 'w-2.5 h-2.5 rounded-full transition-all duration-300 ';
            if (i === this.currentIndex) {
                dotClass += 'bg-primary scale-125 shadow-sm shadow-primary/30';
            } else if (this.revealed[i]) {
                dotClass += this.answers[i] === this.questions[i].correct ? 'bg-emerald-400' : 'bg-red-400';
            } else {
                dotClass += 'bg-outline-variant/30';
            }
            return `<div class="${dotClass}"></div>`;
        }).join('');

        return `
            <div class="bg-surface-container-lowest rounded-2xl border border-outline-variant/20 shadow-lg overflow-hidden">
                <!-- Header -->
                <div class="bg-gradient-to-r from-primary/10 via-primary/5 to-transparent p-5 border-b border-outline-variant/10">
                    <div class="flex items-center justify-between mb-3">
                        <div class="flex items-center gap-3">
                            <div class="w-9 h-9 rounded-xl bg-primary/10 flex items-center justify-center">
                                <span class="material-symbols-outlined text-primary text-lg" style="font-variation-settings: 'FILL' 1;">quiz</span>
                            </div>
                            <div>
                                <h3 class="text-sm font-bold text-on-surface">Knowledge Check</h3>
                                <p class="text-[10px] font-mono text-on-surface-variant/60 uppercase tracking-wider">Question ${currentNum} of ${totalQ}</p>
                            </div>
                        </div>
                        <span class="px-3 py-1 text-[10px] font-bold uppercase tracking-wider rounded-full ${diff.bg} ${diff.text} ${diff.border} border">${q.difficulty || 'medium'}</span>
                    </div>
                    <!-- Progress dots -->
                    <div class="flex items-center justify-center gap-2 mt-2">
                        ${dotsHTML}
                    </div>
                </div>

                <!-- Question body -->
                <div class="p-5">
                    <p class="text-base font-headline leading-relaxed text-on-surface mb-5">${this.escapeHtml(q.question)}</p>
                    
                    <!-- Options -->
                    <div class="flex flex-col gap-2.5">
                        ${optionsHTML}
                    </div>

                    ${explanationHTML}

                    <!-- Actions -->
                    <div class="mt-5">
                        ${actionsHTML}
                    </div>
                </div>
            </div>
        `;
    },

    /**
     * Build the final results screen
     */
    buildResultsHTML() {
        const total = this.questions.length;
        const pct = Math.round((this.score / total) * 100);
        
        let verdict = '', verdictColor = '', verdictIcon = '';
        if (pct >= 80) { verdict = 'Excellent!'; verdictColor = 'text-emerald-600'; verdictIcon = 'emoji_events'; }
        else if (pct >= 60) { verdict = 'Good job!'; verdictColor = 'text-primary'; verdictIcon = 'thumb_up'; }
        else if (pct >= 40) { verdict = 'Keep studying!'; verdictColor = 'text-amber-600'; verdictIcon = 'auto_stories'; }
        else { verdict = 'Review needed'; verdictColor = 'text-red-600'; verdictIcon = 'school'; }

        const breakdownHTML = this.questions.map((q, i) => {
            const isCorrect = this.answers[i] === q.correct;
            return `
                <div class="flex items-start gap-3 py-2.5 ${i < this.questions.length - 1 ? 'border-b border-outline-variant/10' : ''}">
                    <div class="w-6 h-6 rounded-full flex items-center justify-center flex-shrink-0 mt-0.5 ${isCorrect ? 'bg-emerald-100 text-emerald-600' : 'bg-red-100 text-red-600'}">
                        <span class="text-xs font-bold">${isCorrect ? '✓' : '✗'}</span>
                    </div>
                    <div class="flex-1 min-w-0">
                        <p class="text-xs text-on-surface leading-relaxed truncate">${this.escapeHtml(q.question)}</p>
                    </div>
                </div>
            `;
        }).join('');

        return `
            <div class="bg-surface-container-lowest rounded-2xl border border-outline-variant/20 shadow-lg overflow-hidden">
                <!-- Results Header -->
                <div class="bg-gradient-to-br from-primary/10 via-primary/5 to-emerald-50/50 p-8 text-center border-b border-outline-variant/10">
                    <div class="w-16 h-16 rounded-2xl bg-white shadow-lg flex items-center justify-center mx-auto mb-4">
                        <span class="material-symbols-outlined ${verdictColor} text-3xl" style="font-variation-settings: 'FILL' 1;">${verdictIcon}</span>
                    </div>
                    <h3 class="text-2xl font-headline ${verdictColor} mb-1">${verdict}</h3>
                    <p class="text-on-surface-variant text-sm">You scored <strong class="text-on-surface">${this.score}/${total}</strong> (${pct}%)</p>
                    
                    <!-- Score Bar -->
                    <div class="mt-4 mx-auto max-w-[200px]">
                        <div class="h-2.5 bg-outline-variant/20 rounded-full overflow-hidden">
                            <div class="h-full rounded-full transition-all duration-1000 ease-out ${pct >= 60 ? 'bg-emerald-500' : pct >= 40 ? 'bg-amber-500' : 'bg-red-500'}" 
                                 style="width: ${pct}%"></div>
                        </div>
                    </div>
                </div>

                <!-- Breakdown -->
                <div class="p-5">
                    <h4 class="text-[10px] font-mono font-bold uppercase tracking-widest text-on-surface-variant/50 mb-3">Question Breakdown</h4>
                    ${breakdownHTML}
                </div>

                <!-- Retake -->
                <div class="p-5 border-t border-outline-variant/10">
                    <button class="w-full py-3 bg-primary text-white font-semibold rounded-xl hover:bg-primary-container transition-all shadow-lg shadow-primary/20 flex items-center justify-center gap-2"
                            onclick="QuizUI.retake()">
                        <span class="material-symbols-outlined text-sm">refresh</span>
                        Retake Quiz
                    </button>
                </div>
            </div>
        `;
    },

    selectOption(idx) {
        if (this.revealed[this.currentIndex]) return; // Already answered
        this.answers[this.currentIndex] = idx;
        this.rerender();
    },

    checkAnswer() {
        const q = this.questions[this.currentIndex];
        const selected = this.answers[this.currentIndex];
        if (selected === undefined) return;
        
        this.revealed[this.currentIndex] = true;
        if (selected === q.correct) {
            this.score++;
        }
        this.rerender();
    },

    nextQuestion() {
        if (this.currentIndex < this.questions.length - 1) {
            this.currentIndex++;
            this.rerender();
            // Scroll quiz into view
            const block = document.getElementById('quiz-block');
            if (block) block.scrollIntoView({ behavior: 'smooth', block: 'start' });
        }
    },

    showResults() {
        this.quizComplete = true;
        this.rerender();
    },

    retake() {
        this.currentIndex = 0;
        this.answers = {};
        this.revealed = {};
        this.score = 0;
        this.quizComplete = false;
        this.rerender();
    },

    rerender() {
        const block = document.getElementById('quiz-block');
        if (block) {
            block.innerHTML = this.buildQuizHTML();
        }
    },

    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
};

window.QuizUI = QuizUI;
