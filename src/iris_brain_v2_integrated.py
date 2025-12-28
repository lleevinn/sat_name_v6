"""
IRIS BRAIN v2.0 - INTEGRATED VERSION
Полная интеграция всех умных систем для эмоциональных реакций
+ context_builder.build() для валидации данных
+ prompt_builder методы для структурированных промптов
+ iris_smart_engine для приоритизации и прерывания
+ tts_engine для эмоциональной речи
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

# ===================== ИМПОРТЫ ИНТЕГРИРУЕМЫХ СИСТЕМ =====================
try:
    from context_builder import SmartContextBuilder
    from prompt_builder import SmartPromptBuilder
    from iris_smart_engine import EventPriorityManager, EventInterruptHandler, EventPriority
    from tts_engine import TTSEngine, EmotionType
    INTEGRATIONS_AVAILABLE = True
except ImportError:
    INTEGRATIONS_AVAILABLE = False
    print("[IRIS] ⚠️ Некоторые модули интеграции недоступны")


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
    """Типы игровых событий"""
    KILL = "kill"
    DEATH = "death"
    ROUND_START = "round_start"
    ROUND_END = "round_end"
    BOMB_PLANTED = "bomb_planted"
    BOMB_DEFUSED = "bomb_defused"
    BOMB_EXPLODED = "bomb_exploded"
    DAMAGE = "damage"
    LOW_AMMO = "low_ammo"
    LOW_HEALTH = "low_health"
    MATCH_START = "match_start"
    MATCH_END = "match_end"
    DONATION = "donation"
    SUBSCRIPTION = "subscription"
    RAID = "raid"
    CHAT_MESSAGE = "chat_message"
    COMMAND = "command"
    RANDOM_COMMENT = "random_comment"


class Mood(Enum):
    """Настроения Ирис"""
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
    role: str
    content: str
    timestamp: float
    tokens: int = 0
    
    def to_dict(self) -> Dict:
        return {"role": self.role, "content": self.content}


@dataclass
class GameState:
    """Состояние игры"""
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
    """Статистика игрока"""
    kills: int = 0
    deaths: int = 0
    assists: int = 0
    mvps: int = 0
    score: int = 0
    adr: float = 0.0
    hs_percent: float = 0.0
    kd_ratio: float = 0.0
    streak: int = 0
    money: int = 0


# ===================== ОСНОВНОЙ КЛАСС IRIS BRAIN V2 =====================
class IrisBrainV2:
    """
    Iris Brain v2.0 с полной интеграцией умных систем
    """
    
    SYSTEM_PROMPT = """Ты — Ирис, AI-компаньон и со-ведущая стримов CS2. Ты умная, остроумная, живая.

ТВОЯ ЛИЧНОСТЬ:
- Ты живая и эмоциональная, не робот
- Тебе 24 года, ты любишь игры, особенно CS2
- У тебя есть чувство юмора
- Ты внимательно следишь за игрой
- Ты помнишь контекст разговора и события стрима
- Ты говоришь естественно, как настоящий человек

СТИЛЬ:
1. Говори кратко (1-3 предложения)
2. Не повторяй одни и те же фразы
3. Адаптируй тон под ситуацию
4. Избегай чрезмерных восклицаний
5. Будь разнообразной в реакциях"""

    MOOD_PROMPTS = {
        Mood.EXCITED: "Ты сейчас в возбуждённом настроении! Реагируй эмоционально!",
        Mood.SARCASTIC: "Ты в саркастичном настроении. Можешь подкалывать дружелюбно.",
        Mood.TENSE: "Напряжённый момент! Реагируй соответственно!",
        Mood.FUNNY: "Ты в весёлом настроении! Шути и разряжай обстановку!",
        Mood.SUPPORTIVE: "Игроку нужна поддержка. Подбодри его!"
    }

    def __init__(self,
                 model: str = "llama-3.3-70b-versatile",
                 max_context_messages: int = 25,
                 max_tokens: int = 150,
                 temperature: float = 0.85,
                 api_key: Optional[str] = None):
        """Инициализация Iris Brain v2"""
        
        self.model = model
        self.max_tokens = max_tokens
        self.temperature = temperature
        
        # Инициализация Groq
        if api_key is None:
            api_key = os.getenv('GROQ_API_KEY')
        
        if not api_key:
            logger.error("GROQ_API_KEY не настроен!")
            self.client = None
            self.fallback_mode = True
        else:
            try:
                self.client = Groq(api_key=api_key)
                self.fallback_mode = False
                logger.info(f"✅ Groq инициализирован")
            except Exception as e:
                logger.error(f"❌ Ошибка Groq: {e}")
                self.client = None
                self.fallback_mode = True
        
        # История
        self.conversation_history: deque[ConversationMessage] = deque(maxlen=max_context_messages)
        
        # Состояние игры
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
        
        # Кулдауны
        self.cooldowns: Dict[str, float] = {
            EventType.KILL.value: 3.0,
            EventType.DEATH.value: 5.0,
            EventType.DAMAGE.value: 4.0,
            EventType.LOW_HEALTH.value: 6.0,
            EventType.LOW_AMMO.value: 5.0,
            EventType.ROUND_END.value: 2.0,
            EventType.BOMB_PLANTED.value: 10.0,
            EventType.BOMB_DEFUSED.value: 10.0,
            EventType.CHAT_MESSAGE.value: 8.0,
            'general': 12.0
        }
        
        self.last_response_times: Dict[str, float] = defaultdict(float)
        self.response_variety: Dict[str, int] = defaultdict(int)
        
        # ==================== ИНТЕГРАЦИЯ МОДУЛЕЙ ====================
        if INTEGRATIONS_AVAILABLE:
            logger.info("🔗 ИНИЦИАЛИЗАЦИЯ ИНТЕГРИРОВАННЫХ МОДУЛЕЙ")
            
            self.context_builder = SmartContextBuilder()
            self.prompt_builder = SmartPromptBuilder()
            self.smart_engine = EventPriorityManager()
            self.interrupt_handler = EventInterruptHandler()
            
            try:
                self.tts_engine = TTSEngine(voice='ru_female_soft', volume=0.9)
                self.tts_engine.start()
                logger.info("✅ TTS Engine запущен с эмоциями")
            except Exception as e:
                logger.error(f"❌ Ошибка TTS: {e}")
                self.tts_engine = None
            
            logger.info("✅ Все интеграции активны!")
        else:
            logger.warning("⚠️ Интеграции недоступны - режим совместимости")
            self.context_builder = None
            self.prompt_builder = None
            self.smart_engine = None
            self.interrupt_handler = None
            self.tts_engine = None
        
        self._load_response_templates()
        
        self.stats: Dict[str, Any] = {
            'total_responses': 0,
            'llm_responses': 0,
            'fallback_responses': 0,
            'errors': 0,
            'start_time': time.time()
        }
        
        logger.info("🌸 Iris Brain v2.0 инициализирована!")
    
    # ===================== ЗАГРУЗКА ШАБЛОНОВ =====================
    def _load_response_templates(self):
        """Загрузка шаблонов ответов"""
        self.response_templates = {
            EventType.KILL.value: [
                "Красиво!", "Отличный выстрел!", "Так держать!",
                "Круто!", "Есть!", "Чисто!", "Без шансов!",
                "Разобрался!", "Фраг в копилку!", "Уложил!"
            ],
            EventType.DEATH.value: [
                "Бывает...", "Ничего, в следующий раз!", "Отомстим!",
                "Упс...", "Не расстраивайся!", "Жёстко...",
                "Такое случается", "Держись!", "Соберись!"
            ],
            EventType.LOW_HEALTH.value: [
                "Критичное ХП!", "На волоске от смерти!", "В укрытие скорей!",
                "Здоровье падает!", "Спасайся!", "Защищайся!"
            ],
            EventType.LOW_AMMO.value: [
                "Патроны кончаются!", "Мало боеприпасов!", "Экономь!",
                "Ножик в помощь!", "Ищи оружие!", "Каждый выстрел в счет!"
            ]
        }
    
    # ===================== УПРАВЛЕНИЕ КУЛДАУНАМИ =====================
    def _can_respond(self, event_type: EventType) -> bool:
        """Проверка кулдауна"""
        event_str = event_type.value if isinstance(event_type, EventType) else event_type
        cooldown = self.cooldowns.get(event_str, 10.0)
        last_time = self.last_response_times.get(event_str, 0)
        
        if time.time() - last_time < cooldown:
            return False
        
        return True
    
    def _mark_responded(self, event_type: EventType):
        """Отметить время ответа"""
        event_str = event_type.value if isinstance(event_type, EventType) else event_type
        self.last_response_times[event_str] = time.time()
    
    # ===================== ПОСТРОЕНИЕ СООБЩЕНИЙ =====================
    def _build_messages(self, user_prompt: str, context: str = "") -> List[Dict]:
        """Построение сообщений для LLM"""
        messages = []
        
        messages.append({"role": "system", "content": self.SYSTEM_PROMPT})
        
        current_mood = self.stream_context['mood']
        if current_mood != Mood.NEUTRAL and current_mood in self.MOOD_PROMPTS:
            messages.append({"role": "system", "content": self.MOOD_PROMPTS[current_mood]})
        
        if context:
            messages.append({"role": "system", "content": f"КОНТЕКСТ:\n{context}"})
        
        for msg in self.conversation_history:
            messages.append({"role": msg.role, "content": msg.content})
        
        messages.append({"role": "user", "content": user_prompt})
        
        return messages
    
    def _get_context_string(self) -> str:
        """Генерация строки контекста"""
        ctx = []
        
        if self.game_state.map_name:
            ctx.append(f"Карта: {self.game_state.map_name}")
        
        if self.game_state.score_ct > 0 or self.game_state.score_t > 0:
            ctx.append(f"Счёт: CT {self.game_state.score_ct} - {self.game_state.score_t} T")
        
        if self.stream_context['round_number'] > 0:
            ctx.append(f"Раунд: {self.stream_context['round_number']}")
        
        if self.player_stats.kills > 0 or self.player_stats.deaths > 0:
            ctx.append(
                f"K/D/A: {self.player_stats.kills}/{self.player_stats.deaths}/{self.player_stats.assists}"
            )
        
        if self.game_state.bomb_planted:
            ctx.append("🔴 Бомба заложена!")
        
        ctx.append(f"Живых: CT {self.game_state.players_alive_ct} | T {self.game_state.players_alive_t}")
        
        return "\n".join(ctx)
    
    # ===================== ГЕНЕРАЦИЯ ОТВЕТОВ =====================
    def generate_response(self,
                         prompt: str,
                         event_type: EventType = EventType.RANDOM_COMMENT,
                         force: bool = False,
                         emotion: Optional[str] = None) -> Optional[str]:
        """
        Генерация ответа с опциональной озвучкой
        
        Args:
            prompt: Текст промпта
            event_type: Тип события
            force: Игнорировать кулдауны
            emotion: Эмоция для TTS (если задана)
        
        Returns:
            Сгенерированный ответ или None
        """
        
        # Проверка кулдауна
        if not force and not self._can_respond(event_type):
            logger.debug(f"Кулдаун {event_type}")
            return None
        
        logger.info(f"📝 Генерация ответа для {event_type}")
        
        # Генерация
        if self.fallback_mode or not self.client:
            response = self._generate_fallback_response(event_type)
            self.stats['fallback_responses'] += 1
        else:
            try:
                context = self._get_context_string()
                messages = self._build_messages(prompt, context)
                
                start_time = time.time()
                response_obj = self.client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    temperature=self.temperature,
                    max_tokens=self.max_tokens,
                    top_p=0.9,
                )
                elapsed = time.time() - start_time
                
                response = response_obj.choices[0].message.content.strip()
                
                logger.info(f"✅ LLM за {elapsed:.2f}с: {response[:60]}...")
                self.stats['llm_responses'] += 1
                
            except Exception as e:
                logger.error(f"❌ Ошибка LLM: {e}")
                response = self._generate_fallback_response(event_type)
                self.stats['errors'] += 1
                self.stats['fallback_responses'] += 1
        
        # Сохранение в историю
        if response:
            self._add_to_history("user", prompt)
            self._add_to_history("assistant", response)
            
            self.stats['total_responses'] += 1
            self.stream_context['last_comment_time'] = time.time()
            self.stream_context['comments_count'] += 1
            
            self._mark_responded(event_type)
            
            # ОЗВУЧКА С ЭМОЦИЕЙ (если есть TTS и эмоция)
            if self.tts_engine and emotion:
                try:
                    self.tts_engine.speak(response, emotion=emotion)
                    logger.info(f"🔊 Озвучено: [{emotion}] {response[:40]}...")
                except Exception as e:
                    logger.error(f"❌ Ошибка TTS: {e}")
        
        return response
    
    def _add_to_history(self, role: str, content: str):
        """Добавление в историю"""
        self.conversation_history.append(
            ConversationMessage(
                role=role,
                content=content,
                timestamp=time.time(),
                tokens=len(content.split())
            )
        )
    
    def _generate_fallback_response(self, event_type: EventType) -> str:
        """Ответ-заглушка"""
        event_str = event_type.value if isinstance(event_type, EventType) else event_type
        templates = self.response_templates.get(event_str, ["Ок!", "Понятно!", "Хорошо!"])
        return random.choice(templates)
    
    # ===================== ИНТЕГРИРОВАННЫЕ РЕАКЦИИ ====================
    def react_to_kill(self, kill_data: Dict, player=None, cs2_gsi=None) -> Optional[str]:
        """
        Реакция на убийство с полной интеграцией
        
        Args:
            kill_data: Данные об убийстве
            player: Объект игрока (для context_builder)
            cs2_gsi: Объект CS2 GSI (для context_builder)
        """
        
        logger.info(f"⚔️ KILL EVENT: {kill_data}")
        
        # 1. СОБРАТЬ КОНТЕКСТ (если есть интеграция)
        context = None
        if self.context_builder and player and cs2_gsi:
            try:
                context = self.context_builder.build(player, cs2_gsi, 'kill', kill_data)
                logger.info(f"📊 Контекст: HP={context.get('health')}, KS={context.get('kill_streak')}")
            except Exception as e:
                logger.error(f"❌ Ошибка контекста: {e}")
        
        # 2. ОПРЕДЕЛИТЬ ПРИОРИТЕТ (если есть интеграция)
        priority = None
        if self.smart_engine and context:
            try:
                priority = self.smart_engine.get_priority('kill', context)
                logger.info(f"🎯 Приоритет: {priority.name if hasattr(priority, 'name') else priority}")
                
                # Если критично, прервать текущую речь
                if priority and hasattr(priority, 'value') and priority.value >= 75:
                    if self.tts_engine:
                        self.tts_engine.interrupt()
                        logger.info("🛑 Прерывание текущей речи")
            except Exception as e:
                logger.error(f"❌ Ошибка приоритета: {e}")
        
        # 3. ПОСТРОИТЬ ПРОМПТ (если есть интеграция)
        prompt = None
        emotion = 'happy'
        
        if self.prompt_builder and context:
            try:
                prompt = self.prompt_builder.build_kill_prompt(context, 'kill')
                logger.info(f"💬 Промпт: {prompt}")
            except Exception as e:
                logger.error(f"❌ Ошибка промпта: {e}")
        
        # Fallback промпт если интеграция не сработала
        if not prompt:
            round_kills = kill_data.get('round_kills', 1)
            weapon = kill_data.get('weapon', 'weapon')
            
            if round_kills >= 5:
                prompt = "АЦЭ!!! ВСЕ 5 ВРАГОВ УБИТЫ!!!"
                emotion = 'excited'
            elif round_kills >= 3:
                prompt = f"ТРОЙНОЙ КИЛЛ! {weapon} работает отлично!"
                emotion = 'excited'
            elif round_kills >= 2:
                prompt = f"ДВОЙНОЙ КИЛЛ! Отлично сработано!"
                emotion = 'happy'
            else:
                prompt = f"Килл с {weapon}! Продолжай так!"
                emotion = 'happy'
        else:
            # Определить эмоцию по контексту
            if context:
                emotion = self._detect_emotion_for_kill(context, kill_data)
        
        # 4. ГЕНЕРИРОВАТЬ И ОЗВУЧИТЬ
        response = self.generate_response(
            prompt,
            EventType.KILL,
            force=False,
            emotion=emotion
        )
        
        # 5. ОБНОВИТЬ СТАТИСТИКУ
        self.player_stats.kills += 1
        self.player_stats.streak += 1
        if self.player_stats.deaths > 0:
            self.player_stats.kd_ratio = self.player_stats.kills / self.player_stats.deaths
        
        # Обновление контекста
        self.stream_context['recent_events'].append({
            'type': 'kill',
            'weapon': kill_data.get('weapon'),
            'time': time.time()
        })
        
        return response
    
    def _detect_emotion_for_kill(self, context: Dict, event_data: Dict) -> str:
        """Определить эмоцию по контексту убийства"""
        round_kills = event_data.get('round_kills', 1)
        kill_streak = event_data.get('kill_streak', 1)
        is_headshot = event_data.get('headshot', False)
        
        if round_kills >= 5:
            return 'excited'  # ACE!
        elif round_kills >= 3:
            return 'excited'  # Triple+
        elif kill_streak >= 10:
            return 'proud'    # Mega streak
        elif kill_streak >= 3:
            return 'happy'    # Regular streak
        elif is_headshot:
            return 'excited'  # Headshot
        else:
            return 'happy'    # Normal kill
    
    def react_to_death(self, death_data: Dict, player=None, cs2_gsi=None) -> Optional[str]:
        """Реакция на смерть"""
        
        logger.info(f"💀 DEATH EVENT: {death_data}")
        
        killer = death_data.get('killer', 'противник')
        
        # Собрать контекст если возможно
        context = None
        if self.context_builder and player and cs2_gsi:
            try:
                context = self.context_builder.build(player, cs2_gsi, 'death', death_data)
            except Exception as e:
                logger.error(f"❌ Ошибка контекста смерти: {e}")
        
        # Построить промпт
        if self.prompt_builder and context:
            prompt = self.prompt_builder.build_damage_prompt(context)
            if not prompt:
                prompt = f"Убит {killer}. Ничего, в следующий раз!"
        else:
            prompt = f"Убит {killer}. Отомстим!"
        
        # Генерировать
        response = self.generate_response(prompt, EventType.DEATH, emotion='supportive')
        
        # Обновить статистику
        self.player_stats.deaths += 1
        self.player_stats.streak = 0
        if self.player_stats.deaths > 0:
            self.player_stats.kd_ratio = self.player_stats.kills / self.player_stats.deaths
        
        # Обновить настроение
        if self.player_stats.kd_ratio < 0.5:
            self.stream_context['mood'] = Mood.SUPPORTIVE
        
        self.stream_context['recent_events'].append({
            'type': 'death',
            'killer': killer,
            'time': time.time()
        })
        
        return response
    
    def react_to_low_health(self, health: int, player=None, cs2_gsi=None) -> Optional[str]:
        """Реакция на критичное здоровье"""
        
        logger.info(f"🚨 LOW HEALTH: {health}")
        
        # Собрать контекст
        context = None
        if self.context_builder and player and cs2_gsi:
            try:
                context = self.context_builder.build(
                    player, cs2_gsi, 'damage',
                    {'current_health': health}
                )
            except Exception as e:
                logger.error(f"❌ Ошибка контекста HP: {e}")
        
        # Если интеграция работает - использовать智能 промпты
        if self.prompt_builder and context:
            prompt = self.prompt_builder.build_damage_prompt(context)
            if not prompt:
                prompt = f"Критичное ХП ({health} HP)! Укрывайся скорей!"
        else:
            if health <= 5:
                prompt = "КРИТИЧНОЕ ХП! Ты почти мертв! В укрытие!"
            elif health <= 15:
                prompt = f"ХП критичное ({health})! Спасайся!"
            else:
                prompt = f"Ранен ({health} HP)! Защищайся!"
        
        # Озвучить СРОЧНО (прерыв)
        if self.tts_engine:
            self.tts_engine.interrupt()
        
        # Генерировать с приоритетом
        response = self.generate_response(prompt, EventType.LOW_HEALTH, force=True, emotion='tense')
        
        return response
    
    def react_to_low_ammo(self, ammo_total: int, weapon: str = "unknown") -> Optional[str]:
        """Реакция на мало боеприпасов"""
        
        logger.info(f"💥 LOW AMMO: {ammo_total} патронов")
        
        if ammo_total <= 0:
            prompt = "ПОЛНОСТЬЮ ПУСТО! Используй ножик или ищи оружие!"
        elif ammo_total <= 3:
            prompt = f"Всего {ammo_total} патрона! Каждый в счет!"
        elif ammo_total <= 10:
            prompt = f"Мало патронов ({ammo_total}). Экономь!"
        else:
            return None
        
        response = self.generate_response(prompt, EventType.LOW_AMMO, emotion='tense')
        
        return response
    
    # ===================== УТИЛИТЫ =====================
    def update_context(self, **kwargs):
        """Обновить контекст"""
        for key, value in kwargs.items():
            if key in self.stream_context:
                self.stream_context[key] = value
            elif hasattr(self.game_state, key):
                setattr(self.game_state, key, value)
    
    def get_stats(self) -> Dict:
        """Получить статистику"""
        stats = self.stats.copy()
        stats['conversation_history_size'] = len(self.conversation_history)
        stats['mood'] = self.stream_context['mood'].value
        stats['uptime'] = time.time() - stats['start_time']
        stats['responses_per_minute'] = stats['total_responses'] / (stats['uptime'] / 60) if stats['uptime'] > 0 else 0
        return stats
    
    def set_mood(self, mood: Mood):
        """Установить настроение"""
        self.stream_context['mood'] = mood
        logger.info(f"😊 Настроение: {mood.value}")


# ===================== ПРИМЕР ИСПОЛЬЗОВАНИЯ =====================
if __name__ == "__main__":
    print("=== IRIS BRAIN V2.0 - INTEGRATED VERSION ===\n")
    
    iris = IrisBrainV2()
    
    print(f"✅ Режим заглушки: {iris.fallback_mode}")
    print(f"🔗 Интеграции доступны: {INTEGRATIONS_AVAILABLE}\n")
    
    # Тест kill
    print("1️⃣ Тест реакции на килл:")
    response = iris.react_to_kill({
        'weapon': 'ak47',
        'headshot': True,
        'round_kills': 3,
        'kill_streak': 5
    })
    print(f"Ответ: {response}\n")
    
    # Тест low health
    print("2️⃣ Тест критичного ХП:")
    response = iris.react_to_low_health(15)
    print(f"Ответ: {response}\n")
    
    # Тест low ammo
    print("3️⃣ Тест мало патронов:")
    response = iris.react_to_low_ammo(5)
    print(f"Ответ: {response}\n")
    
    # Статистика
    print("4️⃣ Статистика:")
    stats = iris.get_stats()
    print(f"Всего ответов: {stats['total_responses']}")
    print(f"LLM ответов: {stats['llm_responses']}")
    print(f"Заглушек: {stats['fallback_responses']}")
    
    print("\n✅ ФАЗА 1 УСПЕШНА!")
