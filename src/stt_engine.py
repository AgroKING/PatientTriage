class STTEngine:
    def is_available(self) -> bool:
        return False

    def transcribe(self, audio_bytes: bytes) -> str:
        raise NotImplementedError(
            "Speech-to-text not implemented. Install faster-whisper and update this module."
        )
