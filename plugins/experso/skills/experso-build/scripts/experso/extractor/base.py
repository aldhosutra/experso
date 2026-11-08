from abc import ABC, abstractmethod


class Extractor(ABC):
    """Turns one Post into a dict following extractor.schema.RESULT_SCHEMA
    (post_summary, image_text, insights, not_extracted). Must be safe to call
    from several threads at once."""

    name: str

    def __init__(self, model: str | None = None, **options):
        self.model = model
        self.options = options

    @property
    def label(self) -> str:
        return f"{self.name}/{self.model or getattr(self, 'default_model', 'default')}"

    @abstractmethod
    def extract(self, post, creator: str) -> dict: ...
