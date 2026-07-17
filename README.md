<<<<<<< HEAD
# 🎙️ Realtime STT — Production Grade

Real-time multilingual Speech-to-Text pipeline using the Groq Whisper API with VAD-based chunking, a Streamlit web UI, Roman Urdu transliteration, and automatic math/code symbol normalization.

---

## Features

- **Streamlit Web UI** — white & blue professional interface with live transcript display, stats dashboard, and one-click download
- **Voice Activity Detection** — WebRTC VAD with configurable aggressiveness and silence thresholds
- **Smart audio chunking** — silence-boundary segmentation, skips clips under 0.3s
- **Multilingual support** — auto-detects language; English and Urdu allowed by default, others filtered
- **Roman Urdu transliteration** — pure Urdu utterances stay in Urdu script; mixed Urdu/English is converted to Roman Urdu automatically
- **Math & code normalization** — spoken expressions like *"x equals two plus one"* are converted to `x = 2 + 1` before display
- **Async non-blocking pipeline** — background thread pushes utterances via a thread-safe queue; UI drains on each rerun
- **Structured transcript logging** — JSON + plain text output with timestamps, language tags, and durations
- **Configurable** — via `.env` and `config/settings.yaml`
- **Graceful shutdown & error recovery**

---

## Project Structure

```
realtime-stt/
├── app.py                      # Streamlit UI entry point
├── main.py                     # CLI entry point
├── requirements.txt
├── .env.example
├── config/
│   ├── loader.py
│   └── settings.yaml           # Sample rate, VAD, output format, language
├── src/
│   ├── audio/
│   │   ├── capture.py          # Mic capture & buffering
│   │   └── utils.py            # WAV buffer helpers, duration calc
│   ├── vad/
│   │   └── detector.py         # WebRTC VAD integration
│   ├── transcription/
│   │   ├── pipeline.py         # Main transcription pipeline
│   │   ├── whisper_client.py   # Groq Whisper API client
│   │   └── language_filter.py  # is_urdu(), is_allowed() helpers
│   └── utils/
│       ├── text_normalizer.py  # Spoken math/code → symbolic notation
│       ├── roman_urdu.py       # Urdu script → Roman Urdu transliterator
│       ├── file_handler.py     # JSON + TXT transcript writer
│       └── logger.py
├── output/
│   └── transcripts/            # Saved session transcripts
├── logs/
└── tests/
```

---

## Quick Start

```bash
pip install -r requirements.txt
cp .env.example .env            # Add your Groq API key
```

**Streamlit UI (recommended):**
```bash
streamlit run app.py
```

**CLI (headless):**
```bash
python main.py
```

> **WSL2 users:** if the mic fails to open, run `pulseaudio --start` first.

---

## Configuration

Edit `config/settings.yaml` to tune:

| Key | Description |
|-----|-------------|
| `audio.sample_rate` | Mic sample rate (default: 16000) |
| `vad.aggressiveness` | WebRTC VAD level 0–3 (higher = less sensitive to noise) |
| `vad.silence_threshold` | Frames of silence before flushing audio to Whisper |
| `whisper.language` | Target language code (`null` for auto-detect) |
| `output.format` | `json`, `txt`, or `both` |

All VAD and output settings are also adjustable live from the sidebar in the Streamlit UI.

---

## Text Processing Pipeline

Each utterance goes through this chain after Whisper transcription:

```
Whisper output
    │
    ▼
TextNormalizer          spoken math/code → symbols
    │                   "x equals two plus one" → "x = 2 + 1"
    │                   only fires when math keywords detected (mode="auto")
    ▼
Language filter         drop non-English/Urdu utterances
    │
    ▼
Roman Urdu (Urdu only)  pure Urdu → kept in Urdu script
                        mixed Urdu+English → Roman Urdu
                        "مجھے glossary چاہیے" → "mujhe glossary chahiye"
    │
    ▼
Display + save
```

### Math & Symbol Normalization (`text_normalizer.py`)

Converts spoken forms to symbolic notation. Triggers only when math/code keywords are present so normal speech is passed through untouched.

| Spoken | Normalized |
|--------|------------|
| `x equals two plus one` | `x = 2 + 1` |
| `if x is greater than or equal to ten` | `if x >= 10` |
| `y equals x squared minus three` | `y = x ^ 2 - 3` |
| `def my underscore function open paren a comma b close paren colon` | `def my_function(a, b):` |

### Roman Urdu Transliteration (`roman_urdu.py`)

- Pure Urdu utterances (no English words) → **kept in Urdu script**
- Mixed Urdu + English → **fully converted to Roman Urdu**
- 300+ word-level overrides for natural romanization
- English loanwords in Urdu script (e.g. `اپلیکیشن`) are mapped to their correct English spelling (`application`)
- Math terms, numbers, and curriculum vocabulary covered

---

## UI Overview

The Streamlit app (`app.py`) provides:

- **Live transcript panel** — utterances with timestamp, language badge, and normalized text
- **Stats bar** — utterance count, word count, session duration, languages detected
- **Sidebar controls** — language selection, VAD aggressiveness, silence threshold, output format
- **Download buttons** — export full session as JSON or plain text

---

## Requirements

- Python 3.9+
- Groq API key (set `GROQ_API_KEY` in `.env`)
- Working microphone
- `portaudio` system library (`brew install portaudio` / `apt install portaudio19-dev`)
=======
# Speech-to-text-service
>>>>>>> 62c449d7cbe056fcb046aca295ed41cd3f8f4bef
