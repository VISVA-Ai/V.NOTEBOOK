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
                <div class="flashcard-empty">
                    <div class="flashcard-empty-icon">🗂️</div>
                    <div class="text-sm font-medium text-secondary">No Flashcards</div>
                    <div class="text-xs text-tertiary mt-1">Use 'Grounded Mode' to unlock.</div>
                    <button class="btn btn-secondary text-xs mt-3" onclick="FlashcardsUI.generate()">+ Generate</button>
                </div>
            `;
            return;
        }

        const card = this.cards[this.currentIndex];
        const totalCards = this.cards.length;
        const currentNum = this.currentIndex + 1;

        this.container.innerHTML = `
            <div class="flashcard-wrapper">
                <!-- Progress Indicator -->
                <div class="flashcard-progress">
                    <span class="flashcard-progress-text">${currentNum} / ${totalCards}</span>
                    <div class="flashcard-progress-bar">
                        <div class="flashcard-progress-fill" style="width: ${(currentNum / totalCards) * 100}%"></div>
                    </div>
                </div>

                <!-- Card -->
                <div class="flashcard ${this.isFlipped ? 'flipped' : ''}" onclick="FlashcardsUI.flipCard()" tabindex="0">
                    <div class="flashcard-inner">
                        <div class="flashcard-face flashcard-front">
                            <div class="flashcard-label flex-row" style="justify-content: space-between;">
                                <span>Question</span>
                                ${card.type || card.difficulty ? `
                                <div class="flashcard-badges">
                                    ${card.type ? `<span class="badge type-badge">${card.type}</span>` : ''}
                                    ${card.difficulty ? `<span class="badge diff-badge">${card.difficulty}</span>` : ''}
                                </div>` : ''}
                            </div>
                            <div class="flashcard-content">${this.escapeHtml(card.front)}</div>
                        </div>
                        <div class="flashcard-face flashcard-back">
                            <div class="flashcard-label">Answer</div>
                            <div class="flashcard-content">${this.escapeHtml(card.back)}</div>
                            ${card.sources ? `<div class="flashcard-sources">Sources: ${card.sources}</div>` : ''}
                        </div>
                    </div>
                </div>

                <!-- Controls -->
                <div class="flashcard-controls">
                    <button class="flashcard-nav-btn" onclick="FlashcardsUI.prevCard()" ${this.currentIndex === 0 ? 'disabled' : ''}>
                        ◀ Prev
                    </button>
                    <button class="flashcard-flip-btn" onclick="FlashcardsUI.flipCard()">
                        ↻ Flip
                    </button>
                    <button class="flashcard-nav-btn" onclick="FlashcardsUI.nextCard()" ${this.currentIndex >= totalCards - 1 ? 'disabled' : ''}>
                        Next ▶
                    </button>
                </div>

                <!-- Keyboard Hint -->
                <div class="flashcard-hint">
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
        const cardEl = this.container.querySelector('.flashcard');
        if (cardEl) {
            cardEl.classList.toggle('flipped', this.isFlipped);
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
