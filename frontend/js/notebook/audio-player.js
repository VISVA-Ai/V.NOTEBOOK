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
            <div class="flex flex-col gap-4 p-5 bg-surface rounded-2xl border border-outline-variant/30 shadow-sm relative overflow-hidden">
                <div class="flex justify-between items-center mb-1">
                    <span class="text-[13px] font-semibold text-on-surface select-none flex items-center gap-2">
                         <span class="material-symbols-outlined text-[18px] text-primary" style="font-variation-settings: 'FILL' 1;">audio_file</span>
                         Audio Overview
                    </span>
                    <button class="w-6 h-6 flex items-center justify-center text-on-surface-variant/70 hover:text-on-surface hover:bg-surface-variant rounded-md transition-colors" onclick="AudioPlayerUI.hide()">✕</button>
                </div>

                <!-- Seek Bar -->
                <div class="flex flex-col gap-1.5 w-full">
                    <input type="range" class="audio-seek w-full h-1.5 bg-outline-variant/30 rounded-full appearance-none cursor-pointer accent-primary outline-none" 
                        min="0" max="${Math.floor(duration)}" value="0" 
                        oninput="AudioPlayerUI.seek(this.value)">
                    <div class="flex justify-between text-[10px] font-mono font-bold text-on-surface-variant/50">
                        <span class="audio-current-time">0:00</span>
                        <span class="audio-duration">${this.formatTime(duration)}</span>
                    </div>
                </div>

                <!-- Controls -->
                <div class="flex items-center justify-center gap-6 my-2">
                    <button class="audio-play-btn w-11 h-11 flex items-center justify-center rounded-full bg-primary text-white hover:bg-primary-container transition-all shadow-md transform hover:scale-105" onclick="AudioPlayerUI.togglePlay()">
                        <span class="play-icon text-xl leading-none ml-1">▶</span>
                    </button>
                    
                    <div class="absolute right-5 bottom-5">
                        <select class="px-2 py-1 text-[10px] font-medium border border-outline-variant/40 rounded-md bg-transparent text-on-surface-variant cursor-pointer outline-none focus:ring-1 focus:ring-primary/50" onchange="AudioPlayerUI.setSpeed(this.value)">
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
                    <div class="mt-2 pt-3 border-t border-outline-variant/20 max-h-[150px] overflow-y-auto custom-scrollbar">
                        <div class="text-[9px] font-bold uppercase tracking-widest text-on-surface-variant/50 mb-2">Transcript</div>
                        <div class="text-[13px] leading-relaxed text-on-surface-variant/90">
                            ${this.transcript.map((s, i) => `
                                <span class="transcript-sentence cursor-pointer px-1 py-0.5 -mx-1 rounded-[4px] transition-colors hover:bg-surface-variant" data-index="${i}" 
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
            if (oldEl) {
                oldEl.classList.remove('active', 'bg-primary/10', 'text-primary');
            }

            // Add new highlight
            if (newIndex >= 0) {
                const newEl = this.container?.querySelector(`.transcript-sentence[data-index="${newIndex}"]`);
                if (newEl) {
                    newEl.classList.add('active', 'bg-primary/10', 'text-primary');
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
