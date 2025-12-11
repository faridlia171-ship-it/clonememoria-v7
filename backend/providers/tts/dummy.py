import logging
import struct
import math
from typing import Optional

from backend.providers.tts.base import BaseTTSProvider

logger = logging.getLogger(__name__)
logger.info("DUMMY_TTS_PROVIDER_LOADED", extra={"file": __file__})


class DummyTTSProvider(BaseTTSProvider):
    """Dummy TTS provider that generates a simple tone as audio."""

    def __init__(self):
        logger.info("DUMMY_TTS_PROVIDER_INITIALIZED")

    async def synthesize(
        self,
        text: str,
        voice_id: Optional[str] = None
    ) -> bytes:
        """
        Generate a simple WAV tone based on text length.

        Returns a valid WAV file with a tone.
        """
        logger.info("DUMMY_TTS_SYNTHESIZE", extra={
            "text_length": len(text),
            "voice_id": voice_id
        })

        sample_rate = 22050
        duration = min(len(text) * 0.05, 3.0)
        frequency = 440.0

        num_samples = int(sample_rate * duration)

        audio_data = []
        for i in range(num_samples):
            value = int(16384 * math.sin(2 * math.pi * frequency * i / sample_rate))
            audio_data.append(struct.pack('<h', value))

        audio_bytes = b''.join(audio_data)

        wav_header = self._create_wav_header(len(audio_bytes), sample_rate)

        logger.info("DUMMY_TTS_SYNTHESIZE_COMPLETE", extra={
            "audio_size_bytes": len(wav_header) + len(audio_bytes),
            "duration_seconds": duration
        })

        return wav_header + audio_bytes

    def _create_wav_header(self, data_size: int, sample_rate: int) -> bytes:
        """Create a WAV file header."""
        num_channels = 1
        bits_per_sample = 16
        byte_rate = sample_rate * num_channels * bits_per_sample // 8
        block_align = num_channels * bits_per_sample // 8

        header = b'RIFF'
        header += struct.pack('<I', 36 + data_size)
        header += b'WAVE'
        header += b'fmt '
        header += struct.pack('<I', 16)
        header += struct.pack('<H', 1)
        header += struct.pack('<H', num_channels)
        header += struct.pack('<I', sample_rate)
        header += struct.pack('<I', byte_rate)
        header += struct.pack('<H', block_align)
        header += struct.pack('<H', bits_per_sample)
        header += b'data'
        header += struct.pack('<I', data_size)

        return header
