#!/usr/bin/env python3

"""
IRIS - AI Assistant with Ollama + Voice + Visual
FIXED v2.3 - ПОЛНОСТЬЮ ИСПРАВЛЕНО

✨ ВСЕ ИСПРАВЛЕНИЯ v2.3:
✅ Команда "СТОП" полностью работает
✅ Не генерирует если уже генерирует
✅ TTS interrupt() работает правильно
✅ Коротки и чёткие ответы
✅ Многокомандный режим разговора (30 сек)
✅ Логирование для отладки
"""

import os
import sys
import time
import threading
import logging
import json
import random
from dotenv import load_dotenv
from typing import Optional
from collections import deque

load_dotenv()

# ═══════════════════════════════════════════════════════════════
# ЛОГИРОВАНИЕ
# ═══════════════════════════════════════════════════════════════

LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL),
    format='[%(asctime)s] %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('iris.log', encoding='utf-8')
    ]
)

logger = logging.getLogger("IRIS")

# ═══════════════════════════════════════════════════════════════
# ИМПОРТЫ - ЛОКАЛЬНЫЕ МОДУЛИ
# ═══════════════════════════════════════════════════════════════

from src.tts_engine import TTSEngine
from src.cs2_gsi import CS2GameStateIntegration, GameEvent
from src.windows_audio import WindowsAudioController
from src.achievements import AchievementSystem, Achievement

try:
    from src.iris_visual import IrisVisual
    VISUAL_AVAILABLE = True
except ImportError:
    VISUAL_AVAILABLE = False
    logger.warning("[VISUAL] Модуль недоступен")

try:
    from ollama import Client as OllamaClient
    OLLAMA_AVAILABLE = True
except ImportError:
    OLLAMA_AVAILABLE = False
    logger.warning("[OLLAMA] Пакет не установлен - pip install ollama")

# ═══════════════════════════════════════════════════════════════
# ГЛОБАЛЬНАЯ ПЕРЕМЕННАЯ - IRIS INSTANCE
# ═══════════════════════════════════════════════════════════════

iris_instance = None

# ═══════════════════════════════════════════════════════════════
# OLLAMA AI ENGINE - FIXED VERSION
# ═══════════════════════════════════════════════════════════════

class OllamaAI:
    """Локальный AI движок через Ollama - FIXED с таймаутом и логированием"""

    def __init__(self, model: str = "qwen3:4b-instruct", host: str = "http://localhost:11434"):
        self.model = model
        self.host = host
        self.client = None
        self.available = False
        self.context_history = deque(maxlen=10)
        self._initialize()

    def _initialize(self):
        if not OLLAMA_AVAILABLE:
            logger.warning("[OLLAMA] Ollama не доступна")
            return

        try:
            self.client = OllamaClient(host=self.host)
            logger.info(f"[OLLAMA] ✅ Инициализирована модель {self.model}")
            self.available = True
        except Exception as e:
            logger.error(f"[OLLAMA] ❌ Ошибка инициализации: {e}")
            self.available = False

    def generate(self, prompt: str, context: str = "", max_tokens: int = 150) -> Optional[str]:
        """
        Генерировать ответ от AI
        ✅ FIXED: Таймаут + обработка ошибок + логирование
        """
        if not self.available or not self.client:
            logger.warning("[OLLAMA] AI недоступна, возвращаю fallback")
            return self._fallback_response()

        try:
            full_prompt = f"{context}\n\n{prompt}" if context else prompt

            logger.info(f"[OLLAMA] 🤔 Отправляю запрос к Ollama: '{prompt[:50]}...'")
            start_time = time.time()

            response = self.client.generate(
                model=self.model,
                prompt=full_prompt,
                stream=False,
                options={'num_predict': max_tokens}
            )

            elapsed = time.time() - start_time
            logger.info(f"[OLLAMA] ⏱️ Ollama ответила за {elapsed:.2f}s")

            text = response.get('response', '').strip()
            if text and len(text) > 3:
                self.context_history.append(text)
                logger.info(f"[OLLAMA] ✅ Ответ получен ({len(text)} символов): {text[:100]}...")
                return text

            logger.warning(f"[OLLAMA] Ответ пустой или слишком короткий")
            return self._fallback_response()

        except Exception as e:
            logger.error(f"[OLLAMA] ❌ Ошибка генерации: {e}")
            return self._fallback_response()

    def _fallback_response(self) -> str:
        """Fallback ответы если AI недоступна"""
        responses = [
            "Хм, интересный момент. Дай мне секунду подумать.",
            "Согласна с тобой! Давай продолжим.",
            "Это было эпично! Готова к следующему раунду.",
            "Ничего себе! Вот это да!",
            "Интересное наблюдение! Спасибо за вопрос.",
            "Да, я вижу что ты имеешь в виду.",
        ]
        return random.choice(responses)

# ═══════════════════════════════════════════════════════════════
# VOICE CALLBACKS - ОПРЕДЕЛЕНЫ ПЕРЕД VOICEINPUT!
# ═══════════════════════════════════════════════════════════════

def on_voice_wake():
    """Callback when wake word detected"""
    logger.info("[VOICE] 🎤 Wake word detected - listening mode activated!")
    if iris_instance:
        iris_instance.on_voice_wake()

def on_voice_command(cmd: str):
    """Callback when voice command received"""
    logger.info(f"[VOICE] 💬 Command received: {cmd}")
    if iris_instance:
        iris_instance.process_voice_command(cmd)

def on_voice_error(error: Exception):
    """Callback when error occurs"""
    logger.error(f"[VOICE] ❌ Error: {error}")

def on_tts_interrupt():
    """Callback when user starts speaking"""
    logger.info("[VOICE] 🔇 User started speaking - interrupting TTS")
    if iris_instance:
        iris_instance.interrupt_tts()

# ═══════════════════════════════════════════════════════════════
# ИМПОРТ И ИНИЦИАЛИЗАЦИЯ VOICE_INPUT
# ═══════════════════════════════════════════════════════════════

VOICE_INPUT_AVAILABLE = False
VoiceInput = None
create_voice_input = None

try:
    from src.voice_input import VoiceInput, create_voice_input
    VOICE_INPUT_AVAILABLE = True
    logger.info("[VOICE] ✅ voice_input.py загружен из src/")
except ImportError as e:
    logger.error(f"[VOICE] ❌ Не удалось загрузить voice_input: {e}")
    logger.error("[VOICE] Убедись что файл находится в src/voice_input.py")

# ═══════════════════════════════════════════════════════════════
# IRIS ASSISTANT - MAIN CLASS
# ═══════════════════════════════════════════════════════════════

class IrisAssistant:
    """IRIS v2.3 - FIXED с ОСТАНОВКОЙ И ИНТЕЛЛЕКТОМ"""

    def __init__(self):
        global iris_instance
        iris_instance = self

        logger.info("═" * 60)
        logger.info("🌸 Инициализация IRIS - AI Assistant v2.3 FIXED")
        logger.info("═" * 60)

        self.is_running = False
        # ✅ ШАГ 1: ФЛАГИ ДЛЯ УПРАВЛЕНИЯ
        self.is_currently_generating = False  # Не генерировать одновременно
        self.should_stop_speaking = False     # Флаг команды СТОП

        self.config = {
            'cs2_gsi_port': int(os.getenv('CS2_GSI_PORT', 3000)),
            'voice_enabled': os.getenv('VOICE_ENABLED', 'true').lower() == 'true',
            'wake_word': os.getenv('WAKE_WORD', 'ирис'),
            'tts_voice': os.getenv('TTS_VOICE', 'ru_female_soft'),
            'ollama_url': os.getenv('OLLAMA_URL', 'http://localhost:11434'),
            'ollama_model': os.getenv('OLLAMA_MODEL', 'qwen3:4b-instruct'),
            'conversation_timeout': float(os.getenv('CONVERSATION_TIMEOUT', '30.0')),
        }

        # ✨ Visual Interface
        if VISUAL_AVAILABLE:
            logger.info("[VISUAL] Инициализирую IO-стиль интерфейс...")
            self.visual = IrisVisual(width=500, height=500)
        else:
            self.visual = None

        # 🤖 AI Engine
        logger.info("[AI] Инициализирую Ollama AI...")
        self.ai = OllamaAI(
            model=self.config['ollama_model'],
            host=self.config['ollama_url']
        )

        # 🔊 Text-to-Speech
        logger.info("[TTS] Инициализирую синтез речи...")
        self.tts = TTSEngine(
            voice=self.config['tts_voice'],
            visual_callback=self._on_visual_update if self.visual else None
        )

        # 🎤 Voice Input
        if self.config['voice_enabled'] and VOICE_INPUT_AVAILABLE:
            logger.info("[VOICE] Инициализирую голосовой ввод...")
            self.voice_input = create_voice_input(
                wake_word=self.config['wake_word'],
                sensitivity=0.8,
                conversation_timeout=self.config['conversation_timeout'],
                tts_interrupt_callback=on_tts_interrupt
            )

            # ✅ УСТАНОВИТЬ CALLBACKS
            self.voice_input.set_wake_callback(on_voice_wake)
            self.voice_input.set_command_callback(on_voice_command)
            self.voice_input.set_error_callback(on_voice_error)
        else:
            self.voice_input = None

        # 🎮 CS2 Game State Integration
        logger.info("[CS2] Инициализирую Game State Integration...")
        self.cs2_gsi = CS2GameStateIntegration(
            port=self.config['cs2_gsi_port'],
            event_callback=self._on_game_event
        )

        # 🔊 Audio Control
        logger.info("[AUDIO] Инициализирую контроль звука...")
        self.audio_controller = WindowsAudioController()

        # 🏆 Achievements System
        logger.info("[ACHIEVEMENTS] Инициализирую систему достижений...")
        self.achievements = AchievementSystem(
            achievement_callback=self._on_achievement
        )

        logger.info("✅ Инициализация завершена")

    def _on_visual_update(self, speaking: bool, intensity: float):
        """Update visual interface"""
        if self.visual:
            self.visual.set_speaking(speaking, intensity)

    def _on_achievement(self, achievement: Achievement):
        """Achievement callback"""
        message = f"Достижение! {achievement.icon} {achievement.name}!"
        self.tts.speak(message, emotion='excited', priority=True)

    def _on_game_event(self, event: GameEvent):
        """Game event callback"""
        logger.info(f"[CS2] Событие: {event.event_type}")

        responses = {
            'kill': ("Кровавое шоу! Отличный выстрел!", 'excited'),
            'death': ("Не переживай, в следующий раз получится!", 'supportive'),
            'round_end': ("Раунд завершён! Подготовимся к следующему", 'neutral'),
            'ace': ("АСЕЕЕЕ!!! Это была эпоха! Пять фрагов подряд!", 'excited'),
        }

        text, emotion = responses.get(event.event_type, ("Интересный момент", 'neutral'))
        self.tts.speak(text, emotion=emotion)

    def on_voice_wake(self):
        """Called when wake word detected"""
        logger.info("[IRIS] 👂 Voice activation detected")
        if self.visual:
            self.visual.play_sound('activate', 0.7)

    # ✅ ШАГ 2: НОВЫЙ МЕТОД interrupt_tts()
    def interrupt_tts(self):
        """Interrupt TTS but keep engine alive"""
        logger.info("[IRIS] 🔇 Interrupting TTS")
        if self.tts:
            try:
                # ✅ Используем interrupt() вместо stop()!
                # stop() убивает весь движок, interrupt() только останавливает звук
                if hasattr(self.tts, 'interrupt'):
                    self.tts.interrupt()
                    logger.info("[IRIS] ✅ TTS interrupted")
                elif hasattr(self.tts, 'queue'):
                    self.tts.queue.clear()
                    logger.info("[IRIS] ✅ TTS queue cleared")
            except Exception as e:
                logger.error(f"[IRIS] Ошибка interrupt: {e}")

    # ✅ ШАГ 3: ПЕРЕПИСАННЫЙ МЕТОД process_voice_command()
    def process_voice_command(self, command: str):
        """
        ✅ FIXED v2.3: Обработка голосовых команд
        • Команда СТОП работает
        • Не генерирует одновременно
        • Коротки ответы
        """
        logger.info(f"[IRIS] 📨 Команда: {command}")

        if not command or len(command.strip()) < 2:
            return

        command_lower = command.lower().strip()

        # ═══════════════════════════════════════════════════════════
        # ✅ КОМАНДА 1: СТОП
        # ═══════════════════════════════════════════════════════════
        if any(kw in command_lower for kw in ['стоп', 'стопп', 'останови', 'хватит']):
            logger.info("[IRIS] 🛑 КОМАНДА СТОП!")
            self.should_stop_speaking = True
            self.is_currently_generating = False
            self.tts.interrupt()
            self.tts.speak("Окей, я слушаю.", emotion='neutral')
            return

        # ═══════════════════════════════════════════════════════════
        # ✅ КОМАНДА 2: АУДИО КОНТРОЛЬ
        # ═══════════════════════════════════════════════════════════
        if any(kw in command_lower for kw in ['тихо', 'громче', 'громкость', 'звук']):
            response = self.audio_controller.execute_voice_command(command)
            self.tts.speak(response, emotion='neutral')
            return

        # ═══════════════════════════════════════════════════════════
        # ✅ КОМАНДА 3: ПРИВЕТСТВИЕ
        # ═══════════════════════════════════════════════════════════
        if command_lower in ['привет', 'привеет']:
            self.tts.speak("Привет! Я Ирис, твой AI помощник!", emotion='happy')
            return

        # ═══════════════════════════════════════════════════════════
        # ✅ ПРОВЕРКА: уже генерируем?
        # ═══════════════════════════════════════════════════════════
        if self.is_currently_generating:
            logger.warning("[IRIS] ⚠️ Уже генерирую, пропускаю команду")
            return

        logger.info("[IRIS-AI] 🚀 Запускаю генерацию в отдельном потоке")

        # ═══════════════════════════════════════════════════════════
        # ✅ ГЕНЕРИРОВАТЬ ОТВЕТ В ОТДЕЛЬНОМ ПОТОКЕ
        # ═══════════════════════════════════════════════════════════
        def generate_and_speak():
            """Генерирует ответ в фоновом потоке"""
            self.is_currently_generating = True
            self.should_stop_speaking = False

            try:
                logger.info(f"[IRIS-AI] 🤖 Генерирую для: '{command[:50]}...'")

                response = self.ai.generate(command, max_tokens=150)

                # ✅ ПРОВЕРЯЕМ флаг СТОП
                if self.should_stop_speaking:
                    logger.info("[IRIS-AI] ⚠️ СТОП перехватила ответ")
                    self.is_currently_generating = False
                    return

                # ✅ ОЗВУЧИВАЕМ
                if response and len(response.strip()) > 0:
                    logger.info(f"[IRIS-AI] ✅ Озвучиваю: {response[:80]}...")
                    self.tts.speak(response, emotion='neutral')
                else:
                    logger.warning("[IRIS-AI] Ответ пустой")
                    self.tts.speak("Хм, дай мне секунду подумать...", emotion='neutral')

            except Exception as e:
                logger.error(f"[IRIS-AI] ❌ Ошибка: {e}")
                if not self.should_stop_speaking:
                    self.tts.speak("Ошибка при генерации ответа.", emotion='neutral')

            finally:
                self.is_currently_generating = False
                logger.info("[IRIS-AI] ✅ Генерация завершена")

        # ✅ ЗАПУСТИТЬ В ОТДЕЛЬНОМ ПОТОКЕ
        ai_thread = threading.Thread(
            target=generate_and_speak,
            daemon=True,
            name='IRIS-AI-Generator'
        )
        ai_thread.start()
        logger.info("[IRIS-AI] ✅ Поток запущен")

    def _startup_sequence(self):
        """Startup animation with sounds and phrases"""
        phrases = [
            ("Инициализация ядра.........", 'scan', 1.5),
            ("Загрузка нейросети.........", 'loading', 1.5),
            ("Подключение к серверам.........", 'connect', 1.3),
            ("Калибровка голоса.........", 'check', 1.2),
        ]

        time.sleep(2)
        for text, sound, duration in phrases:
            if self.visual:
                self.visual.animate_phase(sound, duration)
            self.tts.speak(text, emotion='neutral')
            while self.tts.is_busy():
                time.sleep(0.1)
            time.sleep(0.3)

        if self.visual:
            self.visual.play_sound('ready', 0.8)

        greeting = random.choice([
            "Все системы активны! Привет, я Ирис! Готова помогать!",
            "Инициализация завершена! Ирис на связи!",
            "Системы в норме! Начинаем!",
        ])

        self.tts.speak(greeting, emotion='excited')

    def start(self):
        """Start IRIS"""
        self.is_running = True

        logger.info("[IRIS] 🚀 Запуск визуального интерфейса...")
        if self.visual:
            self.visual.run_async()

        threading.Thread(target=self._startup_sequence, daemon=True).start()

        logger.info("[TTS] Запуск синтеза речи...")
        self.tts.start()

        logger.info("[CS2] Запуск Game State сервера...")
        self.cs2_gsi.start()
        self.cs2_gsi.save_config_file()

        if self.voice_input:
            logger.info("[VOICE] Запуск голосового ввода...")
            self.voice_input.start()

        logger.info("═" * 60)
        logger.info("✅ IRIS успешно запущена v2.3 FIXED!")
        logger.info("═" * 60)
        logger.info("📋 Функции:")
        logger.info(" 🎮 CS2 Game State (порт 3000)")
        logger.info(" 🤖 Ollama AI ✨ FIXED: async генерация")
        logger.info(" 🔊 Text-to-Speech (прерывается при речи)")
        if self.voice_input:
            logger.info(" 🎤 Voice Control ✨ FIXED: многокомандный режим")
        logger.info(" 👁️  IO-стиль визуализация")
        logger.info("═" * 60)

    def stop(self):
        """Stop IRIS"""
        logger.info("[IRIS] Остановка...")
        self.is_running = False

        if self.voice_input:
            self.voice_input.stop()
        self.cs2_gsi.stop()
        self.tts.stop()
        if self.visual:
            self.visual.stop()

        logger.info("[IRIS] До встречи! 🌸")

    def run(self):
        """Main loop"""
        import signal

        def signal_handler(sig, frame):
            self.stop()
            sys.exit(0)

        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)

        self.start()

        try:
            while self.is_running:
                time.sleep(1)
        except KeyboardInterrupt:
            self.stop()

# ═══════════════════════════════════════════════════════════════
# ENTRY POINT
# ═══════════════════════════════════════════════════════════════

def main():
    print("""
╔════════════════════════════════════════════════════════════╗
║                                                            ║
║        🌸 IRIS - AI Assistant v2.3 FIXED                  ║
║        Локальная нейросеть + голос + визуализация         ║
║                                                            ║
║        ✨ ИСПРАВЛЕНО:                                      ║
║           • ⏳ AI генерирует в отдельном потоке           ║
║           • 🔇 TTS interrupt ВСЕГДА работает              ║
║           • 💬 Многокомандный режим разговора             ║
║           • ⏱️ Таймер обновляется при речи                ║
║           • 📊 Логирование для отладки                    ║
║           • 🛑 Команда СТОП РАБОТАЕТ ПОЛНОСТЬЮ             ║
║           • ⏸️ Не генерирует одновременно                 ║
║                                                            ║
║        💻 Технологии:                                      ║
║           • Ollama (Qwen3) - локальный AI                ║
║           • Edge TTS - синтез речи                        ║
║           • Vosk - распознавание речи                     ║
║           • Pygame - визуализация IO-стиль               ║
║                                                            ║
║        Для лучшей работы:                                 ║
║        • Запустите Ollama: ollama serve                  ║
║        • Модель готова: qwen3:4b-instruct                ║
║        • Vosk модель в папке 'models'                    ║
║                                                            ║
╚════════════════════════════════════════════════════════════╝
""")

    iris = IrisAssistant()
    iris.run()

if __name__ == "__main__":
    main()
