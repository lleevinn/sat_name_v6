#!/usr/bin/env python3

"""
IRIS VOICE INPUT - Complete Voice Recognition System v4.2 FIXED

✅ ГЛАВНЫЕ ИСПРАВЛЕНИЯ v4.2:
1. last_vosk_result_time ОБНОВЛЯЕТСЯ на КАЖДОМ результате (final или partial)
2. Pause detector работает правильно (1.5s пауза = конец фразы)
3. Вторая команда ОБРАБАТЫВАЕТСЯ как is_final=True
4. AI генерирует в отдельном потоке (не блокирует voice)
"""

import os
import sys
import threading
import time
import queue
import json
import logging
from typing import Optional, Callable, List, Dict, Any, Tuple
from dataclasses import dataclass
from enum import Enum

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('voice.log', encoding='utf-8')
    ]
)

logger = logging.getLogger('VoiceInput')

# Import voice recognition libraries
try:
    from vosk import Model, KaldiRecognizer, SetLogLevel
    SetLogLevel(-1)
    VOSK_AVAILABLE = True
    logger.info("✅ Vosk успешно импортирован")
except ImportError:
    VOSK_AVAILABLE = False
    logger.warning("⚠️ Vosk не импортирован. pip install vosk")

try:
    import speech_recognition as sr
    SR_AVAILABLE = True
    logger.info("✅ SpeechRecognition успешно импортирован")
except ImportError:
    SR_AVAILABLE = False
    logger.warning("⚠️ SpeechRecognition не импортирован. pip install SpeechRecognition")

try:
    import pyaudio
    PYAUDIO_AVAILABLE = True
    logger.info("✅ PyAudio успешно импортирован")
except ImportError:
    PYAUDIO_AVAILABLE = False
    logger.warning("⚠️ PyAudio не импортирован. pip install pyaudio")

try:
    import sounddevice as sd
    SOUNDDEVICE_AVAILABLE = True
except Exception:
    SOUNDDEVICE_AVAILABLE = False
    logger.info("⚠️ SoundDevice пропущен (требует PortAudio)")

# Constants
WAKEWORD_VARIANTS = ['ирис', 'iris', 'айрис', 'ирус', 'ириш', 'ai iris']

QUICK_COMMANDS = {
    'стоп': 'stop',
    'стопп': 'stop',
    'выход': 'exit',
    'пауза': 'pause',
    'продолжай': 'resume',
    'громче': 'volume_up',
    'тише': 'volume_down',
    'выруб': 'mute',
    'включи': 'unmute',
    'помощь': 'help',
    'команды': 'commands',
    'статус': 'stats',
}

# Sentence ending markers
SENTENCE_ENDINGS = ['.', '!', '?', '...']
PAUSE_THRESHOLD = 1.5  # 1.5 сек паузы = конец фразы

@dataclass
class RecognitionStats:
    """Statistics for voice recognition"""
    total_phrases: int = 0
    wake_detected: int = 0
    vosk_success: int = 0
    google_success: int = 0
    avg_confidence: float = 0.0
    last_recognition: str = ""
    audio_quality: float = 0.0

@dataclass
class AudioSettings:
    """Audio configuration"""
    sample_rate: int = 16000
    chunk_size: int = 1600
    channels: int = 1
    energy_threshold: int = 3000
    pause_threshold: float = 0.5
    phrase_threshold: float = 0.3
    non_speaking_duration: float = 0.3
    dynamic_threshold: bool = True

class VoiceInput:
    """
    Complete voice input system with Vosk + Google Speech Recognition
    
    ✅ FIXED v4.2:
    - last_vosk_result_time обновляется на КАЖДОМ результате
    - Pause detector работает правильно
    - Вторая команда обрабатывается
    - AI генерирует в отдельном потоке
    """

    def __init__(
        self,
        wake_word: str = 'ирис',
        sensitivity: float = 0.8,
        mode: str = 'hybrid',
        vosk_model_path: Optional[str] = None,
        audio_device_index: Optional[int] = None,
        sample_rate: int = 16000,
        enable_analytics: bool = True,
        conversation_timeout: float = 30.0,
        tts_interrupt_callback: Optional[Callable[[], None]] = None
    ):
        """Initialize VoiceInput system"""

        print("=" * 60)
        print("[VOICE] Инициализация системы голосового ввода v4.2 FIXED...")
        print("=" * 60)

        # Core settings
        self.wake_word = wake_word.lower()
        self.sensitivity = max(0.1, min(1.0, sensitivity))
        self.mode = mode
        self.audio_device_index = audio_device_index
        self.sample_rate = sample_rate
        self.enable_analytics = enable_analytics
        self.conversation_timeout = conversation_timeout
        self.tts_interrupt_callback = tts_interrupt_callback

        # Audio settings
        self.audio_settings = AudioSettings(
            sample_rate=sample_rate,
            energy_threshold=int(1500 + (3500 - 1500) * (1 - self.sensitivity))
        )

        # State management
        self.is_listening = False
        self.is_active = False
        self.is_calibrating = False
        self.conversation_active = False
        self.is_processing_command = False

        # Timeouts
        self.activation_timeout = conversation_timeout
        self.last_activation_time = 0
        self.last_audio_time = 0
        self.last_speech_time = 0
        self.last_phrase_text = ""
        self.current_partial_phrase = ""
        self.speech_started_time = 0
        self.user_speaking = False

        # ✅ FIXED: last_vosk_result_time ОБНОВЛЯЕТСЯ НА КАЖДОМ РЕЗУЛЬТАТЕ!
        self.last_vosk_result_time = 0  # Время последнего результата от Vosk (final или partial)
        self.phrase_finalization_timeout = 1.5  # 1.5s паузы = конец фразы

        # Command queue and history
        self.command_queue = queue.PriorityQueue()
        self.audio_buffer = queue.Queue()

        # Callbacks
        self.command_callback: Optional[Callable[[str], None]] = None
        self.wake_callback: Optional[Callable[[], None]] = None
        self.error_callback: Optional[Callable[[Exception], None]] = None

        # Recognition history
        self.recognition_history: List[Dict[str, Any]] = []
        self.max_history = 100
        self.stats = RecognitionStats()

        # Duplicate command prevention
        self.last_command = ""
        self.last_command_time = 0
        self.duplicate_timeout = 0.3

        # Vosk setup
        self.vosk_model = None
        self.vosk_recognizer = None
        self._init_vosk(vosk_model_path)

        # Google Speech Recognition setup
        self.sr_recognizer = None
        self._init_google_speech()

        # Audio device setup
        self.audio_stream = None
        self.pyaudio_instance = None
        self._init_audio_device()

        # Threads
        self.listener_thread: Optional[threading.Thread] = None
        self.processor_thread: Optional[threading.Thread] = None
        self.analytics_thread: Optional[threading.Thread] = None
        self.pause_detector_thread: Optional[threading.Thread] = None

        # Print system info
        self._print_system_info()

        print("=" * 60)
        print("[VOICE] ✅ Все компоненты инициализированы")
        print(f"[VOICE] ⏱️ Режим разговора: {self.conversation_timeout}s (таймер обновляется при речи!)")
        print("[VOICE] 🎙️ При вашей речи будет вызван TTS interrupt callback")
        print(f"[VOICE] ⏸️ Детектор паузы: {self.phrase_finalization_timeout}s")
        print("=" * 60)

    def _init_vosk(self, model_path: Optional[str] = None):
        """Initialize Vosk model for offline speech recognition"""
        if not VOSK_AVAILABLE:
            logger.warning("[VOICE] Vosk недоступен")
            return

        model_paths = [
            model_path,
            'models/vosk-model-ru-0.22',
            'vosk-model-ru-0.22',
            os.path.expanduser('~/.vosk/vosk-model-ru-0.22'),
            '/usr/share/vosk/vosk-model-ru-0.22',
        ]

        for path in model_paths:
            if path and os.path.exists(path):
                try:
                    self.vosk_model = Model(path)
                    self.vosk_recognizer = KaldiRecognizer(self.vosk_model, self.sample_rate)
                    self.vosk_recognizer.SetWords(True)
                    logger.info(f"[VOICE] ✅ Модель Vosk загружена: {path}")
                    return
                except Exception as e:
                    logger.error(f"[VOICE] Ошибка загрузки Vosk: {e}")

        logger.warning("[VOICE] Vosk модель не найдена")

    def _init_google_speech(self):
        """Initialize Google Speech Recognition"""
        if not SR_AVAILABLE:
            logger.warning("[VOICE] Google Speech Recognition недоступен")
            return

        try:
            self.sr_recognizer = sr.Recognizer()
            self.sr_recognizer.pause_threshold = self.audio_settings.pause_threshold
            self.sr_recognizer.phrase_threshold = self.audio_settings.phrase_threshold
            self.sr_recognizer.non_speaking_duration = self.audio_settings.non_speaking_duration
            self.sr_recognizer.energy_threshold = self.audio_settings.energy_threshold
            self.sr_recognizer.dynamic_energy_threshold = self.audio_settings.dynamic_threshold
            logger.info("[VOICE] ✅ SpeechRecognition инициализирован")
        except Exception as e:
            logger.error(f"[VOICE] Ошибка инициализации SpeechRecognition: {e}")

    def _init_audio_device(self):
        """Initialize audio device and list available devices"""
        logger.info("[VOICE] Поиск аудиоустройств...")

        if not PYAUDIO_AVAILABLE:
            logger.warning("[VOICE] PyAudio недоступен")
            return

        try:
            self.pyaudio_instance = pyaudio.PyAudio()
            device_count = self.pyaudio_instance.get_device_count()
            logger.info(f"[VOICE] Найдено аудиоустройств: {device_count}")

            for i in range(device_count):
                device_info = self.pyaudio_instance.get_device_info_by_index(i)
                if device_info.get('maxInputChannels', 0) > 0:
                    print(f" [{i}] {device_info.get('name')}")

            self.audio_device_index = self.audio_device_index or self.pyaudio_instance.get_default_input_device_info()['index']
            logger.info(f"[VOICE] Используется устройство: {self.audio_device_index}")

        except Exception as e:
            logger.error(f"[VOICE] Ошибка инициализации PyAudio: {e}")

    def _print_system_info(self):
        """Print system information"""
        print("\n[VOICE] 📊 СИСТЕМНАЯ ИНФОРМАЦИЯ")
        print(f" • Wake word: '{self.wake_word}'")
        print(f" • Чувствительность: {self.sensitivity:.1f}")
        print(f" • Режим распознавания: {self.mode}")
        print(f" • Частота дискретизации: {self.sample_rate} Hz")
        print(f" • Vosk доступен: {'✅' if VOSK_AVAILABLE else '❌'}")
        print(f" • Google Speech доступен: {'✅' if SR_AVAILABLE else '❌'}")
        print(f" • PyAudio доступен: {'✅' if PYAUDIO_AVAILABLE else '❌'}")
        print(f" • SoundDevice доступен: {'✅' if SOUNDDEVICE_AVAILABLE else '❌'}")
        print(f" • Аналитика: {'✅' if self.enable_analytics else '❌'}")

    def check_wakeword(self, text: str, confidence: float = 1.0) -> Tuple[bool, str]:
        """
        Check if wake word is in text with fuzzy matching
        Returns: (is_wake_word, cleaned_text)
        """
        if not text or len(text.strip()) < 2:
            return False, text

        text_lower = text.lower().strip()
        words = text_lower.split()

        # Method 1: Exact substring match
        for variant in WAKEWORD_VARIANTS:
            if variant in text_lower:
                logger.debug(f"[VOICE] Wake word variant found: {variant}")
                return True, text_lower.replace(variant, '', 1).strip()

        # Method 2: Fuzzy matching
        for word in words:
            if len(word) >= 4:
                for variant in WAKEWORD_VARIANTS:
                    if word.startswith(variant[:4]) and len(variant) >= 4:
                        logger.debug(f"[VOICE] Wake word fuzzy match: {word} ~= {variant}")
                        return True, text_lower.replace(word, '', 1).strip()

        # Method 3: Prefix matching
        for variant in WAKEWORD_VARIANTS:
            if text_lower.startswith(variant):
                logger.debug(f"[VOICE] Wake word prefix match: {variant}")
                return True, text_lower[len(variant):].strip()

        # Method 4: Character overlap
        wake_chars = set(self.wake_word)
        for word in words:
            if len(word) >= 3:
                word_chars = set(word)
                overlap = len(wake_chars & word_chars)
                if overlap >= len(wake_chars) * 0.7:
                    logger.debug(f"[VOICE] Wake word fuzzy overlap: {word}")
                    return True, text_lower.replace(word, '', 1).strip()

        return False, text_lower

    def extract_command(self, text: str) -> str:
        """Extract and clean command from text"""
        if not text:
            return ""

        text_lower = text.lower().strip()

        # Check for quick commands
        for cmd_key, cmd_value in QUICK_COMMANDS.items():
            if cmd_key in text_lower:
                return cmd_value

        # Remove wake word if present
        is_wake, cleaned = self.check_wakeword(text_lower)
        if is_wake:
            return cleaned

        return text_lower

    def is_phrase_complete(self, text: str, time_since_last_speech: float) -> bool:
        """
        Determine if phrase is complete
        Returns True if text ends with punctuation OR pause > 1.5s
        """
        # Check for ending punctuation
        for ending in SENTENCE_ENDINGS:
            if text.rstrip().endswith(ending):
                logger.debug(f"[VOICE] Фраза завершена (пунктуация): {text}")
                return True

        # Check for pause duration
        if time_since_last_speech > PAUSE_THRESHOLD:
            logger.debug(f"[VOICE] Фраза завершена (пауза {time_since_last_speech:.1f}s): {text}")
            return True

        return False

    def process_recognition(self, text: str, is_final: bool = False):
        """
        ✅ ОБРАБОТИТЬ РАСПОЗНАННЫЙ ТЕКСТ
        Когда is_final=True → вызывается command_callback
        """
        if not text or len(text.strip()) < 2:
            return

        # 🎙️ ОБНОВЛЯЕМ ТАЙМЕР И last_vosk_result_time
        current_time = time.time()
        self.last_speech_time = current_time
        self.last_vosk_result_time = current_time  # ✅ ОБНОВЛЯЕТСЯ НА КАЖДОМ РЕЗУЛЬТАТЕ!

        # Если в режиме беседы - обновляем activation_timeout!
        if self.conversation_active:
            self.last_activation_time = current_time
            logger.debug(f"[VOICE] ⏱️ Таймер обновлён: {self.conversation_timeout}s")

        # 🎙️ Если пользователь говорит - прерываем TTS!
        if self.tts_interrupt_callback:
            try:
                logger.info("[VOICE] 🔇 Прерываю TTS (пользователь начал говорить)")
                self.tts_interrupt_callback()
            except Exception as e:
                logger.error(f"[VOICE] Ошибка TTS interrupt: {e}")

        # Filter pure numbers
        text_clean = text.strip()
        parts = text_clean.split()
        all_numbers = all(all(c.isdigit() or c == '.' or c == '-' for c in part) for part in parts)

        if all_numbers and len(parts) > 0:
            logger.debug(f"[VOICE] Пропущена числовая последовательность: {text_clean}")
            return

        # Update statistics
        self.stats.total_phrases += 1
        self.stats.last_recognition = text

        # Store in history
        self.recognition_history.append({
            'text': text,
            'timestamp': current_time,
            'is_final': is_final
        })

        if len(self.recognition_history) > self.max_history:
            self.recognition_history.pop(0)

        logger.info(f"🌐 [VOICE] Распознано: '{text}' (final={is_final})")

        # Check for wake word
        is_wake, cleaned_text = self.check_wakeword(text)

        if is_wake:
            # ═════════════════════════════════════════════════════════
            # РЕЖИМ 1: ОБНАРУЖЕН WAKE WORD
            # ═════════════════════════════════════════════════════════

            if current_time - self.last_activation_time < 1.0:
                logger.debug(f"[VOICE] Дубль wake word, пропускаем")
                return

            self.stats.wake_detected += 1
            logger.info(f"[VOICE] ✅ Wake word найден: '{self.wake_word}'")

            # Activate conversation mode
            self.is_active = True
            self.conversation_active = True
            self.last_activation_time = current_time
            self.last_speech_time = current_time
            self.current_partial_phrase = cleaned_text

            # Call wake callback
            if self.wake_callback:
                try:
                    self.wake_callback()
                except Exception as e:
                    logger.error(f"[VOICE] Ошибка wake callback: {e}")
                    if self.error_callback:
                        self.error_callback(e)

            # Если есть текст после wake word - обработай его как команду
            if cleaned_text and len(cleaned_text.strip()) > 2:
                self.handle_command(cleaned_text)

        elif self.conversation_active:
            # ═════════════════════════════════════════════════════════
            # РЕЖИМ 2: РЕЖИМ РАЗГОВОРА
            # ═════════════════════════════════════════════════════════

            self.current_partial_phrase = text

            # Проверяем завершённость фразы
            time_since_speech = current_time - self.last_speech_time

            # ✅ ГЛАВНОЕ УСЛОВИЕ: Когда распознавание ЗАВЕРШЕНО
            if is_final:
                # ФРАЗА ЗАВЕРШЕНА - обработаем команду!
                self.last_phrase_text = text
                logger.info(f"[VOICE] 📝 Полная фраза: '{text}' (is_final=True)")

                # ✅ ВЫЗЫВАЕМ HANDLE_COMMAND
                self.handle_command(text)

            else:
                # Still waiting for more input
                logger.debug(f"[VOICE] ⏳ Неполная фраза: '{text}' (жду продолжение...)")

    def handle_command(self, command: str):
        """
        ✅ ОБРАБОТКА КОМАНДЫ - Здесь вызывается command_callback!
        """
        if not command:
            return

        # Clean command
        clean_command = command.strip().lower()

        # Remove wake word if still present
        if clean_command.startswith(self.wake_word):
            clean_command = clean_command[len(self.wake_word):].strip()

        if not clean_command or len(clean_command.strip()) < 2:
            return

        # Check for duplicate commands
        current_time = time.time()
        if self.last_command == clean_command and current_time - self.last_command_time < self.duplicate_timeout:
            logger.debug(f"[VOICE] Дубль команды, пропускаем: {clean_command}")
            return

        # Update command history
        self.last_command = clean_command
        self.last_command_time = current_time

        # Log command
        logger.info(f"💬 [VOICE] Команда: '{clean_command}'")

        # Mark as processing
        self.is_processing_command = True

        # ✅ ВЫЗЫВАЕМ COMMAND CALLBACK
        if self.command_callback:
            try:
                logger.info(f"[VOICE] 📤 Вызываю command_callback с: '{clean_command}'")
                self.command_callback(clean_command)
                logger.info(f"[VOICE] ✅ Callback выполнен для: '{clean_command}'")
            except Exception as e:
                logger.error(f"[VOICE] Ошибка command callback: {e}")
                if self.error_callback:
                    self.error_callback(e)
        else:
            logger.warning(f"[VOICE] ⚠️ Command callback не установлен!")

        self.is_processing_command = False

        # ✅ НЕ ВЫКЛЮЧАЕМ conversation_active!
        # Позволяем пользователю давать несколько команд подряд

    def _pause_detector_loop(self):
        """⭐ Детектор паузы - вызывает process_recognition с is_final=True когда пауза >= 1.5s"""
        logger.info("[VOICE] ⏸️ Pause detector запущен")

        while self.is_listening:
            try:
                current_time = time.time()

                # Если мы в режиме разговора и был результат Vosk
                if self.conversation_active and self.last_vosk_result_time > 0:
                    time_since_last = current_time - self.last_vosk_result_time

                    # Если прошло >= 1.5 сек без результата и есть текущая фраза
                    if time_since_last >= self.phrase_finalization_timeout and self.current_partial_phrase:
                        logger.info(f"[VOICE] ⏸️ Пауза обнаружена ({time_since_last:.1f}s) → вызываю is_final=True")

                        # Вызываем process_recognition с is_final=True
                        self.process_recognition(self.current_partial_phrase, is_final=True)

                        # Очищаем буфер
                        self.current_partial_phrase = ""
                        self.last_vosk_result_time = 0

                time.sleep(0.1)  # Проверяем каждые 100ms

            except Exception as e:
                logger.error(f"[VOICE] Ошибка pause detector: {e}")
                time.sleep(0.1)

    def recognize_with_vosk(self, audio_data: bytes) -> Tuple[Optional[str], bool]:
        """
        Recognize speech using Vosk (offline)
        Returns: (text, is_final)
        """
        if not self.vosk_recognizer:
            return None, False

        try:
            if self.vosk_recognizer.AcceptWaveform(audio_data):
                result_json = self.vosk_recognizer.Result()
                result = json.loads(result_json)

                text = result.get('result', [])

                if text:
                    if isinstance(text, str):
                        if text.strip():
                            return text.strip(), True
                    elif isinstance(text, list) and len(text) > 0:
                        parts = []
                        for item in text:
                            extracted = None
                            if isinstance(item, dict):
                                extracted = item.get('conf') or item.get('result') or item.get('text') or item.get('word')
                            elif isinstance(item, str):
                                extracted = item
                            elif isinstance(item, (int, float)):
                                continue

                            if extracted:
                                extracted_str = str(extracted).strip()
                                if extracted_str:
                                    parts.append(extracted_str)

                        if parts:
                            result_text = ' '.join(parts).strip()
                            if result_text and len(result_text) > 1:
                                return result_text, True

                text = result.get('text', '').strip()
                if text and len(text) > 1:
                    return text, True

            # Check partial result
            partial_json = self.vosk_recognizer.PartialResult()
            partial = json.loads(partial_json)
            text = partial.get('partial', '').strip()

            if text and len(text) > 3:
                return text, False

        except json.JSONDecodeError:
            pass
        except Exception as e:
            logger.error(f"[VOICE] Ошибка Vosk: {e}")

        return None, False

    def recognize_with_google(self, audio_data) -> Optional[str]:
        """Recognize speech using Google Speech Recognition (online fallback)"""
        if not self.sr_recognizer:
            return None

        try:
            text = self.sr_recognizer.recognize_google(audio_data, language='ru-RU')
            return text
        except sr.UnknownValueError:
            return None
        except sr.RequestError as e:
            logger.error(f"[VOICE] Ошибка Google Speech: {e}")
            return None

    def listen_loop_vosk(self):
        """Main Vosk listening loop"""
        print("[VOICE] 🎯 VOSK LOOP STARTED")
        logger.info("[VOICE] ✅ Прослушивание запущено в режиме 'hybrid'")
        logger.info(f"[VOICE] Запуск Vosk прослушивания... (скажите '{self.wake_word}')")

        if not VOSK_AVAILABLE or not self.vosk_recognizer:
            logger.error("[VOICE] Vosk недоступен!")
            return

        if not PYAUDIO_AVAILABLE:
            logger.warning("[VOICE] PyAudio недоступен, переключаюсь на Google")
            self.listen_loop_google()
            return

        try:
            p = pyaudio.PyAudio()

            try:
                self.audio_stream = p.open(
                    format=pyaudio.paInt16,
                    channels=self.audio_settings.channels,
                    rate=self.audio_settings.sample_rate,
                    input=True,
                    input_device_index=self.audio_device_index,
                    frames_per_buffer=self.audio_settings.chunk_size
                )

                logger.info("[VOICE] ✅ Аудиопоток открыт, начинаем слушать...")

                while self.is_listening:
                    try:
                        audio_data = self.audio_stream.read(self.audio_settings.chunk_size, exception_on_overflow=False)

                        # Recognize with Vosk
                        text, is_final = self.recognize_with_vosk(audio_data)

                        if text:
                            self.process_recognition(text, is_final=is_final)

                        # Check conversation timeout
                        if self.conversation_active:
                            elapsed = time.time() - self.last_activation_time
                            if elapsed > self.activation_timeout:
                                logger.info(f"[VOICE] ⏱️ Таймаут беседы ({self.activation_timeout}s), выключаюсь")
                                self.conversation_active = False
                                self.is_active = False

                    except Exception as e:
                        logger.error(f"[VOICE] Ошибка в Vosk loop: {e}")
                        time.sleep(0.1)

            except Exception as e:
                logger.error(f"[VOICE] Ошибка Vosk loop: {e}")
                self.fallback_to_google()

            finally:
                if self.audio_stream:
                    self.audio_stream.stop_stream()
                    self.audio_stream.close()
                logger.info("[VOICE] Vosk loop остановлен")

        except Exception as e:
            logger.error(f"[VOICE] Ошибка Vosk loop: {e}")
            self.fallback_to_google()

    def listen_loop_google(self):
        """Google Speech Recognition listening loop (fallback)"""
        print("[VOICE] 🔄 GOOGLE LOOP STARTED")
        logger.info("[VOICE] Google Speech Recognition...")

        if not SR_AVAILABLE:
            logger.error("[VOICE] SpeechRecognition недоступен!")
            return

        try:
            with sr.Microphone(device_index=self.audio_device_index, sample_rate=self.audio_settings.sample_rate) as source:
                logger.info("[VOICE] Калибровка микрофона на 2 сек...")
                self.sr_recognizer.adjust_for_ambient_noise(source, duration=2)
                logger.info(f"[VOICE] Пороговое значение энергии: {self.sr_recognizer.energy_threshold}")

                while self.is_listening:
                    try:
                        audio = self.sr_recognizer.listen(source, timeout=10.0)
                        text = self.recognize_with_google(audio)

                        if text:
                            self.process_recognition(text, is_final=True)

                    except sr.WaitTimeoutError:
                        # Check conversation timeout
                        if self.conversation_active:
                            elapsed = time.time() - self.last_activation_time
                            if elapsed > self.activation_timeout:
                                logger.info(f"[VOICE] ⏱️ Таймаут беседы ({self.activation_timeout}s), выключаюсь")
                                self.conversation_active = False
                                self.is_active = False
                        continue

                    except Exception as e:
                        logger.error(f"[VOICE] Ошибка Google loop: {e}")
                        time.sleep(0.5)

        except OSError as e:
            logger.error(f"[VOICE] Ошибка микрофона: {e}")
            self.fallback_to_simple()

        except Exception as e:
            logger.error(f"[VOICE] Ошибка Google loop: {e}")
            self.fallback_to_simple()

        finally:
            logger.info("[VOICE] Google loop остановлен")

    def listen_loop_simple(self):
        """Simple input loop for testing"""
        print("[VOICE] 📝 SIMPLE LOOP STARTED")
        logger.info(f"[VOICE] Simple режим. Скажите '{self.wake_word}'")

        while self.is_listening:
            try:
                user_input = input().strip().lower()
                if user_input:
                    self.process_recognition(user_input, is_final=True)
            except EOFError:
                break
            except KeyboardInterrupt:
                break
            except Exception as e:
                logger.error(f"[VOICE] Ошибка Simple loop: {e}")

    def fallback_to_google(self):
        """Fallback from Vosk to Google"""
        logger.warning("[VOICE] Fallback to Google Speech")
        self.mode = 'google'
        if self.is_listening:
            self.listen_loop_google()

    def fallback_to_simple(self):
        """Fallback to simple input mode"""
        logger.warning("[VOICE] Fallback to Simple mode")
        self.mode = 'simple'
        if self.is_listening:
            self.listen_loop_simple()

    def calibrate_microphone(self):
        """Calibrate microphone for better recognition"""
        if self.is_calibrating:
            return

        self.is_calibrating = True
        logger.info("[VOICE] Калибровка микрофона...")

        try:
            if self.sr_recognizer:
                with sr.Microphone(device_index=self.audio_device_index) as source:
                    logger.info("[VOICE] Слушаю окружающие звуки на 2 сек...")
                    self.sr_recognizer.adjust_for_ambient_noise(source, duration=2)
                    logger.info(f"[VOICE] Новое пороговое значение: {self.sr_recognizer.energy_threshold}")

        except Exception as e:
            logger.error(f"[VOICE] Ошибка калибровки: {e}")

        finally:
            self.is_calibrating = False

    def set_command_callback(self, callback: Callable[[str], None]):
        """Set callback for voice commands"""
        self.command_callback = callback
        logger.info("[VOICE] ✅ Command callback установлен")

    def set_wake_callback(self, callback: Callable[[], None]):
        """Set callback for wake word detection"""
        self.wake_callback = callback
        logger.info("[VOICE] ✅ Wake callback установлен")

    def set_error_callback(self, callback: Callable[[Exception], None]):
        """Set callback for errors"""
        self.error_callback = callback
        logger.info("[VOICE] ✅ Error callback установлен")

    def set_tts_interrupt_callback(self, callback: Callable[[], None]):
        """Set callback to interrupt TTS when user speaks"""
        self.tts_interrupt_callback = callback
        logger.info("[VOICE] ✅ TTS interrupt callback установлен")

    def get_recognition_stats(self) -> Dict[str, Any]:
        """Get recognition statistics"""
        remaining_timeout = 0
        if self.conversation_active:
            remaining_timeout = max(0, self.activation_timeout - (time.time() - self.last_activation_time))

        return {
            'total_phrases': self.stats.total_phrases,
            'wake_detected': self.stats.wake_detected,
            'vosk_success': self.stats.vosk_success,
            'google_success': self.stats.google_success,
            'avg_confidence': self.stats.avg_confidence,
            'last_recognition': self.stats.last_recognition,
            'audio_quality': self.stats.audio_quality,
            'queue_size': self.command_queue.qsize(),
            'conversation_active': self.conversation_active,
            'conversation_timeout_remaining': remaining_timeout
        }

    def save_stats(self, filename: str = 'voice_stats.json'):
        """Save statistics to file"""
        try:
            stats_data = {
                'timestamp': time.time(),
                'stats': self.get_recognition_stats(),
                'history': self.recognition_history[-50:]
            }

            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(stats_data, f, indent=2, ensure_ascii=False)

            logger.info(f"[VOICE] Статистика сохранена: {filename}")

        except Exception as e:
            logger.error(f"[VOICE] Ошибка сохранения: {e}")

    def start(self):
        """Start voice input system"""
        if self.is_listening:
            logger.warning("[VOICE] Уже запущено")
            return

        self.is_listening = True

        # Select listening mode
        if self.mode == 'vosk':
            target = self.listen_loop_vosk
        elif self.mode == 'google':
            target = self.listen_loop_google
        elif self.mode == 'simple':
            target = self.listen_loop_simple
        else:  # hybrid (default)
            target = self.listen_loop_vosk

        # Start listener thread
        self.listener_thread = threading.Thread(
            target=target,
            daemon=True,
            name='VoiceInput-Listener'
        )
        self.listener_thread.start()

        # ⭐ Start pause detector thread
        self.pause_detector_thread = threading.Thread(
            target=self._pause_detector_loop,
            daemon=True,
            name='VoiceInput-PauseDetector'
        )
        self.pause_detector_thread.start()

        logger.info(f"[VOICE] ✅ Запущено в режиме '{self.mode}'")

    def stop(self):
        """Stop voice input system"""
        if not self.is_listening:
            return

        self.is_listening = False
        self.is_active = False
        self.conversation_active = False

        # Wait for thread
        if self.listener_thread and self.listener_thread.is_alive():
            self.listener_thread.join(timeout=2.0)

        logger.info("[VOICE] ✅ Прослушивание остановлено")

def create_voice_input(
    wake_word: str = 'ирис',
    sensitivity: float = 0.8,
    mode: str = 'hybrid',
    conversation_timeout: float = 30.0,
    tts_interrupt_callback: Optional[Callable[[], None]] = None,
    **kwargs
) -> VoiceInput:
    """Factory function to create VoiceInput instance"""
    logger.info(f"[VOICE] Создание VoiceInput: wake_word={wake_word}, mode={mode}, timeout={conversation_timeout}s")

    return VoiceInput(
        wake_word=wake_word,
        sensitivity=sensitivity,
        mode=mode,
        conversation_timeout=conversation_timeout,
        tts_interrupt_callback=tts_interrupt_callback,
        **kwargs
    )
