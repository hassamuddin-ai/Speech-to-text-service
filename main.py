import argparse
import signal
import sys
import time

from rich.console import Console
from rich.panel import Panel

from config.loader import load_config
from src.transcription.pipeline import TranscriptionPipeline

console = Console()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Real-time multilingual STT"
    )
    parser.add_argument(
        "--language",
        type=str,
        default=None,
        help="Force language code (e.g. en, ur, ar). Default: auto-detect."
    )
    parser.add_argument(
        "--no-save",
        action="store_true",
        help="Disable transcript file saving."
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    console.print(
        Panel.fit(
            "[bold cyan]🎙  Real-time Multilingual STT[/bold cyan]\n"
            "[dim]Powered by OpenAI Whisper + WebRTC VAD[/dim]",
            border_style="cyan"
        )
    )

    try:
        config = load_config()
    except (FileNotFoundError, EnvironmentError, ValueError) as e:
        console.print(f"[bold red]Config error:[/bold red] {e}")
        sys.exit(1)

    # CLI overrides
    if args.language:
        config["whisper"]["language"] = args.language
        console.print(
            f"[yellow]Language forced:[/yellow] {args.language}"
        )

    if args.no_save:
        config["output"]["format"] = "none"
        console.print("[yellow]File saving disabled.[/yellow]")

    pipeline = TranscriptionPipeline(config)

    # Graceful shutdown on Ctrl+C or SIGTERM
    def _shutdown(sig, frame):
        console.print(
            "\n[yellow]Interrupt received, shutting down…[/yellow]"
        )
        pipeline.stop()
        sys.exit(0)

    signal.signal(signal.SIGINT, _shutdown)

    # SIGTERM is not available on some Windows environments
    if hasattr(signal, "SIGTERM"):
        signal.signal(signal.SIGTERM, _shutdown)

    pipeline.start()

    # Keep the main thread alive (Windows-compatible)
    while True:
        time.sleep(1)


if __name__ == "__main__":
    main()