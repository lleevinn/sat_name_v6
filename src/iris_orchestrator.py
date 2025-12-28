"""
🌟 IRIS ORCHESTRATOR v1.0 - ОКЕСТРАТОР ВСЕХ КОМПОНЕНТОВ

Главный класс для организации работы всех слоёв IRIS:
- Данные: context_builder
- Логика: prompt_builder, iris_smart_engine
- Мозг: iris_brain (ВЮГИ в НЕМ уже ИНТЕГРИРОВАННЫ)
- Голос: tts_engine, iris_voice_engine

Полный цикл обработки события:
CS2 EVENT → context → priority → prompt → LLM → emotion → TTS → SPEECH
"""

import logging
import time
from typing import Dict, Optional, Any
from enum import Enum

try:
    from iris_brain import IrisBrain, EventType, Mood
    from iris_voice_engine import IrisVoiceEngine
    from context_builder import SmartContextBuilder
    from prompt_builder import SmartPromptBuilder
    from iris_smart_engine import EventPriorityManager, EventPriority
    from tts_engine import TTSEngine
    FULL_INTEGRATION = True
except ImportError as e:
    print(f"⚠️ Некоторые модули недоступны: {e}")
    FULL_INTEGRATION = False

# ===================== ЛОГГИРОВАНИЕ =====================
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - ORCHESTRATOR - %(levelname)s - %(message)s'
)
logger = logging.getLogger('IrisOrchestrator')


# ===================== МОДЕЛи СОБЫТИЙ =====================
class EventSource(Enum):
    """Источники событий"""
    CS2_GAME = "cs2"        # Игровые события
    STREAM_CHAT = "chat"    # События чата
    DONATIONS = "donation"  # Донаты
    VOICE = "voice"         # Пользовательские голосовые команды


# ===================== ГЛАВНЫЙ ОКЕСТРАТОР =====================
class IrisOrchestrator:
    """
    Окестратор всех компонентов IRIS
    
    Ответственности:
    1. Принимать события из CS2 GSI
    2. Организовать последовательные вызовы компонентов
    3. Обрабатывать события до говорения
    4. Отправлять в TTS для озвучивания
    """
    
    def __init__(self):
        """Инициализация всех компонентов"""
        
        logger.info("🌟 НИНИЦИАЛИЗАЦИЯ ОКЕСТРАТОРА")
        
        # Основные компоненты
        self.brain = IrisBrain()  # iris_brain имеет поддержку компонентов
        self.voice_engine = IrisVoiceEngine()
        
        # Компоненты интеграции (для поддержки)
        self.context_builder = SmartContextBuilder()
        self.prompt_builder = SmartPromptBuilder()
        self.smart_engine = EventPriorityManager()
        self.tts_engine = self.brain.tts_engine  # Используем из brain
        
        # График событий
        self.event_log = []
        self.processing = False
        
        logger.info("✅ Окестратор готов к работе!")
    
    # ===================== ОБРАБОТКА СОБЫТИЙ =====================
    def on_cs2_event(self, event_type: str, event_data: Dict, player=None, cs2_gsi=None) -> Optional[str]:
        """
        Обработка события из CS2
        
        Пополненный цикл:
        1. Собрать контекст с context_builder
        2. Определить приоритет с iris_smart_engine
        3. Построить промпт с prompt_builder
        4. Обработать в LLM через iris_brain
        5. Озвучить через tts_engine
        
        Args:
            event_type: Тип события (kill, death, damage, round_end, bomb_planted...)
            event_data: Данные события
            player: Объект игрока
            cs2_gsi: Объект CS2 GSI
        
        Returns:
            Ответ IRIS или None
        """
        
        if self.processing:
            logger.debug("🚫 Обработка занята, пропускаем")
            return None
        
        self.processing = True
        start_time = time.time()
        
        try:
            logger.info(f"📄 Событие: {event_type}")
            
            # Передать в iris_brain для генерации ответа
            # iris_brain внутренне использует компоненты интеграции
            if event_type == 'kill':
                response = self.brain.react_to_kill(event_data, player=player, cs2_gsi=cs2_gsi)
            elif event_type == 'death':
                response = self.brain.react_to_death(event_data, player=player, cs2_gsi=cs2_gsi)
            elif event_type == 'damage' or event_type == 'low_health':
                health = event_data.get('health', 100)
                response = self.brain.react_to_low_health(int(health), player=player, cs2_gsi=cs2_gsi)
            elif event_type == 'round_end':
                response = self.brain.react_to_round_end(event_data)
            elif event_type == 'bomb_planted':
                response = self.brain.react_to_bomb_event('plant', event_data)
            elif event_type == 'bomb_defused':
                response = self.brain.react_to_bomb_event('defuse', event_data)
            elif event_type == 'bomb_exploded':
                response = self.brain.react_to_bomb_event('explode', event_data)
            else:
                # Общая обработка
                prompt = f"Событие: {event_type}"
                response = self.brain.generate_response(prompt, force=True)
            
            # ЛОГИРОВАНие
            elapsed = time.time() - start_time
            logger.info(f"✅ Ответ за {elapsed:.3f}с: {response[:50] if response else 'None'}...")
            
            # СОХРАНять в лог
            self.event_log.append({
                'type': event_type,
                'response': response,
                'time': elapsed,
                'timestamp': time.time()
            })
            
            return response
        
        except Exception as e:
            logger.error(f"💥 Критическая ошибка: {e}", exc_info=True)
            return None
        
        finally:
            self.processing = False
    
    # ===================== НОРМаЛиЗАЦИЯ МОдели =====================
    def set_mood(self, mood: str):
        """Установить настроение"""
        try:
            mood_enum = Mood[mood.upper()]
            self.brain.set_mood(mood_enum)
            logger.info(f"😊 Настроение: {mood}")
        except KeyError:
            logger.error(f"Неизвестное настроение: {mood}")
    
    def get_stats(self) -> Dict:
        """Получить статистику"""
        stats = self.brain.get_stats()
        stats['event_log_size'] = len(self.event_log)
        stats['recent_events'] = self.event_log[-5:] if self.event_log else []
        return stats
    
    def shutdown(self):
        """Корректно остановить систему"""
        logger.info("🛑 Остановка окестратора...")
        
        try:
            self.brain.shutdown()
        except Exception as e:
            logger.error(f"Ошибка при остановке brain: {e}")
        
        logger.info("✅ Окестратор остановлен")


# ===================== ПОВЕРАМЫ ИСПОЛЬЗОВАНИЯ =====================
if __name__ == "__main__":
    print("""
    🌟 IRIS ORCHESTRATOR v1.0
    Окестратор всех компонентов IRIS
    
    🔗 Основа - iris_brain (уже интегрирован с):
    - context_builder (данные)
    - prompt_builder (логика)
    - iris_smart_engine (приоритеты)
    - tts_engine (эмоциональный голос)
    """)
    
    # Нициализировать
    orchestrator = IrisOrchestrator()
    
    # Тест CS2 события
    print("\n1️⃣ Тест события kill:")
    response = orchestrator.on_cs2_event(
        'kill',
        {
            'weapon': 'ak47',
            'headshot': True,
            'round_kills': 3,
            'kill_streak': 5
        }
    )
    print(f"Ответ: {response}\n")
    
    # Тест death
    print("2️⃣ Тест события death:")
    response = orchestrator.on_cs2_event('death', {'killer': 'противник'})
    print(f"Ответ: {response}\n")
    
    # Статистика
    print("3️⃣ Статистика:")
    stats = orchestrator.get_stats()
    print(f"Всего ответов: {stats['total_responses']}")
    print(f"Настроение: {stats['current_mood']}")
    
    # Остановка
    orchestrator.shutdown()
    
    print("\n🌸 Окестратор потестирован!")
