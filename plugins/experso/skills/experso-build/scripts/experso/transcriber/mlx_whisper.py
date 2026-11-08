from pathlib import Path

import mlx_whisper

from .base import Transcriber, Transcript


class MlxWhisperTranscriber(Transcriber):
    """OpenAI Whisper on Apple Silicon GPU via MLX. Multilingual."""

    name = "mlx-whisper"
    default_model = "mlx-community/whisper-large-v3-turbo"

    def transcribe(self, media: Path) -> Transcript:
        r = mlx_whisper.transcribe(
            str(media),
            path_or_hf_repo=self.model or self.default_model,
            language=self.language,
            # Avoids Whisper repeating itself across segments on short clips.
            condition_on_previous_text=False,
        )
        return Transcript(text=r["text"].strip(), language=r.get("language"))
