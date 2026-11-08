from pathlib import Path

from faster_whisper import WhisperModel

from .base import Transcriber, Transcript


class FasterWhisperTranscriber(Transcriber):
    """Whisper via CTranslate2. Uses CUDA when available, otherwise CPU int8."""

    name = "faster-whisper"
    default_model = "large-v3-turbo"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        try:
            import ctranslate2
            cuda = ctranslate2.get_cuda_device_count() > 0
        except Exception:
            cuda = False
        device, compute = ("cuda", "float16") if cuda else ("cpu", "int8")
        self._model = WhisperModel(self.model or self.default_model,
                                   device=device, compute_type=compute)

    def transcribe(self, media: Path) -> Transcript:
        segments, info = self._model.transcribe(
            str(media), language=self.language, condition_on_previous_text=False)
        text = " ".join(s.text.strip() for s in segments)  # segments is lazy
        return Transcript(text=text.strip(), language=info.language)
