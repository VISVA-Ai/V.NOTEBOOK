/**
 * FlashcardsUI - Interactive flashcard system with navigation
 */
const FlashcardsUI = {
    // State
    cards: [],
    currentIndex: 0,
    isFlipped: false,
    container: null,

    init() {
        this.container = document.getElementById('flashcard-container');
        if (!this.container) return;

        // Initial empty state
        this.renderEmptyState();

        // Bind keyboard events
        document.addEventListener('keydown', (e) => this.handleKeydown(e));
    },

    renderEmptyState() {
        this.container.innerHTML = `
            <div class="flashcard-empty">
                <div class="text-center p-4">
                    <p class="text-sm text-tertiary mb-2">Generate flashcards from grounded research.</p>
                    <button class="btn btn-secondary text-xs w-full" onclick="FlashcardsUI.generate()">+ Generate</button>
                </div>
            </div>
        `;
    },

    async generate() {
        if (!State.data.currentSessionId) {
            return alert("Start a session first.");
        }

        const btn = this.container.querySelector('button');
        if (btn) {
            btn.textContent = 'Generating...';
            btn.disabled = true;
        }

        try {
            const result = await API.generateFlashcards(State.data.currentSessionId);
            this.cards = result.cards || [];
            this.currentIndex = 0;
            this.isFlipped = false;
            this.render();
        } catch (e) {
            if (btn) {
                btn.textContent = '+ Generate';
                btn.disabled = false;
            }
            alert(e.message);
        }
    },

    render() {
        if (this.cards.length === 0) {
            this.container.innerHTML = `
                <div class="flex flex-col items-center justify-center p-8 text-center border-2 border-dashed border-outline-variant/30 rounded-2xl bg-surface">
                    <div class="text-3xl mb-2 opacity-50">🗂️</div>
                    <div class="text-sm font-medium text-on-surface-variant">No Flashcards</div>
                    <div class="text-xs text-on-surface-variant/50 mt-1">Use 'Grounded Mode' to unlock.</div>
                    <button class="px-4 py-2 mt-4 text-xs font-medium bg-surface-variant hover:bg-surface-container text-on-surface rounded-lg transition-colors border border-outline-variant/20 shadow-sm" onclick="FlashcardsUI.generate()">+ Generate</button>
                </div>
            `;
            return;
        }

        const card = this.cards[this.currentIndex];
        const totalCards = this.cards.length;
        const currentNum = this.currentIndex + 1;

        this.container.innerHTML = `
            <div class="flex flex-col gap-4 w-full">
                <!-- Progress Indicator -->
                <div class="flex items-center gap-3">
                    <span class="text-[10px] font-mono font-bold text-on-surface-variant whitespace-nowrap">${currentNum} / ${totalCards}</span>
                    <div class="flex-1 h-1.5 bg-outline-variant/20 rounded-full overflow-hidden">
                        <div class="h-full bg-primary transition-all duration-300 ease-out" style="width: ${(currentNum / totalCards) * 100}%"></div>
                    </div>
                </div>

                <!-- 3D Flashcard -->
                <div class="flashcard group relative w-full h-[220px] cursor-pointer focus:outline-none focus:ring-2 ring-primary/30 rounded-2xl" 
                     style="perspective: 1200px;" 
                     onclick="FlashcardsUI.flipCard()" 
                     tabindex="0">
                    
                    <div class="flashcard-inner w-full h-full relative transition-transform duration-[600ms] ease-[cubic-bezier(0.23,1,0.32,1)]" 
                         style="transform-style: preserve-3d; ${this.isFlipped ? 'transform: rotateY(180deg);' : ''}">
                        
                        <!-- Front Face -->
                        <div class="absolute inset-0 w-full h-full flex flex-col p-5 bg-surface rounded-2xl border border-outline-variant/30 shadow-sm backface-hidden" 
                             style="backface-visibility: hidden; background: linear-gradient(145deg, var(--bg-primary) 0%, var(--bg-hover) 100%);">
                            <div class="flex justify-between items-center text-[9px] uppercase tracking-wider font-bold text-on-surface-variant/60 mb-3">
                                <span>Question</span>
                                ${card.type || card.difficulty ? `
                                <div class="flex gap-1.5">
                                    ${card.type ? `<span class="px-2 py-0.5 rounded-full bg-primary/10 text-primary">${card.type}</span>` : ''}
                                    ${card.difficulty ? `<span class="px-2 py-0.5 rounded-full bg-[#fde68a] text-yellow-800">${card.difficulty}</span>` : ''}
                                </div>` : ''}
                            </div>
                            <div class="flex flex-1 items-center justify-center text-center font-headline text-[1.1rem] leading-snug text-on-surface overflow-y-auto px-2 custom-scrollbar">
                                ${this.escapeHtml(card.front)}
                            </div>
                        </div>

                        <!-- Back Face -->
                        <div class="absolute inset-0 w-full h-full flex flex-col p-5 rounded-2xl shadow-md text-white backface-hidden" 
                             style="backface-visibility: hidden; transform: rotateY(180deg); background: linear-gradient(135deg, var(--color-primary) 0%, var(--color-accent) 100%);">
                            <div class="text-[9px] uppercase tracking-wider font-bold text-white/60 mb-3 text-center">Answer</div>
                            <div class="flex flex-1 items-center justify-center text-center font-headline text-[1.05rem] leading-snug text-white overflow-y-auto px-2 custom-scrollbar">
                                ${this.escapeHtml(card.back)}
                            </div>
                            ${card.sources ? `<div class="mt-3 text-[9px] text-white/50 text-center font-mono">Sources: ${card.sources}</div>` : ''}
                        </div>
                    </div>
                </div>

                <!-- Controls -->
                <div class="flex justify-center gap-2 mt-2">
                    <button class="px-4 py-1.5 text-xs font-medium border border-outline-variant/40 rounded-lg hover:bg-surface-variant transition-colors disabled:opacity-30 disabled:cursor-not-allowed text-on-surface" 
                            onclick="FlashcardsUI.prevCard(); event.stopPropagation();" 
                            ${this.currentIndex === 0 ? 'disabled' : ''}>
                        ◀ Prev
                    </button>
                    <button class="px-6 py-1.5 text-xs font-semibold bg-primary text-white rounded-lg hover:bg-primary-container transition-all shadow-sm" 
                            onclick="FlashcardsUI.flipCard(); event.stopPropagation();">
                        ↻ Flip
                    </button>
                    <button class="px-4 py-1.5 text-xs font-medium border border-outline-variant/40 rounded-lg hover:bg-surface-variant transition-colors disabled:opacity-30 disabled:cursor-not-allowed text-on-surface" 
                            onclick="FlashcardsUI.nextCard(); event.stopPropagation();" 
                            ${this.currentIndex >= totalCards - 1 ? 'disabled' : ''}>
                        Next ▶
                    </button>
                </div>

                <!-- Keyboard Hint -->
                <div class="flex justify-center gap-4 text-[9px] text-on-surface-variant/40 uppercase tracking-widest mt-1">
                    <span>← → Navigate</span>
                    <span>Space to flip</span>
                </div>
            </div>
        `;
    },

    nextCard() {
        if (this.currentIndex < this.cards.length - 1) {
            this.currentIndex++;
            this.isFlipped = false;
            this.render();
        }
    },

    prevCard() {
        if (this.currentIndex > 0) {
            this.currentIndex--;
            this.isFlipped = false;
            this.render();
        }
    },

    flipCard() {
        this.isFlipped = !this.isFlipped;
        const innerEl = this.container.querySelector('.flashcard-inner');
        if (innerEl) {
            innerEl.style.transform = this.isFlipped ? 'rotateY(180deg)' : '';
        }
    },

    handleKeydown(e) {
        // Only handle if flashcards section is visible and we have cards
        if (this.cards.length === 0) return;

        // Check if focus is on an input element
        if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA') return;

        switch (e.key) {
            case 'ArrowLeft':
                e.preventDefault();
                this.prevCard();
                break;
            case 'ArrowRight':
                e.preventDefault();
                this.nextCard();
                break;
            case ' ':
            case 'Enter':
                // Only flip if flashcard container is in view
                if (this.container && this.container.offsetParent !== null) {
                    e.preventDefault();
                    this.flipCard();
                }
                break;
        }
    },

    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    },

    // Called externally to load cards
    loadCards(cards) {
        this.cards = cards || [];
        this.currentIndex = 0;
        this.isFlipped = false;
        this.render();
    },

    createSingleCard(front, source) {
        this.cards.push({
            front: front,
            back: "Derived from evidence chunk.",
            sources: [source],
            type: "concept",
            difficulty: "medium"
        });

        // Show user the new card
        this.currentIndex = this.cards.length - 1;
        this.isFlipped = false;
        if (this.container && this.container.offsetParent !== null) {
            this.render();
        }
    }
};

window.FlashcardsUI = FlashcardsUI;
