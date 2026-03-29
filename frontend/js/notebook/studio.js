const StudioUI = {
    init() {
        // Map card labels/indices to actions
        // index.html has 4 cards in a grid.
        // We can select them by .studio-card
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
            // Fallback: check localStorage directly in case State sync is slow
            sessionId = localStorage.getItem('last_session_id');
            if (sessionId) {
                State.data.currentSessionId = sessionId; // Sync back
            }
        }

        if (!sessionId) {
            alert("No active session found. Please click 'New Chat' or select a history item.");
            return;
        }

        // Visual feedback
        NotebookUI.updateStatus(`Generating ${label}...`);

        try {
            switch (label) {
                case 'Flashcards':
                    await this.generateFlashcards(sessionId);
                    break;
                case 'Quiz':
                    await this.generateQuiz(sessionId);
                    break;
                case 'Audio Overview':
                    await this.generateAudio();
                    break;
                case 'Video Overview':
                    await this.generateVideo();
                    break;
                case 'Mind Map':
                    await this.generateMindMap(sessionId);
                    break;
                case 'Reports':
                    await this.generateReport(sessionId);
                    break;
                case 'Infographic':
                    await this.generateInfographic(sessionId);
                    break;
                case 'Slide deck':
                    await this.generateSlides(sessionId);
                    break;
                case 'Data table':
                    await this.generateDataTable(sessionId);
                    break;
                default:
                    console.warn("Unknown studio action:", label);
            }
        } catch (e) {
            console.error(e);
            alert(`Failed to generate ${label}: ${e.message}`);
        } finally {
            NotebookUI.updateStatus("Ready");
        }
    },

    async generateFlashcards(sessionId) {
        try {
            const result = await API.generateFlashcards(sessionId);
            NotebookUI.appendMessage('system', `Flashcards generated! Check the "Flashcards" tab or view below.`);

            if (window.FlashcardsUI) {
                FlashcardsUI.render(result.cards);
            }
        } catch (e) {
            throw e;
        }
    },

    async generateAudio() {
        try {
            NotebookUI.appendMessage('system', 'Generating audio overview... This may take a moment.');

            const data = await API.generateAudioOverview();

            if (!AudioPlayerUI.container) {
                AudioPlayerUI.init('#audio-player-container');
            }

            // Split transcript into sentences
            const rawSentences = (data.transcript || '').match(/[^.!?]+[.!?]+/g) || [(data.transcript || 'Audio generated.')];
            const transcriptData = rawSentences.map(text => ({ text: text.trim(), startTime: 0, endTime: 0 }));

            await AudioPlayerUI.load(data.audio, transcriptData);

            NotebookUI.appendMessage('system', '🎧 Audio overview ready! Use the player controls on the right.');
        } catch (e) {
            throw e;
        }
    },

    async generateVideo() {
        NotebookUI.appendMessage('system', '📹 Video Overview coming soon! This feature will generate a video summary of your research.');
    },

    async generateMindMap(sessionId) {
        NotebookUI.appendMessage('system', '🕸️ Mind Map generation coming soon! This feature will visualize connections between concepts.');
    },

    async generateReport(sessionId) {
        NotebookUI.appendMessage('system', '📊 Report generation coming soon! This feature will create a structured research report.');
    },

    async generateQuiz(sessionId) {
        NotebookUI.appendMessage('system', '📝 Quiz generation coming soon! This feature will create interactive quizzes from your sources.');
    },

    async generateInfographic(sessionId) {
        NotebookUI.appendMessage('system', '📈 Infographic generation coming soon! This feature will create visual data summaries.');
    },

    async generateSlides(sessionId) {
        NotebookUI.appendMessage('system', '🎨 Slide deck generation coming soon! This feature will create presentation slides.');
    },

    async generateDataTable(sessionId) {
        NotebookUI.appendMessage('system', '📋 Data table generation coming soon! This feature will extract and organize data from sources.');
    }
};

window.StudioUI = StudioUI;

document.addEventListener('DOMContentLoaded', () => {
    setTimeout(() => StudioUI.init(), 500);
});
