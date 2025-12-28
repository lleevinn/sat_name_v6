@"
"""
Utils Package - Вспомогательные утилиты для IRIS AI
"""

from .voice_recorder import VoiceRecorder
from .tts_utils import synthesize_and_play

__all__ = ['VoiceRecorder', 'synthesize_and_play']
"@ | Out-File -FilePath utils/__init__.py -Encoding UTF8