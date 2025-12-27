"""
IRIS CORE 3.0 - Универсальный ИИ-компаньон
Объединяет стрим-компаньона и голосового ассистента
Версия: 3.0.0 (Гибрид)
"""

import os
import time
import json
import logging
import threading
import queue
import asyncio
from typing import Dict, List, Optional, Any, Union, Callable
from dataclasses import dataclass, field, asdict
from enum import Enum
from datetime import datetime
import uuid

try:
    from .modules.qwen_ai import QwenAI
    QWEN_AVAILABLE = True
except ImportError:
    QWEN_AVAILABLE = False
    QwenAI = None

# Настройка логгирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('iris_core.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('IrisCore')

# ===================== БАЗОВЫЕ КЛАССЫ =====================

class IrisMode(Enum):
    """Режимы работы Ирис"""
    STREAM = "stream"           # Режим стрим-компаньона
    VOICE = "voice"            # Голосовой ассистент
    HYBRID = "hybrid"          # Гибридный режим
    AUTO = "auto"              # Автоматическое переключение

class Emotion(Enum):
    """Эмоции Ирис"""
    NEUTRAL = "neutral"
    HAPPY = "happy"
    EXCITED = "excited"
    SARCASTIC = "sarcastic"
    SUPPORTIVE = "supportive"
    TENSE = "tense"
    FUNNY = "funny"
    CALM = "calm"
    ANGRY = "angry"
    SAD = "sad"

@dataclass
class MemoryEntry:
    """Запись в памяти"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    content: str = ""
    category: str = ""  # "game", "user", "preference", "fact"
    importance: float = 0.5  # 0.0-1.0
    timestamp: float = field(default_factory=time.time)
    access_count: int = 0
    tags: List[str] = field(default_factory=list)
    metadata: Dict = field(default_factory=dict)

@dataclass
class UserProfile:
    """Профиль пользователя"""
    user_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    preferences: Dict = field(default_factory=dict)
    voice_patterns: Dict = field(default_factory=dict)
    interaction_history: List = field(default_factory=list)
    adaptation_level: float = 0.0
    created_at: float = field(default_factory=time.time)
    last_interaction: float = field(default_factory=time.time)

# ===================== ОСНОВНОЙ КЛАСС =====================

class IrisBrain:
    """
    Универсальный ИИ-компаньон с поддержкой стримов и голоса
    """
    
    def __init__(self, 
                 mode: IrisMode = IrisMode.HYBRID,
                 config_path: Optional[str] = None,
                 streamer_name: str = "",
                 enable_voice: bool = True,
                 enable_learning: bool = True,
                 api_key: Optional[str] = None):
        """
        Инициализация универсального ИИ
        
        Args:
            mode: Режим работы
            config_path: Путь к конфигурации
            streamer_name: Имя стримера
            enable_voice: Включить голосовые функции
            enable_learning: Включить самообучение
            api_key: API ключ для LLM (если нужен)
        """
        
        print("╔══════════════════════════════════════════════════════════╗")
        print("║               🧠 ИНИЦИАЛИЗАЦИЯ IRIS CORE 3.0              ║")
        print("╚══════════════════════════════════════════════════════════╝")
        
        # Основные параметры
        self.mode = mode
        self.streamer_name = streamer_name or os.getenv('STREAMER_NAME', 'стример')
        self.enable_voice = enable_voice
        self.enable_learning = enable_learning
                # Qwen3 Local AI
        self.qwen = None
        
        # Инициализация компонентов
        self._init_paths()
        self._init_state()
        self._init_components(api_key)
        self._init_threads()
        
        # Загрузка конфигурации
        if config_path:
            self.load_config(config_path)
        
        print(f"✅ IRIS Core 3.0 инициализирован в режиме: {mode.value}")
        print(f"   👤 Стример: {self.streamer_name}")
        print(f"   🔊 Голос: {'ВКЛ' if enable_voice else 'ВЫКЛ'}")
        print(f"   🧠 Самообучение: {'ВКЛ' if enable_learning else 'ВЫКЛ'}")
        print("═══════════════════════════════════════════════════════════")
    
    def _init_paths(self):
        """Инициализация путей"""
        self.base_dir = os.path.expanduser("~/.iris_core")
        os.makedirs(self.base_dir, exist_ok=True)
        
        self.paths = {
            'models': os.path.join(self.base_dir, "models"),
            'profiles': os.path.join(self.base_dir, "profiles"),
            'memory': os.path.join(self.base_dir, "memory"),
            'learning': os.path.join(self.base_dir, "learning"),
            'logs': os.path.join(self.base_dir, "logs")
        }
        
        for path in self.paths.values():
            os.makedirs(path, exist_ok=True)
    
    def _init_state(self):
        """Инициализация состояния"""
        # Основное состояние
        self.is_running = False
        self.is_listening = False
        
        # Эмоции и настроение
        self.current_emotion = Emotion.NEUTRAL
        self.emotion_intensity = 0.5
        self.mood_history = []
        
        # Контекст игры (если режим стрима)
        self.game_state = {
            'map': "",
            'score_ct': 0,
            'score_t': 0,
            'round': 0,
            'phase': "live",
            'bomb_planted': False,
            'player_stats': {
                'kills': 0,
                'deaths': 0,
                'assists': 0,
                'kd': 0.0,
                'streak': 0
            }
        }
        
        # Контекст диалога
        self.conversation_context = {
            'topic': "",
            'last_interaction': 0,
            'user_intent': "",
            'active_goals': [],
            'temporal_context': {}
        }
        
        # Профиль пользователя
        self.user_profile = UserProfile()
        
        # Память
        self.memory = []
        self.short_term_memory = []
        
        # Очереди для межпоточной коммуникации
        self.event_queue = queue.Queue()
        self.command_queue = queue.Queue()
        self.voice_queue = queue.Queue() if self.enable_voice else None
        
        # Коллбэки
        self.callbacks = {
            'on_message': [],
            'on_event': [],
            'on_voice': [],
            'on_emotion_change': [],
            'on_learning': []
        }
    
    def _init_components(self, api_key: Optional[str]):
        """Инициализация компонентов системы"""
        print("[IrisCore] Инициализация компонентов...")
        
        # Проверяем доступность модулей
        try:
            # Импортируем модуль стримов
            from .modules.stream_ai import StreamAI
            self.stream_ai = StreamAI(self)
            print("[IrisCore] ✅ Модуль стримов загружен")
        except ImportError as e:
            print(f"[IrisCore] ⚠️ Модуль стримов недоступен: {e}")
            self.stream_ai = None
        
        # Голосовой модуль
        if self.enable_voice:
            try:
                from .modules.voice_ai import VoiceAI
                self.voice_ai = VoiceAI(self)
                print("[IrisCore] ✅ Голосовой модуль загружен")
            except ImportError as e:
                print(f"[IrisCore] ⚠️ Голосовой модуль недоступен: {e}")
                self.voice_ai = None
        
        # Модуль памяти
        try:
            from .modules.memory import MemorySystem
            self.memory_system = MemorySystem(self)
            print("[IrisCore] ✅ Система памяти загружена")
        except ImportError:
            print("[IrisCore] ⚠️ Система памяти недоступен, используется базовая")
            self.memory_system = None
        
        # Модуль самообучения
        if self.enable_learning:
            try:
                from .modules.learning import LearningSystem
                self.learning_system = LearningSystem(self)
                print("[IrisCore] ✅ Система самообучения загружена")
            except ImportError:
                print("[IrisCore] ⚠️ Система самообучения недоступна")
                self.learning_system = None
        
        # Инициализация LLM (если есть API ключ)
        if api_key:
            self._init_llm(api_key)
    
    def _init_llm(self, api_key: str):
        """Инициализация LLM для генерации ответов"""
        try:
            # Попробуем использовать Groq (из первой версии)
            from groq import Groq
            self.llm_client = Groq(api_key=api_key)
            self.llm_model = "llama-3.3-70b-versatile"
            self.llm_available = True
            print("[IrisCore] ✅ LLM клиент инициализирован")
        except ImportError:
            print("[IrisCore] ⚠️ Groq не установлен, LLM недоступен")
            self.llm_available = False
            self.llm_client = None
    
    def _init_threads(self):
        """Инициализация рабочих потоков"""
        self.threads = {}
        self.thread_config = {
            'event_processor': {'daemon': True, 'target': self._event_loop},
            'memory_processor': {'daemon': True, 'target': self._memory_loop},
            'learning_processor': {'daemon': True, 'target': self._learning_loop} if self.enable_learning else None,
            'voice_processor': {'daemon': True, 'target': self._voice_loop} if self.enable_voice else None
        }
    
    # ===================== ОСНОВНЫЕ МЕТОДЫ =====================
    
    def start(self):
        """Запуск системы"""
        if self.is_running:
            logger.warning("Система уже запущена")
            return
        
        print("🚀 Запуск Iris Core...")
        self.is_running = True
        
        # Запускаем потоки
        for name, config in self.thread_config.items():
            if config:
                thread = threading.Thread(
                    name=f"iris_{name}",
                    daemon=config['daemon'],
                    target=config['target']
                )
                thread.start()
                self.threads[name] = thread
                # Инициализировать Qwen3
        if QWEN_AVAILABLE:
            try:
                self.qwen = QwenAI()
                logger.info("[IRIS] ✅ Qwen3 инициализирован")
            except Exception as e:
                logger.error(f"[IRIS] ⚠️  Qwen3 ошибка: {e}")
            
        # Запускаем голосовой модуль если есть
        if self.enable_voice and self.voice_ai:
            self.voice_ai.start()
        
        print("✅ Iris Core запущен")
        logger.info(f"Iris Core запущен в режиме: {self.mode.value}")
    
    def stop(self):
        """Остановка системы"""
        if not self.is_running:
            return
        
        print("🛑 Остановка Iris Core...")
        self.is_running = False
        
        # Останавливаем голосовой модуль
        if self.enable_voice and self.voice_ai:
            self.voice_ai.stop()
        
        # Сохраняем состояние
        self.save_state()
        
        # Ждем завершения потоков
        for name, thread in self.threads.items():
            if thread.is_alive():
                thread.join(timeout=2.0)
        
        print("✅ Iris Core остановлен")
    
    # ===================== ИНТЕРФЕЙСЫ ДЛЯ СТРИМОВ =====================
    
    def react_to_kill(self, kill_data: Dict) -> Optional[str]:
        """Реакция на убийство (для CS2 стримов)"""
        if self.mode in [IrisMode.STREAM, IrisMode.HYBRID, IrisMode.AUTO]:
            # Обновляем состояние игры
            self._update_game_state('kill', kill_data)
            
            # Генерируем реакцию
            reaction = self._generate_reaction('kill', kill_data)
            
            # Обновляем эмоции
            self._update_emotion('excitement', 0.7)
            
            # Запоминаем событие
            self._remember_event('game_kill', kill_data)
            
            return reaction
        return None
    
    def react_to_death(self, death_data: Dict) -> Optional[str]:
        """Реакция на смерть стримера"""
        if self.mode in [IrisMode.STREAM, IrisMode.HYBRID, IrisMode.AUTO]:
            self._update_game_state('death', death_data)
            reaction = self._generate_reaction('death', death_data)
            self._update_emotion('support', 0.6)
            self._remember_event('game_death', death_data)
            return reaction
        return None
    
    def react_to_round_end(self, round_data: Dict) -> Optional[str]:
        """Реакция на окончание раунда"""
        if self.mode in [IrisMode.STREAM, IrisMode.HYBRID, IrisMode.AUTO]:
            self._update_game_state('round_end', round_data)
            reaction = self._generate_reaction('round_end', round_data)
            
            if round_data.get('won', False):
                self._update_emotion('happy', 0.8)
            else:
                self._update_emotion('supportive', 0.5)
            
            return reaction
        return None
    
    def process_chat_message(self, username: str, message: str) -> Optional[str]:
        """Обработка сообщения из чата"""
        # Сохраняем в историю
        chat_entry = {
            'user': username,
            'message': message,
            'time': time.time(),
            'type': 'chat'
        }
        self._add_to_conversation(chat_entry)
        
        # Определяем, нужно ли отвечать
        should_respond = self._should_respond_to_chat(username, message)
        
        if should_respond:
            # Анализируем намерение
            intent = self._analyze_intent(message)
            
            # Генерируем ответ
            response = self._generate_chat_response(username, message, intent)
            
            # Обновляем профиль пользователя
            self._update_user_profile(username, message)
            
            return response
        
        return None
    
    def qwen_iris_response(self, command: str) -> Optional[str]:
        """
        Получить ответ от локального Qwen3
        
        Args:
            command: Команда пользователя
        
        Returns:
            Ответ или None
        """
        if not self.qwen or not self.qwen.is_available():
            return None
        
        return self.qwen.iris_chat(command)

    
    # ===================== ГОЛОСОВЫЕ ФУНКЦИИ =====================
    
    def process_voice_command(self, audio_data: bytes) -> Dict:
        """Обработка голосовой команды"""
        if not self.enable_voice or not self.voice_ai:
            return {'error': 'Голосовой модуль отключен'}
        
        try:
            # Передаем в голосовой модуль
            result = self.voice_ai.process_audio(audio_data)
            
            if result.get('text'):
                # Анализируем команду
                command_result = self._execute_command(result['text'])
                
                # Объединяем результаты
                result.update({
                    'execution': command_result,
                    'timestamp': time.time()
                })
            
            return result
            
        except Exception as e:
            logger.error(f"Ошибка обработки голосовой команды: {e}")
            return {'error': str(e), 'success': False}
    
    def speak(self, text: str, emotion: Optional[Emotion] = None) -> bool:
        """Озвучивание текста"""
        if not self.enable_voice or not self.voice_ai:
            return False
        
        try:
            # Устанавливаем эмоцию для озвучки
            if emotion:
                self.current_emotion = emotion
            
            # Озвучиваем через голосовой модуль
            return self.voice_ai.synthesize_speech(text, self.current_emotion)
            
        except Exception as e:
            logger.error(f"Ошибка озвучки: {e}")
            return False
    
    # ===================== СИСТЕМНЫЕ ЦИКЛЫ =====================
    
    def _event_loop(self):
        """Цикл обработки событий"""
        logger.info("Запуск цикла обработки событий")
        
        while self.is_running:
            try:
                # Обработка событий из очереди
                event = self.event_queue.get(timeout=0.5)
                self._handle_event(event)
                
            except queue.Empty:
                continue
            except Exception as e:
                logger.error(f"Ошибка в цикле событий: {e}")
    
    def _memory_loop(self):
        """Цикл обработки памяти"""
        logger.info("Запуск цикла обработки памяти")
        
        memory_check_interval = 30  # секунд
        
        while self.is_running:
            try:
                time.sleep(memory_check_interval)
                
                # Оптимизация памяти
                self._optimize_memory()
                
                # Сохранение состояния памяти
                if len(self.memory) > 0:
                    self._save_memory_snapshot()
                
            except Exception as e:
                logger.error(f"Ошибка в цикле памяти: {e}")
    
    def _learning_loop(self):
        """Цикл самообучения"""
        if not self.enable_learning:
            return
        
        logger.info("Запуск цикла самообучения")
        
        learning_interval = 300  # 5 минут
        
        while self.is_running:
            try:
                time.sleep(learning_interval)
                
                # Сбор данных для обучения
                training_data = self._collect_training_data()
                
                if training_data and self.learning_system:
                    # Обучение системы
                    self.learning_system.train(training_data)
                    
                    # Вызываем коллбэк
                    self._trigger_callbacks('on_learning', {
                        'timestamp': time.time(),
                        'samples': len(training_data)
                    })
                
            except Exception as e:
                logger.error(f"Ошибка в цикле обучения: {e}")
    
    def _voice_loop(self):
        """Цикл обработки голоса"""
        if not self.enable_voice:
            return
        
        logger.info("Запуск цикла обработки голоса")
        
        while self.is_running:
            try:
                # Проверяем, нужно ли слушать
                if self.is_listening and self.voice_queue:
                    audio_data = self.voice_queue.get(timeout=0.1)
                    self.process_voice_command(audio_data)
                
                time.sleep(0.05)
                
            except queue.Empty:
                continue
            except Exception as e:
                logger.error(f"Ошибка в голосовом цикле: {e}")
    
    # ===================== ВСПОМОГАТЕЛЬНЫЕ МЕТОДЫ =====================
    
    def _generate_reaction(self, event_type: str, data: Dict) -> str:
        """Генерация реакции на событие"""
        # Сначала пробуем через LLM
        if self.llm_available:
            try:
                return self._generate_llm_reaction(event_type, data)
            except:
                pass
        
        # Если LLM недоступен, используем шаблоны
        templates = self._get_reaction_templates(event_type)
        
        # Выбираем шаблон в зависимости от эмоции
        emotion_templates = templates.get(self.current_emotion.value, templates.get('default', []))
        
        if emotion_templates:
            import random
            return random.choice(emotion_templates)
        
        # Запасной вариант
        return self._get_fallback_reaction(event_type)
    
    def _generate_llm_reaction(self, event_type: str, data: Dict) -> str:
        """Генерация реакции через LLM"""
        prompt = self._build_llm_prompt(event_type, data)
        
        response = self.llm_client.chat.completions.create(
            model=self.llm_model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.8,
            max_tokens=100
        )
        
        return response.choices[0].message.content.strip()
    
    def _build_llm_prompt(self, event_type: str, data: Dict) -> str:
        """Построение промпта для LLM"""
        base_prompt = f"""Ты — Ирис, AI-компаньон для стримов. Ты умная, остроумная, иногда саркастичная.

Контекст:
- Стример: {self.streamer_name}
- Текущая эмоция: {self.current_emotion.value}
- Событие: {event_type}
- Данные: {json.dumps(data, ensure_ascii=False)}

Сгенерируй короткую реакцию (1-2 предложения) в стиле Ирис:"""

        return base_prompt
    
    def _update_emotion(self, emotion_type: str, intensity: float):
        """Обновление эмоционального состояния"""
        # Маппинг типов эмоций на enum
        emotion_map = {
            'happy': Emotion.HAPPY,
            'excited': Emotion.EXCITED,
            'sarcastic': Emotion.SARCASTIC,
            'supportive': Emotion.SUPPORTIVE,
            'tense': Emotion.TENSE,
            'funny': Emotion.FUNNY,
            'calm': Emotion.CALM,
            'angry': Emotion.ANGRY,
            'sad': Emotion.SAD
        }
        
        new_emotion = emotion_map.get(emotion_type, Emotion.NEUTRAL)
        
        # Проверяем, изменилась ли эмоция
        if new_emotion != self.current_emotion or abs(intensity - self.emotion_intensity) > 0.2:
            old_emotion = self.current_emotion
            self.current_emotion = new_emotion
            self.emotion_intensity = intensity
            
            # Сохраняем в историю
            self.mood_history.append({
                'emotion': self.current_emotion.value,
                'intensity': intensity,
                'timestamp': time.time(),
                'reason': emotion_type
            })
            
            # Ограничиваем историю
            if len(self.mood_history) > 100:
                self.mood_history.pop(0)
            
            # Вызываем коллбэки
            self._trigger_callbacks('on_emotion_change', {
                'old': old_emotion.value,
                'new': self.current_emotion.value,
                'intensity': intensity
            })
            
            logger.info(f"Эмоция изменена: {old_emotion.value} → {self.current_emotion.value}")
    
    def _remember_event(self, event_type: str, data: Dict):
        """Запоминание события"""
        memory_entry = MemoryEntry(
            content=f"{event_type}: {json.dumps(data, ensure_ascii=False)}",
            category="event",
            importance=0.7,
            tags=[event_type, 'game' if 'game' in event_type else 'general'],
            metadata=data
        )
        
        self.memory.append(memory_entry)
        
        # Сохраняем в кратковременную память
        self.short_term_memory.append({
            'type': event_type,
            'data': data,
            'timestamp': time.time()
        })
        
        # Ограничиваем кратковременную память
        if len(self.short_term_memory) > 20:
            self.short_term_memory.pop(0)
    
    def _add_to_conversation(self, entry: Dict):
        """Добавление записи в историю диалога"""
        # Добавляем в общую историю
        if not hasattr(self, 'conversation_history'):
            self.conversation_history = []
        
        self.conversation_history.append(entry)
        
        # Ограничиваем размер
        if len(self.conversation_history) > 100:
            self.conversation_history.pop(0)
    
    def _should_respond_to_chat(self, username: str, message: str) -> bool:
        """Определение, нужно ли отвечать на сообщение в чате"""
        message_lower = message.lower()
        
        # Всегда отвечаем на прямое обращение
        if any(word in message_lower for word in ['ирис', 'iris', 'ириска']):
            return True
        
        # Отвечаем на вопросы
        if any(word in message_lower for word in ['?', 'подскажи', 'скажи', 'как']):
            return True
        
        # Случайные ответы (30% шанс)
        import random
        if random.random() < 0.3:
            return True
        
        return False
    
    def _analyze_intent(self, message: str) -> Dict:
        """Анализ намерения пользователя"""
        message_lower = message.lower()
        
        intent = {
            'type': 'unknown',
            'confidence': 0.0,
            'entities': [],
            'action': ''
        }
        
        # Простой анализатор намерений
        intent_patterns = {
            'question': ['?', 'что', 'как', 'почему', 'зачем', 'когда'],
            'greeting': ['привет', 'здравствуй', 'hello', 'hi', 'здаров'],
            'compliment': ['молодец', 'круто', 'супер', 'отлично', 'хорошо'],
            'request': ['сделай', 'включи', 'выключи', 'найди', 'покажи'],
            'game_related': ['cs', 'контру', 'стрелялка', 'раунд', 'фраг']
        }
        
        for intent_type, patterns in intent_patterns.items():
            for pattern in patterns:
                if pattern in message_lower:
                    intent['type'] = intent_type
                    intent['confidence'] = 0.8
                    intent['action'] = pattern
                    break
        
        return intent
    
    def _execute_command(self, command: str) -> Dict:
        """Выполнение команды"""
        command_lower = command.lower()
        
        result = {
            'success': False,
            'action': 'unknown',
            'message': '',
            'data': {}
        }
        
        # Простые команды
        if any(word in command_lower for word in ['привет', 'здравствуй']):
            result.update({
                'success': True,
                'action': 'greet',
                'message': f'Привет! Как дела, {self.streamer_name}?'
            })
        
        elif any(word in command_lower for word in ['пока', 'до свидания']):
            result.update({
                'success': True,
                'action': 'goodbye',
                'message': 'До скорой встречи! Буду скучать!'
            })
        
        elif any(word in command_lower for word in ['расскажи о себе', 'кто ты']):
            result.update({
                'success': True,
                'action': 'self_intro',
                'message': 'Я Ирис — твой ИИ-компаньон для стримов и не только! Помогаю с реакциями, общением и даже могу поддержать беседу!'
            })
        
        elif 'настроение' in command_lower:
            result.update({
                'success': True,
                'action': 'mood_check',
                'message': f'Моё настроение: {self.current_emotion.value}. Интенсивность: {self.emotion_intensity:.1%}'
            })
        
        else:
            result['message'] = 'Не совсем поняла команду. Можешь повторить?'
        
        return result
    
    def _trigger_callbacks(self, callback_type: str, data: Any):
        """Вызов коллбэков"""
        if callback_type in self.callbacks:
            for callback in self.callbacks[callback_type]:
                try:
                    callback(data)
                except Exception as e:
                    logger.error(f"Ошибка в коллбэке {callback_type}: {e}")
    
    # ===================== УТИЛИТЫ =====================
    
    def add_callback(self, callback_type: str, callback: Callable):
        """Добавление коллбэка"""
        if callback_type in self.callbacks:
            self.callbacks[callback_type].append(callback)
            logger.info(f"Добавлен коллбэк типа: {callback_type}")
        else:
            logger.warning(f"Неизвестный тип коллбэка: {callback_type}")
    
    def get_status(self) -> Dict:
        """Получение статуса системы"""
        return {
            'running': self.is_running,
            'mode': self.mode.value,
            'emotion': self.current_emotion.value,
            'emotion_intensity': self.emotion_intensity,
            'game_state': self.game_state,
            'memory_entries': len(self.memory),
            'conversation_history': len(self.conversation_history) if hasattr(self, 'conversation_history') else 0,
            'voice_enabled': self.enable_voice,
            'learning_enabled': self.enable_learning,
            'llm_available': self.llm_available if hasattr(self, 'llm_available') else False
        }
    
    def save_state(self):
        """Сохранение состояния системы"""
        state = {
            'user_profile': asdict(self.user_profile),
            'memory': [asdict(entry) for entry in self.memory[-100:]],  # Сохраняем последние 100
            'conversation_history': self.conversation_history if hasattr(self, 'conversation_history') else [],
            'mood_history': self.mood_history,
            'game_state': self.game_state,
            'last_save': time.time()
        }
        
        try:
            state_path = os.path.join(self.paths['memory'], 'system_state.json')
            with open(state_path, 'w', encoding='utf-8') as f:
                json.dump(state, f, ensure_ascii=False, indent=2)
            logger.info("Состояние системы сохранено")
        except Exception as e:
            logger.error(f"Ошибка сохранения состояния: {e}")
    
    def load_config(self, config_path: str):
        """Загрузка конфигурации"""
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
            
            # Загружаем настройки
            if 'streamer_name' in config:
                self.streamer_name = config['streamer_name']
            
            if 'mode' in config:
                self.mode = IrisMode(config['mode'])
            
            # Загружаем шаблоны реакций
            if 'reaction_templates' in config:
                self.reaction_templates = config['reaction_templates']
            
            logger.info(f"Конфигурация загружена из {config_path}")
            
        except Exception as e:
            logger.error(f"Ошибка загрузки конфигурации: {e}")
    
    def _get_reaction_templates(self, event_type: str) -> Dict:
        """Получение шаблонов реакций"""
        # Базовые шаблоны (можно расширять через конфиг)
        templates = {
            'kill': {
                'excited': ['Красиво!', 'Отличный выстрел!', 'Так держать!'],
                'sarcastic': ['Ну наконец-то!', 'Было время!', 'Уже лучше!'],
                'default': ['Фраг!', 'Есть!', 'Килл!']
            },
            'death': {
                'supportive': ['Бывает...', 'Ничего, в следующий раз!', 'Отомстим!'],
                'sarcastic': ['Ну ты даёшь!', 'Ай-ай-ай...', 'Так себе концовка'],
                'default': ['Упс...', 'Не повезло', 'Жаль...']
            },
            'round_end': {
                'happy': ['Хороший раунд!', 'Отлично сыграно!', 'Команда молодец!'],
                'supportive': ['Держимся!', 'Следующий будет нашим!', 'Не сдаемся!'],
                'default': ['Раунд завершен', 'Продолжаем', 'Следующий!']
            }
        }
        
        return templates.get(event_type, {'default': ['Интересно!', 'Понятно!', 'Хм...']})
    
    def _get_fallback_reaction(self, event_type: str) -> str:
        """Запасная реакция"""
        fallbacks = {
            'kill': 'Неплохо!',
            'death': 'Бывает...',
            'round_end': 'Раунд завершен!',
            'default': 'Интересно!'
        }
        
        return fallbacks.get(event_type, fallbacks['default'])
    
    def _update_game_state(self, event_type: str, data: Dict):
        """Обновление состояния игры"""
        if event_type == 'kill':
            self.game_state['player_stats']['kills'] += 1
            self.game_state['player_stats']['streak'] += 1
            
        elif event_type == 'death':
            self.game_state['player_stats']['deaths'] += 1
            self.game_state['player_stats']['streak'] = 0
            
        # Обновляем K/D ratio
        kills = self.game_state['player_stats']['kills']
        deaths = self.game_state['player_stats']['deaths']
        self.game_state['player_stats']['kd'] = kills / max(deaths, 1)
    
    def _update_user_profile(self, username: str, message: str):
        """Обновление профиля пользователя"""
        # Ищем или создаем запись о пользователе
        if not hasattr(self, 'user_interactions'):
            self.user_interactions = {}
        
        if username not in self.user_interactions:
            self.user_interactions[username] = {
                'count': 0,
                'last_message': '',
                'first_seen': time.time(),
                'last_seen': time.time()
            }
        
        user_data = self.user_interactions[username]
        user_data['count'] += 1
        user_data['last_message'] = message
        user_data['last_seen'] = time.time()
        
        # Обновляем общий профиль
        self.user_profile.interaction_history.append({
            'user': username,
            'message': message,
            'timestamp': time.time()
        })
        
        # Ограничиваем историю
        if len(self.user_profile.interaction_history) > 1000:
            self.user_profile.interaction_history.pop(0)
    
    def _optimize_memory(self):
        """Оптимизация памяти"""
        # Удаляем старые неважные записи
        current_time = time.time()
        self.memory = [
            entry for entry in self.memory
            if entry.importance > 0.3 or (current_time - entry.timestamp) < 604800  # 7 дней
        ]
    
    def _save_memory_snapshot(self):
        """Сохранение снимка памяти"""
        try:
            snapshot = {
                'timestamp': time.time(),
                'entries': [asdict(entry) for entry in self.memory[-50:]],  # Последние 50 записей
                'total_entries': len(self.memory)
            }
            
            snapshot_path = os.path.join(
                self.paths['memory'], 
                f'memory_snapshot_{int(time.time())}.json'
            )
            
            with open(snapshot_path, 'w', encoding='utf-8') as f:
                json.dump(snapshot, f, ensure_ascii=False, indent=2)
                
        except Exception as e:
            logger.error(f"Ошибка сохранения снимка памяти: {e}")
    
    def _collect_training_data(self) -> List:
        """Сбор данных для обучения"""
        training_data = []
        
        # Собираем из истории диалогов
        if hasattr(self, 'conversation_history'):
            for entry in self.conversation_history[-50:]:  # Последние 50
                if 'message' in entry and 'user' in entry:
                    training_data.append({
                        'input': entry['message'],
                        'context': entry.get('context', ''),
                        'timestamp': entry.get('time', 0)
                    })
        
        return training_data
    
    def _generate_chat_response(self, username: str, message: str, intent: Dict) -> str:
        """Генерация ответа на сообщение в чате"""
        # Простые ответы в зависимости от намерения
        if intent['type'] == 'greeting':
            responses = [
                f'Привет, {username}!',
                f'Здравствуй, {username}! Рада тебя видеть!',
                f'Приветствую, {username}! Как настроение?'
            ]
            import random
            return random.choice(responses)
        
        elif intent['type'] == 'question':
            # Пытаемся ответить на вопрос
            if 'как дела' in message.lower():
                return f'У меня всё отлично! Спасибо, что спрашиваешь, {username}! А у тебя?'
            elif 'что делаешь' in message.lower():
                return 'Слежу за стримом и помогаю с реакциями!'
        
        elif intent['type'] == 'compliment':
            return 'Спасибо за добрые слова! Очень приятно!'
        
        # Общий ответ
        general_responses = [
            'Интересно!',
            'Поняла тебя!',
            'Спасибо за сообщение!',
            'Заметил!'
        ]
        
        import random
        return random.choice(general_responses)
    
    # ===================== ПУБЛИЧНЫЕ МЕТОДЫ =====================
    
    def switch_mode(self, new_mode: Union[IrisMode, str]):
        """Переключение режима работы"""
        if isinstance(new_mode, str):
            new_mode = IrisMode(new_mode)
        
        old_mode = self.mode
        self.mode = new_mode
        
        logger.info(f"Режим изменен: {old_mode.value} → {new_mode.value}")
        
        # Адаптируем поведение под новый режим
        if new_mode == IrisMode.VOICE:
            self._update_emotion('calm', 0.6)
        elif new_mode == IrisMode.STREAM:
            self._update_emotion('excited', 0.7)
        
        return True
    
    def get_memory_summary(self) -> str:
        """Получение сводки памяти"""
        if not self.memory:
            return "Память пуста"
        
        # Группируем по категориям
        categories = {}
        for entry in self.memory[-20:]:  # Последние 20 записей
            cat = entry.category
            if cat not in categories:
                categories[cat] = 0
            categories[cat] += 1
        
        summary = f"Всего записей: {len(self.memory)}\n"
        summary += "По категориям:\n"
        for cat, count in categories.items():
            summary += f"  - {cat}: {count}\n"
        
        return summary
    
    def remember_fact(self, fact: str, category: str = "general", importance: float = 0.5):
        """Запоминание факта"""
        entry = MemoryEntry(
            content=fact,
            category=category,
            importance=importance,
            tags=['fact', category],
            metadata={'source': 'user_input'}
        )
        
        self.memory.append(entry)
        return entry.id
    
    def recall(self, query: str, limit: int = 5) -> List[MemoryEntry]:
        """Поиск в памяти по запросу"""
        query_lower = query.lower()
        results = []
        
        for entry in reversed(self.memory):  # Ищем с конца (новые сначала)
            if (query_lower in entry.content.lower() or 
                any(query_lower in tag.lower() for tag in entry.tags)):
                entry.access_count += 1
                results.append(entry)
                
                if len(results) >= limit:
                    break
        
        return results


# ===================== БЫСТРЫЙ СТАРТ =====================

def create_iris_companion(config: Optional[Dict] = None) -> IrisBrain:
    """
    Быстрое создание экземпляра IrisBrain
    
    Args:
        config: Конфигурация (опционально)
    
    Returns:
        IrisBrain: Экземпляр компаньона
    """
    config = config or {}
    
    return IrisBrain(
        mode=IrisMode(config.get('mode', 'hybrid')),
        streamer_name=config.get('streamer_name', ''),
        enable_voice=config.get('enable_voice', True),
        enable_learning=config.get('enable_learning', True),
        api_key=config.get('api_key')
    )


# ===================== ТЕСТ =====================

if __name__ == "__main__":
    print("🧪 Тестирование Iris Core 3.0...")
    
    # Создаем экземпляр
    iris = create_iris_companion({
        'streamer_name': 'Ghost',
        'mode': 'hybrid',
        'enable_voice': False  # Для теста без голоса
    })
    
    # Запускаем
    iris.start()
    
    print("\n📋 Тестовые команды:")
    print("1. Реакция на убийство")
    print("2. Обработка сообщения чата")
    print("3. Проверка памяти")
    print("4. Выход")
    
    try:
        while True:
            cmd = input("\nВыберите команду (1-4): ").strip()
            
            if cmd == "1":
                reaction = iris.react_to_kill({
                    'weapon': 'ak47',
                    'headshot': True,
                    'round_kills': 3
                })
                print(f"Реакция: {reaction}")
                
            elif cmd == "2":
                response = iris.process_chat_message("Viewer123", "Ирис, привет! Как дела?")
                print(f"Ответ: {response}")
                
            elif cmd == "3":
                summary = iris.get_memory_summary()
                print(f"Память:\n{summary}")
                
            elif cmd == "4":
                break
                
            else:
                print("Неизвестная команда")
                
    finally:
        iris.stop()
        print("\n✅ Тест завершен")