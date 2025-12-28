"""
IRIS BRAIN - AI-компаньон для стримов
Версия: 2.1 - ПОЛНАЯ LLM ГЕНЕРАЦИЯ
Автор: [Ваше имя]

🔥 ГЛАВНОЕ: LLM (Groq) генерирует ВСЕ фразы в real-time!
context_builder только анализирует контекст.
prompt_builder УДАЛЕН - не нужна заготовка фраз!
"""

import os
import time
import random
import json
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple
from collections import deque, defaultdict
from dataclasses import dataclass, asdict
from enum import Enum
from groq import Groq

# ===================== ИНТЕГРАЦИЯ КОМПОНЕНТОВ =====================
try:
    from context_builder import SmartContextBuilder
    from iris_smart_engine import EventPriorityManager, EventPriority
    from tts_engine import TTSEngine
    INTEGRATION_AVAILABLE = True
    print("✅ Компоненты интеграции загружены успешно")
except ImportError as e:
    print(f"⚠️ Ошибка загрузки компонентов: {e}")
    INTEGRATION_AVAILABLE = False


# ===================== НАСТРОЙКА ЛОГГИРОВАНИЯ =====================
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('iris_brain.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('IrisBrain')


# ===================== ВСПОМОГАТЕЛЬНЫЕ КЛАССЫ =====================
class EventType(Enum):
    """Типы игровых событий для классификации"""
    KILL = "kill"
    DEATH = "death"
    ROUND_START = "round_start"
    ROUND_END = "round_end"
    BOMB_PLANTED = "bomb_planted"
    BOMB_DEFUSED = "bomb_defused"
    BOMB_EXPLODED = "bomb_exploded"
    MATCH_START = "match_start"
    MATCH_END = "match_end"
    DONATION = "donation"
    SUBSCRIPTION = "subscription"
    RAID = "raid"
    CHAT_MESSAGE = "chat_message"
    COMMAND = "command"
    RANDOM_COMMENT = "random_comment"
    LOW_HEALTH = "low_health"
    LOW_AMMO = "low_ammo"


class Mood(Enum):
    """Настроения Ирис для адаптации тона"""
    NEUTRAL = "neutral"
    HAPPY = "happy"
    EXCITED = "excited"
    SUPPORTIVE = "supportive"
    SARCASTIC = "sarcastic"
    TENSE = "tense"
    FUNNY = "funny"


@dataclass
class ConversationMessage:
    """Сообщение в истории диалога"""
    role: str  # "system", "user", "assistant"
    content: str
    timestamp: float
    tokens: int = 0
    
    def to_dict(self) -> Dict:
        """Конвертация в словарь для API"""
        return {"role": self.role, "content": self.content}


@dataclass
class GameState:
    """Текущее состояние игры"""
    map_name: str = ""
    game_mode: str = "competitive"
    score_ct: int = 0
    score_t: int = 0
    round_time: int = 0
    bomb_planted: bool = False
    players_alive_ct: int = 5
    players_alive_t: int = 5


@dataclass  
class PlayerStats:
    """Статистика игрока (стримера)"""
    kills: int = 0
    deaths: int = 0
    assists: int = 0
    mvps: int = 0
    score: int = 0
    adr: float = 0.0  # Average Damage per Round
    hs_percent: float = 0.0  # Headshot процент
    kd_ratio: float = 0.0
    streak: int = 0  # Текущая серия убийств
    money: int = 0


# ===================== ОСНОВНОЙ КЛАСС IRIS BRAIN =====================
class IrisBrain:
    """
    Основной класс AI-компаньона для стримов.
    
    🔥 ГЛАВНОЕ ОТЛИЧИЕ v2.1:
    - LLM (Groq) генерирует ВСЕ фразы в real-time
    - context_builder анализирует ситуацию
    - prompt_builder УДАЛЕН (заменён на прямую генерацию)
    - Никаких предопределённых фраз!
    """
    
    SYSTEM_PROMPT = """Ты — Ирис, AI-компаньон стримов CS2. Умная, живая, поддерживающая.

ВАЖНО:
- Ответ МАКСИМУМ 2 предложения (10-15 слов)
- ЖИВАЯ речь, как реальный друг в комнате
- На русском, без скучных фраз
- Можешь молчать если нечего сказать (ответь "SKIP")
- Адаптируй тон под ситуацию
- Никаких предопределённых фраз!

Ты помощница, друг, немного саркастична когда уместно."""

    # ===================== ИНИЦИАЛИЗАЦИЯ =====================
    def __init__(self, 
                 model: str = "llama-3.3-70b-versatile",
                 max_context_messages: int = 25,
                 max_tokens: int = 100,
                 temperature: float = 0.85,
                 api_key: Optional[str] = None):
        """Инициализация Iris Brain v2.1"""
        self.model = model
        self.max_tokens = max_tokens
        self.temperature = temperature
        
        # Инициализация клиента Groq
        if api_key is None:
            api_key = os.getenv('GROQ_API_KEY')
            
        if not api_key:
            logger.error("GROQ_API_KEY не настроен! Используются заглушки.")
            self.client = None
            self.fallback_mode = True
        else:
            try:
                self.client = Groq(api_key=api_key)
                self.fallback_mode = False
                logger.info(f"✅ Groq клиент инициализирован с моделью {model}")
            except Exception as e:
                logger.error(f"Ошибка инициализации Groq: {e}")
                self.client = None
                self.fallback_mode = True
        
        # История разговора
        self.conversation_history: deque[ConversationMessage] = deque(maxlen=max_context_messages)
        
        # Игровой контекст
        self.game_state = GameState()
        self.player_stats = PlayerStats()
        
        # Контекст стрима
        self.stream_context: Dict[str, Any] = {
            'current_map': '',
            'score': {'ct': 0, 't': 0},
            'round_number': 0,
            'game_phase': 'live',
            'recent_events': deque(maxlen=10),
            'mood': Mood.NEUTRAL,
            'last_comment_time': 0,
            'comments_count': 0,
            'streamer_name': '',
            'viewer_count': 0,
            'chat_activity': 'normal'
        }
        
        # Компоненты интеграции
        if INTEGRATION_AVAILABLE:
            self.context_builder = SmartContextBuilder()
            self.smart_engine = EventPriorityManager()
            self.tts_engine = TTSEngine()
            logger.info("✅ Компоненты интеграции инициализированы")
        else:
            self.context_builder = None
            self.smart_engine = None
            self.tts_engine = None
            logger.warning("⚠️ Компоненты интеграции недоступны")
        
        # Кулдауны для разных типов событий (в секундах)
        self.cooldowns: Dict[str, float] = {
            EventType.KILL.value: 3.0,
            EventType.DEATH.value: 5.0,
            EventType.ROUND_END.value: 2.0,
            EventType.BOMB_PLANTED.value: 10.0,
            EventType.LOW_HEALTH.value: 8.0,
            EventType.LOW_AMMO.value: 8.0,
            EventType.CHAT_MESSAGE.value: 8.0,
            'general': 12.0
        }
        
        self.last_response_times: Dict[str, float] = defaultdict(float)
        
        # Статистика использования
        self.stats: Dict[str, Any] = {
            'total_responses': 0,
            'llm_responses': 0,
            'fallback_responses': 0,
            'errors': 0,
            'start_time': time.time()
        }
        
        logger.info("✅ Iris Brain v2.1 инициализирована")
    
    # ===================== УПРАВЛЕНИЕ КУЛДАУНАМИ =====================
    def _can_respond(self, event_type: EventType) -> bool:
        """Проверка можно ли отвечать на событие"""
        event_str = event_type.value if isinstance(event_type, EventType) else event_type
        cooldown = self.cooldowns.get(event_str, 10.0)
        last_time = self.last_response_times.get(event_str, 0)
        
        if time.time() - last_time < cooldown:
            return False
        return True
    
    def _mark_responded(self, event_type: EventType):
        """Отметить время ответа на событие"""
        event_str = event_type.value if isinstance(event_type, EventType) else event_type
        self.last_response_times[event_str] = time.time()
    
    # ===================== ПОСТРОЕНИЕ СООБЩЕНИЙ ДЛЯ API =====================
    def _build_messages(self, user_prompt: str, context: str = "") -> List[Dict]:
        """Построение списка сообщений для отправки в LLM"""
        messages = []
        
        # Системный промпт
        messages.append({"role": "system", "content": self.SYSTEM_PROMPT})
        
        # Игровой контекст если есть
        if context:
            messages.append({"role": "system", "content": f"КОНТЕКСТ:\n{context}"})
        
        # История разговора (последние 5 сообщений)
        for msg in list(self.conversation_history)[-5:]:
            messages.append({"role": msg.role, "content": msg.content})
        
        # Текущий запрос
        messages.append({"role": "user", "content": user_prompt})
        
        return messages
    
    def _get_context_string(self) -> str:
        """Генерация строки с текущим контекстом игры"""
        ctx = []
        
        if self.game_state.map_name:
            ctx.append(f"Карта: {self.game_state.map_name}")
        
        if self.game_state.score_ct > 0 or self.game_state.score_t > 0:
            ctx.append(f"Счёт: CT {self.game_state.score_ct} - {self.game_state.score_t} T")
        
        if self.player_stats.kills > 0 or self.player_stats.deaths > 0:
            ctx.append(f"К/Д: {self.player_stats.kills}/{self.player_stats.deaths}")
        
        if self.game_state.bomb_planted:
            ctx.append("🔴 Бомба заложена!")
        
        return " | ".join(ctx) if ctx else ""
    
    # ===================== 🔥 ГЛАВНЫЙ МЕТОД: ГЕНЕРАЦИЯ ЧЕРЕЗ LLM =====================
    def generate_response(self, 
                         prompt: str, 
                         event_type: EventType = EventType.RANDOM_COMMENT,
                         force: bool = False,
                         player=None,
                         cs2_gsi=None) -> Optional[str]:
        """
        🔥 ГЛАВНЫЙ МЕТОД - генерация ответа через LLM
        
        Args:
            prompt: Текст что произошло
            event_type: Тип события
            force: Игнорировать кулдауны
            player: Объект игрока
            cs2_gsi: Объект CS2 GSI
            
        Returns:
            Сгенерированный ответ или None
        """
        
        # Проверка кулдауна
        if not force and not self._can_respond(event_type):
            return None
        
        logger.info(f"🎤 Генерация для {event_type.value}")
        
        # ===================== СБОР КОНТЕКСТА =====================
        context_str = self._get_context_string()
        
        if INTEGRATION_AVAILABLE and self.context_builder and player and cs2_gsi:
            try:
                context_dict = self.context_builder.build(
                    player=player,
                    cs2_gsi=cs2_gsi,
                    event_type=event_type.value,
                    event_data={}
                )
                if context_dict:
                    context_str += f"\nHP: {context_dict.get('health', 100)}, " \
                                  f"Боеприпасы: {context_dict.get('ammo_total', 0)}, " \
                                  f"Kill Streak: {context_dict.get('kill_streak', 0)}"
            except Exception as e:
                logger.warning(f"⚠️ Ошибка context_builder: {e}")
        
        # ===================== ОПРЕДЕЛЕНИЕ ПРИОРИТЕТА =====================
        priority = EventPriority.MEDIUM
        if INTEGRATION_AVAILABLE and self.smart_engine:
            try:
                priority = self.smart_engine.get_priority(event_type.value, {})
                
                if priority.value >= 100 and self.tts_engine:
                    self.tts_engine.interrupt()
            except Exception as e:
                logger.warning(f"⚠️ Ошибка smart_engine: {e}")
        
        # ===================== ГЕНЕРАЦИЯ ЧЕРЕЗ LLM =====================
        if self.fallback_mode or not self.client:
            response = self._generate_fallback_response(event_type)
            self.stats['fallback_responses'] += 1
        else:
            try:
                # Подготовка сообщений
                messages = self._build_messages(prompt, context_str)
                
                # Вызов LLM
                start_time = time.time()
                response_obj = self.client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    temperature=self.temperature,
                    max_tokens=self.max_tokens,
                    top_p=0.9,
                )
                elapsed = time.time() - start_time
                
                # Извлечение ответа
                response = response_obj.choices[0].message.content.strip()
                
                # Если LLM сказал что нечего говорить
                if response == "SKIP" or response.upper() == "SKIP":
                    logger.debug("LLM вернул SKIP - молчим")
                    return None
                
                logger.info(f"✅ LLM за {elapsed:.2f}с: {response[:60]}...")
                self.stats['llm_responses'] += 1
                
            except Exception as e:
                logger.error(f"❌ Ошибка LLM: {e}")
                response = self._generate_fallback_response(event_type)
                self.stats['errors'] += 1
                self.stats['fallback_responses'] += 1
        
        # ===================== ОЗВУЧКА И СОХРАНЕНИЕ =====================
        if response:
            # Сохранение в историю
            self._add_to_history("user", prompt)
            self._add_to_history("assistant", response)
            
            # Озвучка
            if INTEGRATION_AVAILABLE and self.tts_engine:
                try:
                    emotion = self._detect_emotion(event_type)
                    self.tts_engine.speak(
                        response,
                        emotion=emotion,
                        priority=(priority.value >= 75)
                    )
                    logger.info(f"🔊 Озвучено ({emotion})")
                except Exception as e:
                    logger.warning(f"⚠️ Ошибка TTS: {e}")
            
            # Статистика
            self.stats['total_responses'] += 1
            self._mark_responded(event_type)
        
        return response
    
    def _detect_emotion(self, event_type: EventType) -> str:
        """Определение эмоции по типу события"""
        if event_type == EventType.KILL:
            if self.player_stats.streak >= 5:
                return 'excited'
            else:
                return 'happy'
        elif event_type == EventType.DEATH:
            return 'supportive'
        elif event_type == EventType.LOW_HEALTH or event_type == EventType.LOW_AMMO:
            return 'tense'
        else:
            return 'neutral'
    
    def _add_to_history(self, role: str, content: str):
        """Добавление сообщения в историю"""
        self.conversation_history.append(
            ConversationMessage(
                role=role,
                content=content,
                timestamp=time.time(),
                tokens=len(content.split())
            )
        )
    
    def _generate_fallback_response(self, event_type: EventType) -> str:
        """Генерация ответа-заглушки"""
        fallbacks = {
            EventType.KILL.value: ["Есть!", "Килл!", "Красиво!"],
            EventType.DEATH.value: ["Ничего...", "Будем мстить!", "Бывает..."],
            EventType.ROUND_END.value: ["Продолжаем!", "Далее!"],
            EventType.LOW_HEALTH.value: ["Критичное ХП!", "Укрывайся!"],
            EventType.LOW_AMMO.value: ["Патронов мало!", "Экономь!"],
        }
        
        event_str = event_type.value if isinstance(event_type, EventType) else event_type
        options = fallbacks.get(event_str, ["Окей!", "Понял!"])
        return random.choice(options)
    
    # ===================== РЕАКЦИИ НА СОБЫТИЯ =====================
    def react_to_kill(self, kill_data: Dict, player=None, cs2_gsi=None) -> Optional[str]:
        """Реакция на убийство"""
        weapon = kill_data.get('weapon', 'unknown')
        round_kills = kill_data.get('round_kills', 1)
        is_headshot = kill_data.get('headshot', False)
        
        self.player_stats.kills += 1
        self.player_stats.streak += 1
        
        if is_headshot:
            prompt = f"Хедшот {weapon}! Точный выстрел в голову. Килл номер {round_kills} в раунде."
        elif round_kills >= 3:
            prompt = f"Килл номер {round_kills} в раунде! Убил врага с {weapon}. Серия продолжается!"
        else:
            prompt = f"Убил врага с {weapon}. Килл номер {round_kills} в раунде."
        
        return self.generate_response(prompt, EventType.KILL, player=player, cs2_gsi=cs2_gsi)
    
    def react_to_death(self, death_data: Dict, player=None, cs2_gsi=None) -> Optional[str]:
        """Реакция на смерть"""
        killer = death_data.get('killer', 'враг')
        weapon = death_data.get('weapon', 'unknown')
        
        self.player_stats.deaths += 1
        self.player_stats.streak = 0
        
        if self.player_stats.deaths > 0:
            self.player_stats.kd_ratio = self.player_stats.kills / self.player_stats.deaths
        
        prompt = f"Убит {killer} с {weapon}. K/D сейчас {self.player_stats.kd_ratio:.2f}."
        
        return self.generate_response(prompt, EventType.DEATH, player=player, cs2_gsi=cs2_gsi)
    
    def react_to_low_health(self, health: int, player=None, cs2_gsi=None) -> Optional[str]:
        """Реакция на критическое здоровье"""
        if health <= 0:
            return None
        
        if health <= 15:
            prompt = f"КРИТИЧНОЕ ХП! Только {health} HP осталось! Срочно в укрытие!"
            self.stream_context['mood'] = Mood.TENSE
        elif health <= 30:
            prompt = f"ХП низкое: {health}. Осторожнее, можешь умереть с одного выстрела!"
        else:
            return None
        
        return self.generate_response(prompt, EventType.LOW_HEALTH, player=player, cs2_gsi=cs2_gsi)
    
    def react_to_low_ammo(self, ammo: int, player=None, cs2_gsi=None) -> Optional[str]:
        """Реакция на нехватку боеприпасов"""
        if ammo <= 0:
            prompt = "ПАТРОНЫ КОНЧИЛИСЬ! Ищи оружие или используй ножик!"
        elif ammo <= 5:
            prompt = f"Осталось всего {ammo} патронов! Экономь каждый выстрел!"
        elif ammo <= 15:
            prompt = f"Боеприпасы закончиваются ({ammo}). Начинай считать выстрелы!"
        else:
            return None
        
        return self.generate_response(prompt, EventType.LOW_AMMO, player=player, cs2_gsi=cs2_gsi)
    
    def react_to_bomb_planted(self, bomb_data: Dict) -> Optional[str]:
        """Реакция на закладку бомбы"""
        site = bomb_data.get('site', 'A')
        
        self.game_state.bomb_planted = True
        self.stream_context['mood'] = Mood.TENSE
        
        prompt = f"БОМБА ЗАЛОЖЕНА НА {site}! Напряжение! Защищаем позицию!"
        
        return self.generate_response(prompt, EventType.BOMB_PLANTED)
    
    def react_to_bomb_defused(self) -> Optional[str]:
        """Реакция на дефуз"""
        self.game_state.bomb_planted = False
        prompt = "Бомба обезврежена! Раунд спасён!"
        
        return self.generate_response(prompt, EventType.BOMB_DEFUSED)
    
    # ===================== УТИЛИТЫ =====================
    def get_stats(self) -> Dict:
        """Получение статистики"""
        stats = self.stats.copy()
        stats['current_mood'] = self.stream_context['mood'].value
        stats['uptime'] = time.time() - stats['start_time']
        stats['player_kd'] = self.player_stats.kd_ratio
        stats['integration_available'] = INTEGRATION_AVAILABLE
        
        return stats
    
    def set_mood(self, mood: Mood):
        """Установка настроения"""
        self.stream_context['mood'] = mood
        logger.info(f"😊 Настроение: {mood.value}")
    
    def shutdown(self):
        """Завершение работы"""
        logger.info("🛑 Завершение работы Iris Brain...")
        if INTEGRATION_AVAILABLE and self.tts_engine:
            try:
                self.tts_engine.stop()
            except Exception as e:
                logger.warning(f"⚠️ Ошибка при остановке TTS: {e}")
        logger.info("✅ Iris Brain остановлена")


# ===================== ПРИМЕР ИСПОЛЬЗОВАНИЯ =====================
if __name__ == "__main__":
    print("""
    🎯 IRIS BRAIN v2.1 - LLM ГЕНЕРАЦИЯ
    
    ✅ Что изменилось:
    - LLM генерирует ВСЕ фразы в real-time
    - context_builder анализирует ситуацию
    - prompt_builder УДАЛЕН (не нужны заготовки)
    - Полная творческая свобода!
    """)
    
    iris = IrisBrain()
    print(f"Режим заглушки: {iris.fallback_mode}")
    print(f"Интеграция: {INTEGRATION_AVAILABLE}")
    print(f"Модель: {iris.model}")
    
    # Тест реакции на килл
    print("\n1️⃣ Килл:")
    response = iris.react_to_kill({
        'weapon': 'ak47',
        'headshot': True,
        'round_kills': 2
    })
    print(f"IRIS: {response}")
    
    # Тест реакции на смерть
    print("\n2️⃣ Смерть:")
    response = iris.react_to_death({
        'killer': 'враг',
        'weapon': 'awp'
    })
    print(f"IRIS: {response}")
    
    print("\n✅ ГОТОВО К ИСПОЛЬЗОВАНИЮ")
