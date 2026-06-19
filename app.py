"""
app.py — Streamlit UI for Real-time STT Pipeline
Run with: streamlit run app.py
"""
import io
import json
import queue
import threading
import time
import wave
from datetime import datetime
from pathlib import Path

import numpy as np
import streamlit as st

# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Real-time STT",
    page_icon="🎙",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Custom CSS ─────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;600&family=Syne:wght@400;700;800&display=swap');

* { font-family: 'Syne', sans-serif; }
code, pre, .mono { font-family: 'JetBrains Mono', monospace; }

/* Dark terminal aesthetic */
.stApp {
    background: #0a0a0f;
    color: #e8e8f0;
}

/* Sidebar */
[data-testid="stSidebar"] {
    background: #0f0f1a;
    border-right: 1px solid #1e1e3a;
}

/* Header */
.stt-header {
    display: flex;
    align-items: center;
    gap: 16px;
    padding: 24px 0 8px;
    border-bottom: 1px solid #1e1e3a;
    margin-bottom: 24px;
}
.stt-title {
    font-size: 2rem;
    font-weight: 800;
    color: #00ff9d;
    letter-spacing: -1px;
    margin: 0;
}
.stt-subtitle {
    font-size: 0.85rem;
    color: #4a4a6a;
    font-family: 'JetBrains Mono', monospace;
    margin: 0;
}

/* Status badge */
.status-badge {
    display: inline-flex;
    align-items: center;
    gap: 8px;
    padding: 6px 14px;
    border-radius: 20px;
    font-size: 0.8rem;
    font-family: 'JetBrains Mono', monospace;
    font-weight: 600;
    letter-spacing: 0.5px;
}
.status-listening {
    background: rgba(0, 255, 157, 0.1);
    border: 1px solid #00ff9d;
    color: #00ff9d;
}
.status-idle {
    background: rgba(74, 74, 106, 0.2);
    border: 1px solid #2a2a4a;
    color: #4a4a6a;
}
.status-dot {
    width: 8px; height: 8px;
    border-radius: 50%;
    animation: pulse 1.2s infinite;
}
.status-listening .status-dot { background: #00ff9d; }
.status-idle .status-dot { background: #4a4a6a; animation: none; }

@keyframes pulse {
    0%, 100% { opacity: 1; transform: scale(1); }
    50% { opacity: 0.4; transform: scale(0.8); }
}

/* Transcript box */
.transcript-container {
    background: #0f0f1a;
    border: 1px solid #1e1e3a;
    border-radius: 12px;
    padding: 20px;
    min-height: 320px;
    max-height: 480px;
    overflow-y: auto;
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.9rem;
    line-height: 1.8;
}

/* Utterance rows */
.utterance {
    display: flex;
    gap: 12px;
    padding: 8px 0;
    border-bottom: 1px solid #13131f;
    animation: fadeIn 0.3s ease;
}
.utterance:last-child { border-bottom: none; }
.utt-time {
    color: #2a2a5a;
    font-size: 0.75rem;
    min-width: 80px;
    padding-top: 2px;
}
.utt-lang {
    color: #00ff9d;
    font-size: 0.7rem;
    min-width: 28px;
    padding-top: 3px;
    text-transform: uppercase;
}
.utt-text { color: #c8c8e0; flex: 1; }

@keyframes fadeIn {
    from { opacity: 0; transform: translateY(4px); }
    to { opacity: 1; transform: translateY(0); }
}

/* Empty state */
.empty-state {
    text-align: center;
    padding: 60px 20px;
    color: #2a2a4a;
    font-family: 'JetBrains Mono', monospace;
}
.empty-icon { font-size: 3rem; margin-bottom: 12px; }

/* Stats cards */
.stat-card {
    background: #0f0f1a;
    border: 1px solid #1e1e3a;
    border-radius: 10px;
    padding: 16px;
    text-align: center;
}
.stat-value {
    font-size: 1.8rem;
    font-weight: 800;
    color: #00ff9d;
    font-family: 'JetBrains Mono', monospace;
}
.stat-label {
    font-size: 0.75rem;
    color: #4a4a6a;
    text-transform: uppercase;
    letter-spacing: 1px;
    margin-top: 4px;
}

/* Buttons */
.stButton > button {
    background: #00ff9d !important;
    color: #0a0a0f !important;
    border: none !important;
    border-radius: 8px !important;
    font-weight: 700 !important;
    font-family: 'Syne', sans-serif !important;
    letter-spacing: 0.5px !important;
    padding: 10px 24px !important;
    transition: all 0.2s !important;
}
.stButton > button:hover {
    background: #00cc7a !important;
    transform: translateY(-1px) !important;
}
.stop-btn > button {
    background: #ff4466 !important;
    color: white !important;
}
.stop-btn > button:hover { background: #cc3355 !important; }

/* Scrollbar */
::-webkit-scrollbar { width: 4px; }
::-webkit-scrollbar-track { background: #0a0a0f; }
::-webkit-scrollbar-thumb { background: #1e1e3a; border-radius: 2px; }
</style>
""", unsafe_allow_html=True)


# ── Session state init ─────────────────────────────────────────────────────────
# Thread-safe queue: background audio thread puts utterances here,
# main Streamlit thread drains it on each rerun.
if "utterance_queue" not in st.session_state:
    st.session_state.utterance_queue = queue.Queue()

def init_state():
    defaults = {
        "running": False,
        "utterances": [],
        "pipeline": None,
        "thread": None,
        "session_start": None,
        "word_count": 0,
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

init_state()

# Drain any utterances the background thread pushed since last rerun
_uq = st.session_state.utterance_queue
while not _uq.empty():
    try:
        st.session_state.utterances.append(_uq.get_nowait())
    except queue.Empty:
        break


# ── Sidebar — Settings ─────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("### ⚙️ Settings")
    st.divider()

    language = st.selectbox(
        "Language",
        ["Auto-detect", "Urdu (ur)", "Arabic (ar)", "English (en)",
         "Hindi (hi)", "French (fr)", "Spanish (es)", "German (de)"],
        index=0,
    )
    lang_code = None if language == "Auto-detect" else language.split("(")[1].rstrip(")")

    st.divider()
    st.markdown("### 🎚️ VAD Settings")
    aggressiveness = st.slider("Aggressiveness", 0, 3, 2,
        help="Higher = less sensitive to background noise")
    silence_threshold = st.slider("Silence threshold (frames)", 10, 50, 25,
        help="Frames of silence before sending audio to Whisper")

    st.divider()
    st.markdown("### 💾 Output")
    save_format = st.radio("Save format", ["Both (JSON + TXT)", "JSON only", "TXT only", "Don't save"],
                           index=0)
    fmt_map = {
        "Both (JSON + TXT)": "both",
        "JSON only": "json",
        "TXT only": "txt",
        "Don't save": "none"
    }

    st.divider()
    st.markdown("### 📁 Transcripts")
    transcript_dir = Path("output/transcripts")
    if transcript_dir.exists():
        files = sorted(transcript_dir.glob("*.json"), reverse=True)[:5]
        if files:
            for f in files:
                st.markdown(f"📄 `{f.name}`")
        else:
            st.caption("No transcripts yet")
    else:
        st.caption("No transcripts yet")


# ── Header ─────────────────────────────────────────────────────────────────────
st.markdown("""
<div class="stt-header">
    <div>
        <p class="stt-title">🎙 Real-time STT</p>
        <p class="stt-subtitle">groq / whisper-large-v3-turbo · webrtc vad · multilingual</p>
    </div>
</div>
""", unsafe_allow_html=True)

# ── Status + Controls ──────────────────────────────────────────────────────────
col_status, col_btn1, col_btn2, col_btn3 = st.columns([3, 1, 1, 1])

with col_status:
    if st.session_state.running:
        st.markdown("""
        <div class="status-badge status-listening">
            <div class="status-dot"></div> LISTENING
        </div>""", unsafe_allow_html=True)
    else:
        st.markdown("""
        <div class="status-badge status-idle">
            <div class="status-dot"></div> IDLE
        </div>""", unsafe_allow_html=True)

with col_btn1:
    start_clicked = st.button("▶ Start", disabled=st.session_state.running, use_container_width=True)

with col_btn2:
    st.markdown('<div class="stop-btn">', unsafe_allow_html=True)
    stop_clicked = st.button("■ Stop", disabled=not st.session_state.running, use_container_width=True)
    st.markdown('</div>', unsafe_allow_html=True)

with col_btn3:
    clear_clicked = st.button("⌫ Clear", use_container_width=True)

st.markdown("<br>", unsafe_allow_html=True)

# ── Stats row ──────────────────────────────────────────────────────────────────
c1, c2, c3, c4 = st.columns(4)
utterance_count = len(st.session_state.utterances)
word_count = sum(len(u["text"].split()) for u in st.session_state.utterances)
duration = ""
if st.session_state.session_start:
    elapsed = int(time.time() - st.session_state.session_start)
    duration = f"{elapsed // 60:02d}:{elapsed % 60:02d}"
else:
    duration = "00:00"

langs_seen = list({u.get("language", "?") or "?" for u in st.session_state.utterances})
lang_display = ", ".join(langs_seen) if langs_seen else "—"

with c1:
    st.markdown(f'<div class="stat-card"><div class="stat-value">{utterance_count}</div><div class="stat-label">Utterances</div></div>', unsafe_allow_html=True)
with c2:
    st.markdown(f'<div class="stat-card"><div class="stat-value">{word_count}</div><div class="stat-label">Words</div></div>', unsafe_allow_html=True)
with c3:
    st.markdown(f'<div class="stat-card"><div class="stat-value">{duration}</div><div class="stat-label">Duration</div></div>', unsafe_allow_html=True)
with c4:
    st.markdown(f'<div class="stat-card"><div class="stat-value" style="font-size:1rem;padding-top:6px">{lang_display}</div><div class="stat-label">Languages</div></div>', unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# ── Transcript display ─────────────────────────────────────────────────────────
st.markdown("#### Transcript")

if not st.session_state.utterances:
    st.markdown("""
    <div class="transcript-container">
        <div class="empty-state">
            <div class="empty-icon">🎙</div>
            <div>Press <strong>Start</strong> and begin speaking</div>
        </div>
    </div>
    """, unsafe_allow_html=True)
else:
    rows_html = ""
    for u in st.session_state.utterances:
        t = datetime.fromisoformat(u["timestamp"]).strftime("%H:%M:%S")
        lang = (u.get("language") or "?").upper()
        text = u["text"]
        rows_html += f"""
        <div class="utterance">
            <span class="utt-time">{t}</span>
            <span class="utt-lang">{lang}</span>
            <span class="utt-text">{text}</span>
        </div>"""
    st.markdown(f'<div class="transcript-container">{rows_html}</div>', unsafe_allow_html=True)

# ── Download ───────────────────────────────────────────────────────────────────
if st.session_state.utterances:
    st.markdown("<br>", unsafe_allow_html=True)
    dl1, dl2, _ = st.columns([1, 1, 4])
    with dl1:
        json_data = json.dumps({
            "session_start": st.session_state.get("session_start_iso", ""),
            "utterances": st.session_state.utterances
        }, ensure_ascii=False, indent=2)
        st.download_button("⬇ JSON", json_data, "transcript.json", "application/json", use_container_width=True)
    with dl2:
        txt_data = "\n".join(f"[{u['timestamp']}] {u['text']}" for u in st.session_state.utterances)
        st.download_button("⬇ TXT", txt_data, "transcript.txt", "text/plain", use_container_width=True)


# ── Button logic ───────────────────────────────────────────────────────────────
if clear_clicked:
    st.session_state.utterances = []
    st.session_state.session_start = None
    st.rerun()

if start_clicked:
    try:
        from config.loader import load_config
        from src.transcription.pipeline import TranscriptionPipeline

        config = load_config()
        config["whisper"]["language"] = lang_code
        config["vad"]["aggressiveness"] = aggressiveness
        config["vad"]["silence_threshold"] = silence_threshold
        config["output"]["format"] = fmt_map[save_format]

        # Patch pipeline to push utterances into thread-safe queue
        pipeline = TranscriptionPipeline(config)
        utt_queue = st.session_state.utterance_queue

        def patched_save(frames):
            from src.audio.utils import frames_to_wav_buffer, frames_duration_seconds
            duration_s = frames_duration_seconds(frames, config["audio"]["sample_rate"])
            if duration_s < 0.3:
                return
            try:
                wav_buf = frames_to_wav_buffer(frames, config["audio"]["sample_rate"])
                text, language = pipeline._whisper.transcribe(wav_buf)
                if not text:
                    return
                from src.utils.roman_urdu import to_roman_urdu
                from src.transcription.language_filter import is_urdu, is_allowed

                # Drop non-English/Urdu utterances
                if not is_allowed(language):
                    return

                display_text = to_roman_urdu(text.strip()) if is_urdu(language) else text.strip()

                utterance = {
                    "timestamp": datetime.utcnow().isoformat(),
                    "text": display_text,
                    "language": language,
                    "duration_s": round(duration_s, 3),
                }
                # Use thread-safe queue — never touch st.session_state from background thread
                utt_queue.put(utterance)
                pipeline._file_handler.write(display_text, language=language, duration_s=duration_s)
            except Exception as e:
                pipeline._logger.error(f"Transcription error: {e}")

        pipeline._transcribe_and_save = patched_save

        st.session_state.pipeline = pipeline
        st.session_state.running = True
        st.session_state.session_start = time.time()
        st.session_state.session_start_iso = datetime.utcnow().isoformat()

        try:
            pipeline.start()
        except Exception as e:
            st.session_state.running = False
            st.session_state.pipeline = None
            st.error(f"Mic error: {e}\n\nOn WSL2, run: pulseaudio --start")
            st.stop()

        st.rerun()

    except Exception as e:
        st.error(f"Failed to start: {e}")

if stop_clicked and st.session_state.pipeline:
    st.session_state.pipeline.stop()
    st.session_state.pipeline = None
    st.session_state.running = False
    st.rerun()

# ── Auto-refresh while running ─────────────────────────────────────────────────
if st.session_state.running:
    time.sleep(1.5)
    st.rerun()