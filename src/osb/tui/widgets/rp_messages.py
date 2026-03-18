"""Custom messages for RightPane."""

from textual.message import Message


class OllamaChunk(Message):
    """Chunk of text from Ollama streaming response."""

    def __init__(self, text: str, chapter_ref: str) -> None:
        super().__init__()
        self.text = text
        self.chapter_ref = chapter_ref


class OllamaError(Message):
    """Error from Ollama."""

    def __init__(self, error: str) -> None:
        super().__init__()
        self.error = error


class StreamingDone(Message):
    """Ollama streaming response complete."""

    def __init__(self, chapter_ref: str, response: str) -> None:
        super().__init__()
        self.chapter_ref = chapter_ref
        self.response = response
