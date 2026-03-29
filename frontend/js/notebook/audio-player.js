/**
 * AudioPlayerUI - Custom audio player with controls and optional transcript
 */
const AudioPlayerUI = {
    audio: null,
    transcript: [],
    currentSentenceIndex: -1,
    isPlaying: false,
    container: null,

    init(containerSelector = '#audio-player-container') {
        this.container = document.querySelector(containerSelector);
    },

    /**
     * Load audio and optionally transcript, then render the player
     * @param {Blob|string} audioSource - Audio blob or URL
     * @param {Array} transcriptData - Optional array of {text, startTime, endTime}
     */
    async load(audioSource, transcriptData = []) {
        // Create audio URL if blob
        const audioUrl = audioSource instanceof Blob
            ? URL.createObjectURL(audioSource)
            : audioSource;

        this.audio = new Audio(audioUrl);
        this.transcript = transcriptData;
        this.currentSentenceIndex = -1;
        this.isPlaying = false;

        // Wait for metadata
        await new Promise((resolve) => {
            this.audio.addEventListener('loadedmetadata', resolve, { once: true });
            this.audio.load();
        });

        // Approximate timings for transcript sentences
        if (this.transcript.length > 0 && this.audio.duration && this.audio.duration !== Infinity && !isNaN(this.audio.duration)) {
            const totalDuration = this.audio.duration;
            const totalChars = this.transcript.reduce((acc, s) => acc + s.text.length, 0);
            let currentTime = 0;

            this.transcript = this.transcript.map(s => {
                const proportion = s.text.length / totalChars;
                const duration = proportion * totalDuration;
                const chunk = {
                    text: s.text,
                    startTime: currentTime,
                    endTime: currentTime + duration
                };
                currentTime += duration;
                return chunk;
            });
        }

        // Bind audio events
        this.audio.addEventListener('timeupdate', () => this.onTimeUpdate());
        this.audio.addEventListener('ended', () => this.onEnded());
        this.audio.addEventListener('play', () => this.onPlay());
        this.audio.addEventListener('pause', () => this.onPause());

        this.render();
        this.show();
    },

    render() {
        if (!this.container) return;

        const duration = this.audio.duration || 0;
        const hasTranscript = this.transcript.length > 0;

        this.container.innerHTML = `
            <div class="audio-player">
                <div class="audio-header">
                    <span class="audio-title">🎧 Audio Overview</span>
                    <button class="audio-close-btn" onclick="AudioPlayerUI.hide()">×</button>
                </div>

                <!-- Seek Bar -->
                <div class="audio-seek-container">
                    <input type="range" class="audio-seek" min="0" max="${Math.floor(duration)}" value="0" 
                        oninput="AudioPlayerUI.seek(this.value)">
                    <div class="audio-time">
                        <span class="audio-current-time">0:00</span>
                        <span class="audio-duration">${this.formatTime(duration)}</span>
                    </div>
                </div>

                <!-- Controls -->
                <div class="audio-controls">
                    <button class="audio-btn audio-play-btn" onclick="AudioPlayerUI.togglePlay()">
                        <span class="play-icon">▶</span>
                    </button>
                    
                    <div class="audio-speed-container">
                        <select class="audio-speed" onchange="AudioPlayerUI.setSpeed(this.value)">
                            <option value="0.5">0.5×</option>
                            <option value="0.75">0.75×</option>
                            <option value="1" selected>1×</option>
                            <option value="1.25">1.25×</option>
                            <option value="1.5">1.5×</option>
                            <option value="2">2×</option>
                        </select>
                    </div>
                </div>

                <!-- Transcript Panel -->
                ${hasTranscript ? `
                    <div class="transcript-panel">
                        <div class="transcript-header">Transcript</div>
                        <div class="transcript-content">
                            ${this.transcript.map((s, i) => `
                                <span class="transcript-sentence" data-index="${i}" 
                                    onclick="AudioPlayerUI.seekToSentence(${i})">
                                    ${this.escapeHtml(s.text)}
                                </span>
                            `).join(' ')}
                        </div>
                    </div>
                ` : ''}
            </div>
        `;
    },

    togglePlay() {
        if (this.isPlaying) {
            this.pause();
        } else {
            this.play();
        }
    },

    play() {
        if (this.audio) {
            this.audio.play();
        }
    },

    pause() {
        if (this.audio) {
            this.audio.pause();
        }
    },

    seek(time) {
        if (this.audio) {
            this.audio.currentTime = parseFloat(time);
        }
    },

    seekToSentence(index) {
        if (this.transcript[index] && this.audio) {
            this.audio.currentTime = this.transcript[index].startTime || 0;
            if (!this.isPlaying) this.play();
        }
    },

    setSpeed(rate) {
        if (this.audio) {
            this.audio.playbackRate = parseFloat(rate);
        }
    },

    onTimeUpdate() {
        const current = this.audio.currentTime;

        // Update seek bar
        const seekBar = this.container?.querySelector('.audio-seek');
        if (seekBar) seekBar.value = current;

        // Update time display
        const timeDisplay = this.container?.querySelector('.audio-current-time');
        if (timeDisplay) timeDisplay.textContent = this.formatTime(current);

        // Highlight current transcript sentence
        this.highlightCurrentSentence(current);
    },

    highlightCurrentSentence(time) {
        if (this.transcript.length === 0) return;

        // Find current sentence
        let newIndex = -1;
        for (let i = 0; i < this.transcript.length; i++) {
            const s = this.transcript[i];
            if (time >= (s.startTime || 0) && time < (s.endTime || Infinity)) {
                newIndex = i;
                break;
            }
        }

        if (newIndex !== this.currentSentenceIndex) {
            // Remove old highlight
            const oldEl = this.container?.querySelector('.transcript-sentence.active');
            if (oldEl) oldEl.classList.remove('active');

            // Add new highlight
            if (newIndex >= 0) {
                const newEl = this.container?.querySelector(`.transcript-sentence[data-index="${newIndex}"]`);
                if (newEl) {
                    newEl.classList.add('active');
                    // Scroll into view
                    newEl.scrollIntoView({ behavior: 'smooth', block: 'center' });
                }
            }

            this.currentSentenceIndex = newIndex;
        }
    },

    onPlay() {
        this.isPlaying = true;
        const btn = this.container?.querySelector('.audio-play-btn .play-icon');
        if (btn) btn.textContent = '⏸';
    },

    onPause() {
        this.isPlaying = false;
        const btn = this.container?.querySelector('.audio-play-btn .play-icon');
        if (btn) btn.textContent = '▶';
    },

    onEnded() {
        this.isPlaying = false;
        const btn = this.container?.querySelector('.audio-play-btn .play-icon');
        if (btn) btn.textContent = '▶';

        // Reset to beginning
        const seekBar = this.container?.querySelector('.audio-seek');
        if (seekBar) seekBar.value = 0;
    },

    show() {
        if (this.container) {
            this.container.classList.remove('hidden');
        }
    },

    hide() {
        if (this.audio) {
            this.audio.pause();
            this.audio = null;
        }
        if (this.container) {
            this.container.classList.add('hidden');
            this.container.innerHTML = '';
        }
    },

    formatTime(seconds) {
        if (!seconds || isNaN(seconds)) return '0:00';
        const mins = Math.floor(seconds / 60);
        const secs = Math.floor(seconds % 60);
        return `${mins}:${secs.toString().padStart(2, '0')}`;
    },

    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
};

window.AudioPlayerUI = AudioPlayerUI;
