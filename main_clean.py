#!/usr/bin/env python3
"""
IRIS - AI Assistant with Ollama + Voice + Visual
Полностью локальная система - Jarvis style с IO визуализацией
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
from src.voice_input import VoiceInput
from src.cs2_gsi import CS2GameStateIntegration, GameEvent
from src.windows_audio import WindowsAudioController
from src.achievements import AchievementSystem, Achievement

# Визуальный интерфейс
try:
    from src.iris_visual import IrisVisual
    VISUAL_AVAILABLE = True
except ImportError:
    VISUAL_AVAILABLE = False
    logger.warning("[VISUAL] Модуль недоступен")

# Ollama для локального AI
try:
    from ollama import Client as OllamaClient
    OLLAMA_AVAILABLE = True
except ImportError:
    OLLAMA_AVAILABLE = False
    logger.warning("[OLLAMA] Пакет не установлен - pip install ollama")

# ═══════════════════════════════════════════════════════════════
# OLLAMA AI ENGINE - Локальный AI через Ollama
# ═══════════════════════════════════════════════════════════════
class OllamaAI:
    """Локальный AI движок через Ollama"""
    def __init__(self, model: str = "qwen3:4b-instructor", host: str = "http://localhost:11434"):
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
            logger.info(f"[OLLAMA] Инициализирована модель {self.model}")
            self.available = True
        except Exception as e:
            logger.error(f"[OLLAMA] Ошибка инициализации: {e}")
            self.available = False
    
    def generate(self, prompt: str, context: str = "", max_tokens: int = 150) -> Optional[str]:
        """Генерировать ответ от AI"""
        if not self.available or not self.client:
            return self._fallback_response()
        
        try:
            full_prompt = f"{context}\n\n{prompt}" if context else prompt
            
            response = self.client.generate(
                model=self.model,
                prompt=full_prompt,
                stream=False,
                options={'num_predict': max_tokens}
            )
            
            text = response.get('response', '').strip()
            if text:
                self.context_history.append(text)
                return text
            return self._fallback_response()
        
        except Exception as e:
            logger.error(f"[OLLAMA] Ошибка генерации: {e}")
            return self._fallback_response()
    
    def _fallback_response(self) -> str:
        """Fallback ответы если AI недоступна"""
        responses = [
            "Хм, интересный момент. Дай мне секунду подумать.",
            "Согласна с тобой! Давай продолжим.",
            "Это было эпично! Готова к следующему раунду.",
            "Ничего себе! Вот это да!",
        ]
        return random.choice(responses)

# ═══════════════════════════════════════════════════════════════
# IRIS ASSISTANT MAIN CLASS
# ═══════════════════════════════════════════════════════════════
class IrisAssistant:
    def __init__(self):
        logger.info("═" * 60)
        logger.info("🌸 Инициализация IRIS - AI Assistant")
        logger.info("═" * 60)
        
        self.is_running = False
        self.config = {
            'cs2_gsi_port': int(os.getenv('CS2_GSI_PORT', 3000)),
            'voice_enabled': os.getenv('VOICE_ENABLED', 'true').lower() == 'true',
            'wake_word': os.getenv('WAKE_WORD', 'ирис'),
            'tts_voice': os.getenv('TTS_VOICE', 'ru_female_soft'),
            'ollama_url': os.getenv('OLLAMA_URL', 'http://localhost:11434'),
            'ollama_model': os.getenv('OLLAMA_MODEL', 'qwen3:4b-instructor'),
        }
        
        # ✨ Визуальный интерфейс
        if VISUAL_AVAILABLE:
            logger.info("[VISUAL] Инициализирую IO-стиль интерфейс...")
            self.visual = IrisVisual(width=500, height=500)
        else:
            self.visual = None
            logger.warning("[VISUAL] Визуал недоступен (требуется pygame)")
        
        # 🤖 AI
        logger.info("[AI] Инициализирую Ollama AI...")
        self.ai = OllamaAI(
            model=self.config['ollama_model'],
            host=self.config['ollama_url']
        )
        
        # 🔊 TTS
        logger.info("[TTS] Инициализирую синтез речи...")
        self.tts = TTSEngine(
            voice=self.config['tts_voice'],
            visual_callback=self._on_visual_update if self.visual else None
        )
        
        # 🎤 Voice Input
        if self.config['voice_enabled']:
            logger.info("[VOICE] Инициализирую голосовой ввод...")
            self.voice_input = VoiceInput(
                wake_word=self.config['wake_word'],
                sensitivity=0.8
            )
            self.voice_input.set_command_callback(self.process_voice_command)
        else:
            self.voice_input = None
            logger.info("[VOICE] Голосовой ввод отключён")
        
        # 🎮 CS2 GSI
        logger.info("[CS2] Инициализирую Game State Integration...")
        self.cs2_gsi = CS2GameStateIntegration(
            port=self.config['cs2_gsi_port'],
            event_callback=self._on_game_event
        )
        
        # 🔊 Audio Control
        logger.info("[AUDIO] Инициализирую контроль звука...")
        self.audio_controller = WindowsAudioController()
        
        # 🏆 Achievements
        logger.info("[ACHIEVEMENTS] Инициализирую систему достижений...")
        self.achievements = AchievementSystem(
            achievement_callback=self._on_achievement
        )
        
        logger.info("✅ Инициализация завершена")
    
    def _on_visual_update(self, speaking: bool, intensity: float):
        """Обновить визуальный интерфейс"""
        if self.visual:
            self.visual.set_speaking(speaking, intensity)
    
    def _on_achievement(self, achievement: Achievement):
        """Обработка достижений"""
        message = f"Достижение! {achievement.icon} {achievement.name}!"
        self.tts.speak(message, emotion='excited', priority=True)
    
    def _on_game_event(self, event: GameEvent):
        """Обработка событий CS2"""
        logger.info(f"[CS2] Событие: {event.event_type}")
        
        responses = {
            'kill': ("Кровавое шоу! Отличный выстрел!", 'excited'),
            'death': ("Не переживай, в следующий раз получится!", 'supportive'),
            'round_end': ("Раунд завершён! Подготовимся к следующему", 'neutral'),
            'ace': ("АСЕЕЕЕ!!! Это была эпоха! Пять фрагов подряд!", 'excited'),
        }
        
        text, emotion = responses.get(event.event_type, ("Интересный момент", 'neutral'))
        self.tts.speak(text, emotion=emotion)
    
    def process_voice_command(self, command: str):
        """Обработить голосовую команду"""
        logger.info(f"[VOICE] Команда: {command}")
        
        if not command or len(command.strip()) < 2:
            self.tts.speak("Да, я слушаю?", emotion='neutral')
            return
        
        command_lower = command.lower().strip()
        
        # Контрольные команды
        if any(kw in command_lower for kw in ['тихо', 'громче', 'громкость', 'звук']):
            response = self.audio_controller.execute_voice_command(command)
            self.tts.speak(response, emotion='neutral')
            return
        
        if command_lower in ['привет', 'привеет']:
            self.tts.speak("Привет! Я Ирис, твой AI помощник!", emotion='happy')
            return
        
        if command_lower in ['статистика', 'стата']:
            stats = self.achievements.get_stats_summary()
            self.tts.speak(stats[:200], emotion='neutral')
            return
        
        # AI ответ на остальное
        logger.info("[AI] Генерирую ответ...")
        response = self.ai.generate(command)
        if response:
            self.tts.speak(response, emotion='neutral')
    
    def _startup_sequence(self):
        """Красивый стартап с звуками и фразами"""
        phrases = [
            ("Инициализация ядра....", 'scan', 1.5),
            ("Загрузка нейросети....", 'loading', 1.5),
            ("Подключение к серверам....", 'connect', 1.3),
            ("Калибровка голоса....", 'check', 1.2),
        ]
        
        time.sleep(2)
        
        for text, sound, duration in phrases:
            self.visual.animate_phase(sound, duration) if self.visual else None
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
        """Запуск Ирис"""
        self.is_running = True
        
        logger.info("[IRIS] 🚀 Запуск визуального интерфейса...")
        if self.visual:
            self.visual.run_async()
            threading.Thread(target=self._startup_sequence, daemon=True).start()
        
        logger.info("[CS2] Запуск Game State сервера на порту 3000...")
        self.cs2_gsi.start()
        self.cs2_gsi.save_config_file()
        
        if self.voice_input:
            logger.info("[VOICE] Запуск голосового ввода...")
            self.voice_input.start()
        
        logger.info("=" * 60)
        logger.info("✅ IRIS успешно запущена!")
        logger.info("=" * 60)
        logger.info("📋 Функции:")
        logger.info("   🎮 CS2 Game State (порт 3000)")
        logger.info("   🤖 Ollama AI (локальная нейросеть)")
        logger.info("   🔊 Text-to-Speech")
        logger.info("   🎤 Voice Control (скажите 'Ирис')")
        logger.info("   👁️ IO-стиль визуализация")
        logger.info("=" * 60)
    
    def stop(self):
        """Остановка"""
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
        """Основной цикл"""
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
║        🌸 IRIS - AI Assistant                              ║
║        Локальная нейросеть + голос + визуализация         ║
║                                                            ║
║        💜 Технологии:                                      ║
║           • Ollama (Qwen3) - локальный AI                ║
║           • Edge TTS - синтез речи                        ║
║           • Vosk - распознавание речи                     ║
║           • Pygame - визуализация IO-стиль               ║
║                                                            ║
║        Для лучшей работы:                                 ║
║        • Запустите Ollama: ollama serve                  ║
║        • Модель готова: qwen3:4b-instructor              ║
║                                                            ║
╚════════════════════════════════════════════════════════════╝
    """)
    
    iris = IrisAssistant()
    iris.run()

if __name__ == "__main__":
    main()
