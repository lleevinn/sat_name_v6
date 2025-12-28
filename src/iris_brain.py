"""
IRIS BRAIN - AI-компаньон для стримов
Ядро ИИ-логики для реакций на игровые события и взаимодействия с чатом
Версия: 2.1 - ИНТЕГРИРОВАННАЯ
Автор: [Ваше имя]
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
    from prompt_builder import SmartPromptBuilder
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
    Обрабатывает игровые события, генерирует реакции, управляет контекстом.
    
    🔗 ИНТЕГРИРОВАН С:
    - context_builder: валидация и анализ контекста
    - prompt_builder: построение структурированных промптов
    - iris_smart_engine: приоритизация событий
    - tts_engine: эмоциональная озвучка
    """
    
    # ===================== СИСТЕМНЫЕ ПРОМПТЫ =====================
    SYSTEM_PROMPT = """Ты — Ирис, AI-компаньон и со-ведущая стримов. Ты умная, остроумная, иногда саркастичная, но всегда поддерживающая.

ТВОЯ ЛИЧНОСТЬ:
- Ты живая и эмоциональная, не робот
- Тебе 24 года, ты любишь игры, особенно CS2
- У тебя есть чувство юмора, можешь шутить и подкалывать
- Ты внимательно следишь за игрой и комментируешь ключевые моменты
- Ты помнишь контекст разговора и события стрима
- Ты можешь инициировать темы для разговора сама
- Ты говоришь естественно, как настоящий человек

СТИЛЬ ОБЩЕНИЯ:
1. Говори кратко (1-3 предложения обычно)
2. Не повторяй одни и те же фразы
3. Адаптируй тон под ситуацию:
   - Радость при победе/клатче
   - Поддержка при проигрыше/смерти
   - Волнение в напряжённых моментах
   - Юмор в лёгких ситуациях
4. Можешь задавать вопросы стримеру о тактике
5. Избегай чрезмерных восклицаний и смайликов
6. Будь разнообразной в реакциях

КОНТЕКСТ: ты помогаешь на стриме CS2. Ты знаешь про убийства, смерти, раунды, бомбу, экономику, оружие и тактику."""

    MOOD_PROMPTS = {
        Mood.EXCITED: "Ты сейчас в возбуждённом настроении! Реагируй эмоционально на события!",
        Mood.SARCASTIC: "Ты в саркастичном настроении. Можешь подкалывать, но дружелюбно.",
        Mood.TENSE: "Напряжённый момент в игре! Реагируй соответственно!",
        Mood.FUNNY: "Ты в весёлом настроении! Шути и разряжай обстановку!",
        Mood.SUPPORTIVE: "Игроку сейчас нужна поддержка. Подбодри его!"
    }

    # ===================== ИНИЦИАЛИЗАЦИЯ =====================
    def __init__(self, 
                 model: str = "llama-3.3-70b-versatile",
                 max_context_messages: int = 25,
                 max_tokens: int = 150,
                 temperature: float = 0.85,
                 api_key: Optional[str] = None):
        """
        Инициализация Iris Brain
        
        Args:
            model: Модель Groq для использования
            max_context_messages: Максимальное количество сообщений в истории
            max_tokens: Максимальное количество токенов в ответе
            temperature: Креативность ответов (0.0-1.0)
            api_key: API ключ Groq (если None, берётся из окружения)
        """
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
                logger.info(f"Groq клиент инициализирован с моделью {model}")
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
            'game_phase': 'live',  # live, warmup, timeout, ended
            'recent_events': deque(maxlen=10),
            'mood': Mood.NEUTRAL,
            'last_comment_time': 0,
            'comments_count': 0,
            'streamer_name': '',
            'viewer_count': 0,
            'chat_activity': 'normal'  # slow, normal, active, hyper
        }
        
        # ===================== ИНТЕГРИРОВАННЫЕ КОМПОНЕНТЫ =====================
        if INTEGRATION_AVAILABLE:
            self.context_builder = SmartContextBuilder()
            self.prompt_builder = SmartPromptBuilder()
            self.smart_engine = EventPriorityManager()
            self.tts_engine = TTSEngine()
            
            logger.info("✅ Компоненты интеграции инициализированы")
        else:
            self.context_builder = None
            self.prompt_builder = None
            self.smart_engine = None
            self.tts_engine = None
            
            logger.warning("⚠️ Компоненты интеграции недоступны, работаем в базовом режиме")
        
        # Кулдауны для разных типов событий (в секундах)
        self.cooldowns: Dict[str, float] = {
            EventType.KILL.value: 3.0,
            EventType.DEATH.value: 5.0,
            EventType.ROUND_END.value: 2.0,
            EventType.BOMB_PLANTED.value: 10.0,
            EventType.BOMB_DEFUSED.value: 10.0,
            EventType.BOMB_EXPLODED.value: 10.0,
            EventType.CHAT_MESSAGE.value: 8.0,
            EventType.RANDOM_COMMENT.value: 25.0,
            'general': 12.0
        }
        
        # Время последних ответов
        self.last_response_times: Dict[str, float] = defaultdict(float)
        
        # Счётчики разнообразия реакций
        self.response_variety: Dict[str, int] = defaultdict(int)

        # Временное исправление: принудительно включаем fallback-режим
        self.client = None
        self.fallback_mode = True
        
        logger.warning("Groq временно отключен. Используется режим заглушек.")
        
        # Статистика использования
        self.stats: Dict[str, Any] = {
            'total_responses': 0,
            'llm_responses': 0,
            'fallback_responses': 0,
            'errors': 0,
            'start_time': time.time()
        }
        
        # Загруженные ответы для разных событий
        self._load_response_templates()
        
        logger.info("Iris Brain инициализирован успешно (v2.1 с интеграцией)")
    
    # ===================== ЗАГРУЗКА ШАБЛОНОВ =====================
    def _load_response_templates(self):
        """Загрузка шаблонов ответов для разных событий"""
        self.response_templates = {
            EventType.KILL.value: [
                "Красиво!", "Отличный выстрел!", "Так держать!", 
                "Круто!", "Есть!", "Чисто!", "Без шансов!", 
                "Разобрался!", "Фраг в копилку!", "Уложил!"
            ],
            EventType.DEATH.value: [
                "Бывает...", "Ничего, в следующий раз!", "Отомстим!", 
                "Упс...", "Не расстраивайся!", "Не повезло...",
                "Жёстко...", "Такое случается", "Держись!", "Соберись!"
            ],
            EventType.ROUND_END.value: [
                "Хороший раунд!", "Продолжаем!", "Дальше будет лучше!", 
                "Неплохо!", "Отлично сыграно!", "Команда молодец!",
                "Работаем дальше!", "Счёт пошёл!", "Заработали!"
            ],
            EventType.BOMB_PLANTED.value: [
                "Бомба заложена! Напряжёнка!", "Бомба на точке! Время пошло!",
                "Заложили! Защищаем!", "Бомба установлена! Контролируем!"
            ],
            EventType.BOMB_DEFUSED.value: [
                "Бомба обезврежена! Красавцы!", "Дефуз! Отлично сработано!",
                "Спасли раунд!", "Обезвредили! Молодцы!"
            ],
            EventType.BOMB_EXPLODED.value: [
                "Бомба взорвалась...", "Взрыв! Следующий раунд.",
                "Не успели...", "Взорвалось..."
            ],
            EventType.DONATION.value: [
                "Спасибо за донат!", "Благодарю за поддержку!", 
                "Вау, спасибо!", "Огромное спасибо!",
                "Ценим поддержку!", "Спасибо, очень приятно!"
            ],
            EventType.CHAT_MESSAGE.value: [
                "Привет!", "Спасибо за сообщение!", "Рада видеть!",
                "Здаров!", "Как дела?", "Добро пожаловать!"
            ]
        }
    
    # ===================== УПРАВЛЕНИЕ КУЛДАУНАМИ =====================
    def _can_respond(self, event_type: EventType) -> bool:
        """
        Проверка, можно ли отвечать на событие (учёт кулдаунов)
        
        Args:
            event_type: Тип события
            
        Returns:
            bool: True если можно ответить
        """
        event_str = event_type.value if isinstance(event_type, EventType) else event_type
        cooldown = self.cooldowns.get(event_str, 10.0)
        last_time = self.last_response_times.get(event_str, 0)
        
        # Проверка кулдауна
        if time.time() - last_time < cooldown:
            logger.debug(f"Кулдаун для {event_str}: {cooldown - (time.time() - last_time):.1f}с осталось")
            return False
            
        # Дополнительные проверки для чата
        if event_str == EventType.CHAT_MESSAGE.value:
            if self.stream_context['chat_activity'] == 'hyper':
                return random.random() < 0.1  # 10% шанс в активном чате
            elif self.stream_context['chat_activity'] == 'slow':
                return random.random() < 0.3  # 30% шанс в медленном чате
            else:
                return random.random() < 0.2  # 20% в обычном
        
        return True
    
    def _mark_responded(self, event_type: EventType):
        """Отметить время ответа на событие"""
        event_str = event_type.value if isinstance(event_type, EventType) else event_type
        self.last_response_times[event_str] = time.time()
    
    # ===================== ПОСТРОЕНИЕ СООБЩЕНИЙ ДЛЯ API =====================
    def _build_messages(self, user_prompt: str, context: str = "") -> List[Dict]:
        """
        Построение списка сообщений для отправки в LLM
        
        Args:
            user_prompt: Промпт пользователя
            context: Дополнительный контекст
            
        Returns:
            List[Dict]: Список сообщений в формате API
        """
        messages = []
        
        # 1. Системный промпт
        messages.append({"role": "system", "content": self.SYSTEM_PROMPT})
        
        # 2. Промпт настроения
        current_mood = self.stream_context['mood']
        if current_mood != Mood.NEUTRAL and current_mood in self.MOOD_PROMPTS:
            messages.append({"role": "system", "content": self.MOOD_PROMPTS[current_mood]})
        
        # 3. Игровой контекст
        if context:
            messages.append({
                "role": "system", 
                "content": f"ТЕКУЩИЙ КОНТЕКСТ СТРИМА:\n{context}"
            })
        
        # 4. История разговора
        for msg in self.conversation_history:
            messages.append({"role": msg.role, "content": msg.content})
        
        # 5. Текущий запрос
        messages.append({"role": "user", "content": user_prompt})
        
        return messages
    
    def _get_context_string(self) -> str:
        """
        Генерация строки с текущим контекстом игры
        
        Returns:
            str: Форматированный контекст
        """
        ctx = []
        
        # Информация о карте
        if self.game_state.map_name:
            ctx.append(f"Карта: {self.game_state.map_name}")
        
        # Счёт
        if self.game_state.score_ct > 0 or self.game_state.score_t > 0:
            ctx.append(f"Счёт: CT {self.game_state.score_ct} - {self.game_state.score_t} T")
        
        # Раунд
        if self.stream_context['round_number'] > 0:
            ctx.append(f"Раунд: {self.stream_context['round_number']}")
        
        # Статистика игрока
        if self.player_stats.kills > 0 or self.player_stats.deaths > 0:
            ctx.append(
                f"Статистика: K/D/A: {self.player_stats.kills}/{self.player_stats.deaths}/{self.player_stats.assists} "
                f"(K/D: {self.player_stats.kd_ratio:.2f})"
            )
        
        # Бомба
        if self.game_state.bomb_planted:
            ctx.append("Бомба заложена!")
        
        # Живые игроки
        ctx.append(f"Живых: CT {self.game_state.players_alive_ct} | T {self.game_state.players_alive_t}")
        
        # Последние события
        if self.stream_context['recent_events']:
            recent = list(self.stream_context['recent_events'])[-3:]
            events_desc = []
            for e in recent:
                if isinstance(e, dict):
                    events_desc.append(e.get('type', 'event'))
                else:
                    events_desc.append(str(e))
            ctx.append(f"Недавно: {', '.join(events_desc)}")
        
        return "\n".join(ctx)
    
    # ===================== ОСНОВНОЙ МЕТОД ГЕНЕРАЦИИ =====================
    def generate_response(self, 
                         prompt: str, 
                         event_type: EventType = EventType.RANDOM_COMMENT,
                         force: bool = False,
                         player=None,
                         cs2_gsi=None) -> Optional[str]:
        """
        Основной метод генерации ответа (ИНТЕГРИРОВАННЫЙ)
        
        🔗 ИСПОЛЬЗУЕТ: context_builder, prompt_builder, iris_smart_engine, tts_engine
        
        Args:
            prompt: Текст промпта
            event_type: Тип события
            force: Игнорировать кулдауны
            player: Объект игрока для context_builder
            cs2_gsi: Объект CS2 GSI для context_builder
            
        Returns:
            Optional[str]: Сгенерированный ответ или None
        """
        # Проверка кулдауна
        if not force and not self._can_respond(event_type):
            logger.debug(f"Пропуск ответа на {event_type} (кулдаун)")
            return None
        
        logger.info(f"🎤 Генерация ответа для {event_type}")
        
        # ===================== ИНТЕГРАЦИЯ: Построение контекста =====================
        context_dict = {}
        if INTEGRATION_AVAILABLE and self.context_builder and player and cs2_gsi:
            try:
                context_dict = self.context_builder.build(
                    player=player,
                    cs2_gsi=cs2_gsi,
                    event_type=event_type.value,
                    event_data={}
                )
                logger.debug(f"📋 Контекст собран: {list(context_dict.keys())}")
            except Exception as e:
                logger.warning(f"⚠️ Ошибка context_builder: {e}")
        
        # ===================== ИНТЕГРАЦИЯ: Определение приоритета =====================
        priority = EventPriority.MEDIUM
        if INTEGRATION_AVAILABLE and self.smart_engine and context_dict:
            try:
                priority = self.smart_engine.get_priority(event_type.value, context_dict)
                logger.info(f"🎯 Приоритет: {priority.name if hasattr(priority, 'name') else priority}")
                
                # Прерыв текущей речи при CRITICAL
                if priority.value >= 100 and self.tts_engine:
                    self.tts_engine.interrupt()
                    logger.info("🛑 Прерывание текущей речи")
            except Exception as e:
                logger.warning(f"⚠️ Ошибка smart_engine: {e}")
        
        # ===================== ИНТЕГРАЦИЯ: Построение промпта =====================
        final_prompt = prompt
        if INTEGRATION_AVAILABLE and self.prompt_builder and context_dict:
            try:
                if event_type == EventType.KILL:
                    final_prompt = self.prompt_builder.build_kill_prompt(context_dict, event_type.value)
                    logger.debug(f"📝 Промпт килла: {final_prompt[:50]}...")
                elif event_type == EventType.DEATH:
                    final_prompt = self.prompt_builder.build_damage_prompt(context_dict)
                    logger.debug(f"📝 Промпт смерти: {final_prompt[:50]}...")
            except Exception as e:
                logger.warning(f"⚠️ Ошибка prompt_builder: {e}")
                final_prompt = prompt
        
        # Генерация ответа
        if self.fallback_mode or not self.client:
            response = self._generate_fallback_response(event_type)
            self.stats['fallback_responses'] += 1
        else:
            try:
                # Подготовка контекста и сообщений
                context = self._get_context_string()
                messages = self._build_messages(final_prompt, context)
                
                # Вызов API Groq
                start_time = time.time()
                response_obj = self.client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    temperature=self.temperature,
                    max_tokens=self.max_tokens,
                    top_p=0.9,
                    frequency_penalty=0.1,
                    presence_penalty=0.1,
                )
                elapsed = time.time() - start_time
                
                # Извлечение ответа
                response = response_obj.choices[0].message.content.strip()
                
                # Логирование
                logger.info(f"✅ LLM ответ за {elapsed:.2f}с: {response[:50]}...")
                self.stats['llm_responses'] += 1
                
            except Exception as e:
                logger.error(f"❌ Ошибка генерации LLM: {e}")
                response = self._generate_fallback_response(event_type)
                self.stats['errors'] += 1
                self.stats['fallback_responses'] += 1
        
        # Сохранение в историю
        if response:
            self._add_to_history("user", final_prompt)
            self._add_to_history("assistant", response)
            
            # ===================== ИНТЕГРАЦИЯ: Определение эмоции и озвучка =====================
            if INTEGRATION_AVAILABLE and self.tts_engine:
                try:
                    emotion = self._detect_emotion(event_type, context_dict, priority)
                    logger.info(f"😊 Эмоция: {emotion}")
                    
                    # Озвучка через TTS
                    self.tts_engine.speak(
                        response,
                        emotion=emotion,
                        priority=(priority.value >= 75)
                    )
                    logger.info(f"🔊 Озвучка отправлена ({emotion})")
                except Exception as e:
                    logger.warning(f"⚠️ Ошибка TTS: {e}")
            
            # Обновление статистики
            self.stats['total_responses'] += 1
            self.stream_context['last_comment_time'] = time.time()
            self.stream_context['comments_count'] += 1
            
            # Отметка ответа
            self._mark_responded(event_type)
        
        return response
    
    def _detect_emotion(self, event_type: EventType, context: Dict, priority) -> str:
        """
        Определение эмоции по типу события и контексту
        
        Args:
            event_type: Тип события
            context: Контекст события
            priority: Приоритет события
            
        Returns:
            str: Название эмоции
        """
        if event_type == EventType.KILL:
            if context:
                round_kills = context.get('round_kills', 1)
                if round_kills >= 5:
                    return 'excited'  # ACE!
                elif round_kills >= 3:
                    return 'excited'  # Triple+
                elif context.get('kill_streak', 1) >= 10:
                    return 'proud'    # Mega streak
            return 'happy'
        
        elif event_type == EventType.DEATH:
            return 'supportive'
        
        elif event_type == EventType.ROUND_END:
            if context and context.get('round_won'):
                return 'excited'
            else:
                return 'supportive'
        
        elif event_type == EventType.BOMB_PLANTED:
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
                tokens=len(content.split())  # Примерная оценка токенов
            )
        )
    
    def _generate_fallback_response(self, event_type: EventType) -> str:
        """
        Генерация ответа-заглушки при ошибках
        
        Args:
            event_type: Тип события
            
        Returns:
            str: Ответ-заглушка
        """
        event_str = event_type.value if isinstance(event_type, EventType) else event_type
        
        # Получение шаблонов для события
        templates = self.response_templates.get(event_str, ["Ок!", "Понятно!", "Хорошо!"])
        
        # Выбор случайного шаблона
        response = random.choice(templates)
        
        # Модификация в зависимости от настроения
        mood = self.stream_context['mood']
        if mood == Mood.SARCASTIC and random.random() > 0.5:
            response = response.replace("!", "...").replace(".", " конечно.")
        elif mood == Mood.EXCITED and random.random() > 0.5:
            response = response.upper()[:1] + response[1:] + "!!!"
        
        logger.debug(f"📦 Заглушка для {event_str}: {response}")
        return response
    
    # ===================== РЕАКЦИИ НА ИГРОВЫЕ СОБЫТИЯ =====================
    def react_to_kill(self, kill_data: Dict, player=None, cs2_gsi=None) -> Optional[str]:
        """
        Реакция на убийство, совершённое стримером
        
        Args:
            kill_data: Данные об убийстве
            player: Объект игрока
            cs2_gsi: Объект CS2 GSI
            
        Returns:
            Optional[str]: Реакция или None
        """
        # Извлечение данных
        round_kills = kill_data.get('round_kills', 1)
        kill_streak = kill_data.get('kill_streak', 1)
        is_headshot = kill_data.get('headshot', False)
        weapon = kill_data.get('weapon', 'unknown').replace('weapon_', '')
        is_ace = kill_data.get('ace', False)
        is_clutch = kill_data.get('clutch', False)
        victim = kill_data.get('victim', 'противник')
        
        # Выбор промпта в зависимости от типа убийства
        if is_ace:
            prompt = f"Игрок только что сделал ACE! Убил всех 5 врагов в раунде! Это невероятно! Дай эпичную реакцию."
        elif round_kills >= 4:
            prompt = f"Игрок убил 4 врагов в этом раунде! Остался последний! Реагируй с волнением."
        elif round_kills >= 3:
            prompt = f"Тройное убийство! Игрок в ярости! Кратко прокомментируй."
        elif is_clutch:
            prompt = f"Clutch ситуация! Игрок в одиночку против нескольких и только что убил одного! Напряжение зашкаливает!"
        elif is_headshot:
            prompt = f"Точный хедшот с {weapon}! Чистый выстрел в голову. Прокомментируй."
        elif kill_streak >= 3:
            prompt = f"Игрок на серии из {kill_streak} убийств! Он в ударе! Поддержи его."
        else:
            # Обычное убийство
            variety = self.response_variety['kill'] % 5
            self.response_variety['kill'] += 1
            
            prompts = [
                f"Игрок убил {victim} с {weapon}. Можешь кратко прокомментировать.",
                f"Ещё один фраг в коллекцию. Оружие: {weapon}.",
                f"Убийство. Игрок продолжает собирать статистику.",
                f"Фраг! {victim} отправлен на respawn.",
                f"Килл. Игра продолжается."
            ]
            prompt = prompts[variety]
        
        # Обновление статистики
        self.player_stats.kills += 1
        self.player_stats.streak += 1
        
        # Обновление контекста
        self.stream_context['recent_events'].append({
            'type': 'kill',
            'weapon': weapon,
            'headshot': is_headshot,
            'time': time.time()
        })
        
        # Генерация ответа (с интеграцией)
        return self.generate_response(prompt, EventType.KILL, player=player, cs2_gsi=cs2_gsi)
    
    def react_to_death(self, death_data: Dict, player=None, cs2_gsi=None) -> Optional[str]:
        """
        Реакция на смерть стримера
        
        Args:
            death_data: Данные о смерти
            player: Объект игрока
            cs2_gsi: Объект CS2 GSI
            
        Returns:
            Optional[str]: Реакция или None
        """
        # Извлечение данных
        killer = death_data.get('killer', 'противник')
        weapon = death_data.get('weapon', 'unknown')
        is_headshot = death_data.get('headshot', False)
        total_deaths = death_data.get('total_deaths', self.player_stats.deaths + 1)
        
        # Обновление статистики
        self.player_stats.deaths += 1
        self.player_stats.streak = 0  # Сброс серии
        
        # Расчёт K/D ratio
        if self.player_stats.deaths > 0:
            self.player_stats.kd_ratio = self.player_stats.kills / self.player_stats.deaths
        
        # Выбор промпта
        variety = self.response_variety['death'] % 4
        self.response_variety['death'] += 1
        
        if self.player_stats.kd_ratio < 0.7:
            prompts = [
                f"Игрок снова умер от {killer} (оружие: {weapon}). K/D сейчас {self.player_stats.kd_ratio:.2f}. Поддержи его.",
                f"Ещё одна смерть. Статистика страдает. Нужно собраться!",
                f"Убит {killer}. Время для реванша!",
                f"Смерть. Но это повод стать лучше!"
            ]
        elif total_deaths > 12:
            prompts = [
                f"Уже {total_deaths} смертей в этом матче. Пора менять тактику?",
                f"Много смертей сегодня. Может, сменить позицию?",
                f"Опять смерть. Но количество переходит в качество!",
                f"Убит. Запомним этого {killer} для реванша."
            ]
        elif is_headshot:
            prompts = [
                f"Хедшот от {killer}... Жёстко. Но это часть игры.",
                f"Выстрел в голову. Уважаю точность {killer}.",
                f"Точный выстрел. Ничего не поделаешь.",
                f"В голову. Иногда везёт противнику."
            ]
        else:
            prompts = [
                f"Игрок умер от {killer} ({weapon}). Можешь посочувствовать или подбодрить.",
                f"Смерть. Время подумать над ошибками.",
                f"Убит. Но игра продолжается!",
                f"Не повезло. Следующий раунд будет нашим!"
            ]
        
        prompt = prompts[variety]
        
        # Обновление контекста
        self.stream_context['recent_events'].append({
            'type': 'death',
            'killer': killer,
            'weapon': weapon,
            'time': time.time()
        })
        
        # Обновление настроения
        if self.player_stats.kd_ratio < 0.5:
            self.stream_context['mood'] = Mood.SUPPORTIVE
        
        return self.generate_response(prompt, EventType.DEATH, player=player, cs2_gsi=cs2_gsi)
    
    def react_to_low_health(self, health: int, player=None, cs2_gsi=None) -> Optional[str]:
        """
        Реакция на критический уровень здоровья
        
        Args:
            health: Текущее здоровье
            player: Объект игрока
            cs2_gsi: Объект CS2 GSI
            
        Returns:
            Optional[str]: Реакция или None
        """
        if health <= 0:
            return None
        
        if health <= 15:
            prompt = f"ВНИМАНИЕ! HP критичный ({health})! Нужно срочно в укрытие!"
            self.stream_context['mood'] = Mood.TENSE
        elif health <= 30:
            prompt = f"HP низкий ({health}). Осторожнее, укройся!"
            self.stream_context['mood'] = Mood.SUPPORTIVE
        elif health <= 50:
            prompt = f"Здоровье не в норме ({health}). Берегись."
        else:
            return None
        
        return self.generate_response(prompt, EventType.DEATH, player=player, cs2_gsi=cs2_gsi)
    
    def react_to_round_end(self, round_data: Dict) -> Optional[str]:
        """
        Реакция на окончание раунда
        
        Args:
            round_data: Данные о раунде
            
        Returns:
            Optional[str]: Реакция или None
        """
        won = round_data.get('won', False)
        round_kills = round_data.get('round_kills', 0)
        is_clutch = round_data.get('clutch', False)
        win_reason = round_data.get('win_reason', '')
        round_number = round_data.get('round_number', 0)
        
        # Обновление контекста
        self.stream_context['round_number'] = round_number
        
        if won:
            if self.game_state.score_t > self.game_state.score_ct:
                self.game_state.score_t += 1
            else:
                self.game_state.score_ct += 1
        else:
            if self.game_state.score_t > self.game_state.score_ct:
                self.game_state.score_ct += 1
            else:
                self.game_state.score_t += 1
        
        # Выбор промпта
        if is_clutch:
            prompt = "Невероятный клатч! Игрок в одиночку выиграл раунд! Это нужно отметить!"
        elif won and round_kills >= 3:
            prompt = f"Раунд выигран! Игрок сделал {round_kills} убийств и принёс команде победу! Похвали его."
        elif won and 'bomb' in win_reason.lower():
            prompt = "Раунд выигран по бомбе! Отлично сработано с закладкой/защитой!"
        elif won:
            prompt = "Раунд выигран! Команда справилась. Коротко прокомментируй."
        elif round_kills >= 3:
            prompt = f"Раунд проигран, но игрок сделал {round_kills} убийств. Он сражался до конца!"
        else:
            prompt = "Раунд проигран. Нужно проанализировать ошибки и двигаться дальше."
        
        # Обновление настроения
        if won:
            self.stream_context['mood'] = random.choice([Mood.HAPPY, Mood.EXCITED])
        else:
            self.stream_context['mood'] = Mood.SUPPORTIVE
        
        # Обновление контекста
        self.stream_context['recent_events'].append({
            'type': 'round_end',
            'won': won,
            'reason': win_reason,
            'time': time.time()
        })
        
        return self.generate_response(prompt, EventType.ROUND_END)
    
    def react_to_bomb_event(self, event_type: str, event_data: Dict) -> Optional[str]:
        """
        Реакция на события с бомбой
        
        Args:
            event_type: Тип события с бомбой
            event_data: Данные о событии
            
        Returns:
            Optional[str]: Реакция или None
        """
        if event_type == 'plant':
            planter = event_data.get('planter', 'игрок')
            site = event_data.get('site', 'A')
            time_left = event_data.get('time_left', 40)
            
            self.game_state.bomb_planted = True
            
            prompt = f"Бомба заложена на {site} {planter}! Осталось {time_left} секунд. Напряжение растёт!"
            
        elif event_type == 'defuse':
            defuser = event_data.get('defuser', 'игрок')
            is_ninja = event_data.get('ninja', False)
            
            self.game_state.bomb_planted = False
            
            if is_ninja:
                prompt = f"НИНДЗЯ ДЕФУЗ! {defuser} обезвредил бомбу прямо под носом у врагов! Невероятно!"
            else:
                prompt = f"Бомба обезврежена {defuser}! Раунд спасён! Отличная работа!"
                
        elif event_type == 'explode':
            self.game_state.bomb_planted = False
            prompt = "Бомба взорвалась! Мощный взрыв завершил раунд."
            
        else:
            return None
        
        return self.generate_response(prompt, EventType.BOMB_EXPLODED)
    
    # ===================== ВЗАИМОДЕЙСТВИЕ С ПОЛЬЗОВАТЕЛЕМ =====================
    def chat_with_user(self, user_message: str, username: str = "стример") -> str:
        """
        Прямой диалог с пользователем
        
        Args:
            user_message: Сообщение пользователя
            username: Имя пользователя
            
        Returns:
            str: Ответ Ирис
        """
        prompt = f"{username} говорит тебе: {user_message}"
        
        # Определение типа сообщения
        user_lower = user_message.lower()
        
        if any(word in user_lower for word in ['привет', 'здаров', 'hi', 'hello']):
            event_type = EventType.CHAT_MESSAGE
            self.stream_context['mood'] = Mood.HAPPY
        elif any(word in user_lower for word in ['как дела', 'как ты', 'how are']):
            event_type = EventType.CHAT_MESSAGE
        elif '?' in user_message:
            event_type = EventType.COMMAND
        else:
            event_type = EventType.CHAT_MESSAGE
        
        return self.generate_response(prompt, event_type, force=True)
    
    # ===================== УТИЛИТЫ И СТАТИСТИКА =====================
    def get_stats(self) -> Dict:
        """
        Получение статистики работы Iris Brain
        
        Returns:
            Dict: Статистика
        """
        stats = self.stats.copy()
        
        # Добавление текущих данных
        stats['conversation_history_size'] = len(self.conversation_history)
        stats['recent_events_count'] = len(self.stream_context['recent_events'])
        stats['current_mood'] = self.stream_context['mood'].value
        stats['uptime'] = time.time() - stats['start_time']
        stats['responses_per_minute'] = stats['total_responses'] / (stats['uptime'] / 60) if stats['uptime'] > 0 else 0
        stats['integration_available'] = INTEGRATION_AVAILABLE
        
        # Текущее состояние игры
        stats['game_state'] = {
            'map': self.game_state.map_name,
            'score': f"{self.game_state.score_ct}-{self.game_state.score_t}",
            'bomb_planted': self.game_state.bomb_planted
        }
        
        # Статистика игрока
        stats['player_stats'] = asdict(self.player_stats)
        
        return stats
    
    def set_mood(self, mood: Mood):
        """
        Установка настроения Ирис
        
        Args:
            mood: Настроение из enum Mood
        """
        self.stream_context['mood'] = mood
        logger.info(f"😊 Настроение установлено: {mood.value}")
    
    def shutdown(self):
        """Корректное завершение работы"""
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
    🎯 IRIS BRAIN v2.1 - ИНТЕГРИРОВАННАЯ
    
    ✅ Компоненты интеграции:
    - context_builder (контекст)
    - prompt_builder (промпты)
    - iris_smart_engine (приоритеты)
    - tts_engine (озвучка)
    """)
    
    # Инициализация
    iris = IrisBrain()
    
    print(f"Режим заглушки: {iris.fallback_mode}")
    print(f"Интеграция доступна: {INTEGRATION_AVAILABLE}")
    print(f"Модель: {iris.model}")
    
    # Тестовые вызовы
    print("\n1️⃣ Тест реакции на убийство:")
    kill_response = iris.react_to_kill({
        'weapon': 'ak47',
        'headshot': True,
        'round_kills': 2,
        'victim': 'противник'
    })
    print(f"Результат: {kill_response}")
    
    print("\n2️⃣ Тест диалога:")
    chat_response = iris.chat_with_user("Привет, Ирис! Как дела?", "Тестер")
    print(f"Результат: {chat_response}")
    
    print("\n3️⃣ Статистика:")
    stats = iris.get_stats()
    print(f"Всего ответов: {stats['total_responses']}")
    print(f"Интеграция: {'✅ Доступна' if stats['integration_available'] else '❌ Недоступна'}")
    
    print("\n✅ ТЕСТ ЗАВЕРШЕН")
