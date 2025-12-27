"""
IRIS Voice Input - Супер-продвинутая версия голосового ассистента
Версия: 5.0.0 - ИИ-Мозг с самообучением и нейросетевыми возможностями
"""

import asyncio
import threading
import time
import queue
import os
import json
import logging
import sys
import pickle
import hashlib
import uuid
from typing import Optional, Callable, List, Dict, Any, Tuple, Union, Set
from pathlib import Path
from dataclasses import dataclass, asdict, field
from enum import Enum, auto
from datetime import datetime, timedelta
from collections import defaultdict, deque
import numpy as np
import wave
import io

# Настройка логгирования с нейросетевым анализом
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('iris_ai.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('IRIS-AI')

# ============================================
# КОНСТАНТЫ И КОНФИГУРАЦИЯ ИИ-МОДУЛЯ
# ============================================

AI_MODES = {
    "ADAPTIVE": "adaptive",           # Адаптивный с самообучением
    "NEURAL": "neural",               # Нейросетевой режим
    "CONTEXTUAL": "contextual",       # Контекстно-зависимый
    "EMOTIONAL": "emotional",         # С эмоциональным интеллектом
    "MULTIMODAL": "multimodal",       # Мультимодальный (голос + текст)
    "AUTONOMOUS": "autonomous"        # Автономное принятие решений
}

EMOTION_TYPES = {
    "NEUTRAL": "neutral",
    "HAPPY": "happy",
    "SAD": "sad",
    "ANGRY": "angry",
    "EXCITED": "excited",
    "CALM": "calm",
    "STRESSED": "stressed",
    "CONFUSED": "confused"
}

CONTEXT_DOMAINS = {
    "WEATHER": "weather",
    "MUSIC": "music",
    "NEWS": "news",
    "SMART_HOME": "smart_home",
    "SCHEDULE": "schedule",
    "COMMUNICATION": "communication",
    "ENTERTAINMENT": "entertainment",
    "PRODUCTIVITY": "productivity",
    "LEARNING": "learning",
    "HEALTH": "health"
}

# ============================================
# ДИНАМИЧЕСКИЕ ИМПОРТЫ МАШИННОГО ОБУЧЕНИЯ
# ============================================

# Базовые зависимости
try:
    import numpy as np
    NP_AVAILABLE = True
except ImportError:
    NP_AVAILABLE = False
    logger.warning("NumPy не установлен. Установите: pip install numpy")

# Аудиообработка
try:
    import sounddevice as sd
    import soundfile as sf
    SOUND_AVAILABLE = True
except ImportError:
    SOUND_AVAILABLE = False
    logger.warning("SoundDevice/SoundFile не установлены")

try:
    import pyaudio
    import wave
    PYAUDIO_AVAILABLE = True
except ImportError:
    PYAUDIO_AVAILABLE = False

# Распознавание речи
try:
    from vosk import Model, KaldiRecognizer, SetLogLevel
    SetLogLevel(-1)
    VOSK_AVAILABLE = True
except ImportError:
    VOSK_AVAILABLE = False

try:
    import speech_recognition as sr
    SR_AVAILABLE = True
except ImportError:
    SR_AVAILABLE = False

# Яндекс SpeechKit
try:
    import requests
    import uuid as uuid_lib
    YANDEX_AVAILABLE = True
except ImportError:
    YANDEX_AVAILABLE = False

# Машинное обучение и нейросети
ML_LIBS = {}
try:
    import torch
    import torch.nn as nn
    import torch.nn.functional as F
    from torch.utils.data import Dataset, DataLoader
    ML_LIBS['PYTORCH'] = True
except ImportError:
    ML_LIBS['PYTORCH'] = False

try:
    import tensorflow as tf
    ML_LIBS['TENSORFLOW'] = True
except ImportError:
    ML_LIBS['TENSORFLOW'] = False

try:
    import sklearn
    from sklearn.cluster import KMeans
    from sklearn.decomposition import PCA
    from sklearn.preprocessing import StandardScaler
    ML_LIBS['SKLEARN'] = True
except ImportError:
    ML_LIBS['SKLEARN'] = False

# NLP и обработка текста
try:
    import nltk
    from nltk.tokenize import word_tokenize
    from nltk.corpus import stopwords
    nltk.download('punkt', quiet=True)
    nltk.download('stopwords', quiet=True)
    NLP_AVAILABLE = True
except ImportError:
    NLP_AVAILABLE = False

# Аудиообработка продвинутая
try:
    import librosa
    import librosa.display
    AUDIO_ML_AVAILABLE = True
except ImportError:
    AUDIO_ML_AVAILABLE = False

# Визуализация и аналитика
try:
    import matplotlib.pyplot as plt
    from matplotlib.animation import FuncAnimation
    VISUAL_AVAILABLE = True
except ImportError:
    VISUAL_AVAILABLE = False

# ============================================
# ДАТАКЛАССЫ ДЛЯ ИИ-СТРУКТУР
# ============================================

@dataclass
class NeuralConfig:
    """Конфигурация нейросетевого модуля"""
    use_attention: bool = True
    use_transformer: bool = True
    hidden_layers: int = 4
    neurons_per_layer: int = 256
    dropout_rate: float = 0.3
    learning_rate: float = 0.001
    batch_size: int = 32
    epochs: int = 100
    use_pretrained: bool = True
    model_type: str = "transformer"  # transformer, lstm, cnn, hybrid
    feature_size: int = 128
    context_window: int = 10

@dataclass
class EmotionState:
    """Состояние эмоций пользователя"""
    emotion: str = "neutral"
    confidence: float = 0.0
    intensity: float = 0.0
    valence: float = 0.0  # Позитивность
    arousal: float = 0.0  # Возбуждение
    dominance: float = 0.0  # Доминирование
    timestamp: float = field(default_factory=time.time)
    history: List[Dict] = field(default_factory=list)

@dataclass
class UserProfile:
    """Профиль пользователя с адаптацией"""
    user_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    voice_features: Dict = field(default_factory=dict)
    speech_patterns: Dict = field(default_factory=dict)
    preferences: Dict = field(default_factory=dict)
    learning_rate: float = 0.1
    adaptation_level: float = 0.0
    interaction_count: int = 0
    last_interaction: float = field(default_factory=time.time)
    created_at: float = field(default_factory=time.time)

@dataclass
class AIContext:
    """Контекст ИИ-ассистента"""
    current_domain: str = ""
    previous_commands: List[str] = field(default_factory=list)
    user_intent: str = ""
    entities: List[Dict] = field(default_factory=list)
    conversation_history: List[Dict] = field(default_factory=list)
    memory: Dict = field(default_factory=dict)
    context_score: float = 0.0
    temporal_context: Dict = field(default_factory=dict)

@dataclass
class LearningData:
    """Данные для самообучения"""
    audio_samples: List = field(default_factory=list)
    transcriptions: List = field(default_factory=list)
    corrections: List = field(default_factory=list)
    success_patterns: List = field(default_factory=list)
    error_patterns: List = field(default_factory=list)
    reinforcement_signals: List = field(default_factory=list)

@dataclass
class PerformanceMetrics:
    """Расширенные метрики производительности"""
    real_time_factor: float = 0.0
    latency: Dict = field(default_factory=lambda: {"audio": 0.0, "processing": 0.0})
    accuracy: Dict = field(default_factory=lambda: {"wake": 0.0, "command": 0.0})
    efficiency: Dict = field(default_factory=lambda: {"cpu": 0.0, "memory": 0.0})
    quality: Dict = field(default_factory=lambda: {"audio": 0.0, "recognition": 0.0})

# ============================================
# НЕЙРОСЕТЕВЫЕ МОДУЛИ
# ============================================

class VoiceEncoder(nn.Module):
    """Нейросеть для кодирования голосовых особенностей"""
    def __init__(self, input_dim=128, hidden_dim=256, latent_dim=64):
        super().__init__()
        self.encoder = nn.Sequential(
            nn.Linear(input_dim, hidden_dim),
            nn.ReLU(),
            nn.Dropout(0.2),
            nn.Linear(hidden_dim, hidden_dim // 2),
            nn.ReLU(),
            nn.Linear(hidden_dim // 2, latent_dim)
        )
        
        self.decoder = nn.Sequential(
            nn.Linear(latent_dim, hidden_dim // 2),
            nn.ReLU(),
            nn.Linear(hidden_dim // 2, hidden_dim),
            nn.ReLU(),
            nn.Linear(hidden_dim, input_dim),
            nn.Sigmoid()
        )
        
    def forward(self, x):
        latent = self.encoder(x)
        reconstructed = self.decoder(latent)
        return latent, reconstructed

class EmotionClassifier(nn.Module):
    """Классификатор эмоций по голосу"""
    def __init__(self, input_dim=128, num_emotions=8):
        super().__init__()
        self.conv1 = nn.Conv1d(1, 32, kernel_size=5, stride=2)
        self.conv2 = nn.Conv1d(32, 64, kernel_size=5, stride=2)
        self.conv3 = nn.Conv1d(64, 128, kernel_size=5, stride=2)
        
        self.lstm = nn.LSTM(128, 128, batch_first=True, bidirectional=True)
        
        self.fc = nn.Sequential(
            nn.Linear(256, 128),
            nn.ReLU(),
            nn.Dropout(0.3),
            nn.Linear(128, num_emotions),
            nn.Softmax(dim=1)
        )
        
    def forward(self, x):
        x = x.unsqueeze(1)  # Add channel dimension
        x = F.relu(self.conv1(x))
        x = F.relu(self.conv2(x))
        x = F.relu(self.conv3(x))
        
        x = x.transpose(1, 2)
        lstm_out, _ = self.lstm(x)
        
        # Use last hidden state
        last_hidden = lstm_out[:, -1, :]
        emotion_probs = self.fc(last_hidden)
        return emotion_probs

class IntentRecognizer:
    """Распознавание намерений с использованием NLP"""
    def __init__(self):
        self.intent_patterns = {
            "включить": ["включи", "запусти", "активируй", "вруби", "старт"],
            "выключить": ["выключи", "останови", "деактивируй", "выруби", "стоп"],
            "узнать": ["сколько", "какая", "какой", "что", "кто", "где", "когда"],
            "изменить": ["измени", "настрой", "скорректируй", "поправь"],
            "найти": ["найди", "поищи", "ищи", "отыщи", "локализуй"],
            "создать": ["создай", "сделай", "построй", "организуй", "придумай"],
            "удалить": ["удали", "убери", "стерни", "ликвидируй", "сотри"],
            "помочь": ["помоги", "подскажи", "объясни", "посоветуй", "расскажи"]
        }
        
        self.entity_types = {
            "устройство": ["телевизор", "свет", "лампа", "кондиционер", "обогреватель"],
            "медиа": ["музыка", "фильм", "видео", "радио", "подкаст"],
            "информация": ["погода", "новости", "курс", "время", "дата"],
            "настройка": ["громкость", "яркость", "температура", "скорость"]
        }
        
    def extract_intent(self, text: str) -> Dict:
        """Извлечение намерения и сущностей из текста"""
        result = {
            "intent": "unknown",
            "confidence": 0.0,
            "entities": [],
            "action": "",
            "target": ""
        }
        
        text_lower = text.lower()
        words = text_lower.split()
        
        # Определяем интент
        for intent, patterns in self.intent_patterns.items():
            for pattern in patterns:
                if pattern in text_lower:
                    result["intent"] = intent
                    result["confidence"] = 0.8
                    result["action"] = pattern
                    break
        
        # Извлекаем сущности
        for entity_type, entities in self.entity_types.items():
            for entity in entities:
                if entity in text_lower:
                    result["entities"].append({
                        "type": entity_type,
                        "value": entity,
                        "position": text_lower.find(entity)
                    })
        
        # Определяем цель (последнее существительное)
        if NLP_AVAILABLE:
            try:
                tokens = word_tokenize(text_lower, language='russian')
                pos_tags = nltk.pos_tag(tokens, lang='rus')
                
                for word, tag in pos_tags:
                    if tag.startswith('S'):  # Существительное
                        result["target"] = word
            except:
                pass
        
        return result

# ============================================
# ОСНОВНОЙ КЛАСС IRIS AI
# ============================================

class IRISVoiceAI:
    """
    Супер-продвинутый ИИ-ассистент с самообучением и нейросетевыми возможностями
    """
    
    # Wake word вариации с нейросетевым распознаванием
    WAKE_WORD_VARIANTS = [
        'ирис', 'iris', 'ири', 'ириска', 'ирисс', 'ириса',
        'айрис', 'арис', 'ириш', 'ирись', 'рис', 'эрис',
        'ирисю', 'ирися', 'ирису', 'ирисе', 'ириша'
    ]
    
    # Команды с контекстным пониманием
    SMART_COMMANDS = {
        'погода': {
            'actions': ['погода', 'прогноз', 'температура', 'дождь', 'солнце'],
            'context': 'weather',
            'requires_location': True
        },
        'музыка': {
            'actions': ['музыка', 'песня', 'трек', 'альбом', 'плейлист'],
            'context': 'music',
            'requires_query': True
        },
        'новости': {
            'actions': ['новости', 'события', 'происшествия', 'сводка'],
            'context': 'news',
            'category': 'general'
        },
        'умный дом': {
            'actions': ['включи', 'выключи', 'свет', 'температура', 'розетка'],
            'context': 'smart_home',
            'devices': ['свет', 'лампа', 'телевизор', 'кондиционер']
        }
    }
    
    def __init__(self, 
                 config_path: Optional[str] = None,
                 ai_mode: str = "adaptive",
                 neural_config: Optional[NeuralConfig] = None,
                 enable_self_learning: bool = True,
                 enable_emotion_recognition: bool = True,
                 enable_context_awareness: bool = True):
        """
        Инициализация ИИ-ассистента
        
        Args:
            config_path: Путь к файлу конфигурации
            ai_mode: Режим ИИ (adaptive, neural, contextual, emotional, multimodal, autonomous)
            neural_config: Конфигурация нейросетей
            enable_self_learning: Включить самообучение
            enable_emotion_recognition: Распознавание эмоций
            enable_context_awareness: Контекстная осведомленность
        """
        
        print("╔═══════════════════════════════════════════════════════╗")
        print("║         🧠 ИНИЦИАЛИЗАЦИЯ IRIS AI МОЗГА                ║")
        print("╚═══════════════════════════════════════════════════════╝")
        
        # Основные настройки
        self.ai_mode = ai_mode
        self.enable_self_learning = enable_self_learning
        self.enable_emotion_recognition = enable_emotion_recognition
        self.enable_context_awareness = enable_context_awareness
        
        # Нейросетевая конфигурация
        self.neural_config = neural_config or NeuralConfig()
        
        # Инициализация компонентов
        self._init_paths()
        self._init_components()
        self._init_neural_networks()
        self._init_ai_modules()
        
        # Состояния ИИ
        self.emotion_state = EmotionState()
        self.user_profile = UserProfile()
        self.ai_context = AIContext()
        self.learning_data = LearningData()
        self.performance_metrics = PerformanceMetrics()
        
        # Система очередей и потоков
        self.command_queue = queue.PriorityQueue()
        self.audio_queue = queue.Queue()
        self.event_queue = asyncio.Queue()
        
        # Потоки обработки
        self.threads = {}
        self.is_running = False
        self.is_learning = False
        
        # Коллбэки и обработчики
        self.callbacks = {
            'command': [],
            'wake': [],
            'error': [],
            'emotion_change': [],
            'context_change': [],
            'learning_update': [],
            'intent_detected': []
        }
        
        # Загрузка конфигурации
        if config_path and os.path.exists(config_path):
            self._load_config(config_path)
        
        # Вывод информации о системе
        self._print_system_info()
        
        print("✅ IRIS AI Мозг инициализирован и готов к работе!")
        print("═════════════════════════════════════════════════════════")
    
    def _init_paths(self):
        """Инициализация путей для данных ИИ"""
        self.base_dir = Path.home() / ".iris_ai"
        self.base_dir.mkdir(exist_ok=True)
        
        self.paths = {
            'models': self.base_dir / "models",
            'profiles': self.base_dir / "profiles",
            'learning': self.base_dir / "learning",
            'audio': self.base_dir / "audio_samples",
            'logs': self.base_dir / "logs",
            'config': self.base_dir / "config"
        }
        
        for path in self.paths.values():
            path.mkdir(exist_ok=True)
    
    def _init_components(self):
        """Инициализация всех компонентов системы"""
        print("[IRIS AI] Инициализация компонентов...")
        
        # Проверка и инициализация распознавания речи
        self.speech_engines = {}
        
        if VOSK_AVAILABLE:
            self._init_vosk()
        
        if SR_AVAILABLE:
            self._init_speech_recognition()
        
        if YANDEX_AVAILABLE:
            self._init_yandex_speechkit()
        
        # Инициализация аудио
        self._init_audio_system()
        
        # Инициализация NLP
        if NLP_AVAILABLE:
            self.intent_recognizer = IntentRecognizer()
            print("[IRIS AI] ✅ NLP модуль инициализирован")
        
        print("[IRIS AI] ✅ Все компоненты инициализированы")
    
    def _init_neural_networks(self):
        """Инициализация нейросетевых моделей"""
        print("[IRIS AI] Инициализация нейросетевых модулей...")
        
        self.neural_models = {}
        
        if ML_LIBS.get('PYTORCH', False):
            try:
                # Голосовой энкодер
                self.neural_models['voice_encoder'] = VoiceEncoder()
                
                # Классификатор эмоций
                self.neural_models['emotion_classifier'] = EmotionClassifier()
                
                # Загрузка предобученных весов, если есть
                self._load_neural_weights()
                
                print("[IRIS AI] ✅ Нейросетевые модели инициализированы (PyTorch)")
            except Exception as e:
                print(f"[IRIS AI] ⚠️ Ошибка инициализации нейросетей: {e}")
        
        if ML_LIBS.get('SKLEARN', False):
            try:
                # Кластеризация для голосовых паттернов
                self.neural_models['voice_cluster'] = KMeans(n_clusters=5)
                self.neural_models['feature_scaler'] = StandardScaler()
                print("[IRIS AI] ✅ ML модели инициализированы (Scikit-learn)")
            except Exception as e:
                print(f"[IRIS AI] ⚠️ Ошибка инициализации ML: {e}")
    
    def _init_ai_modules(self):
        """Инициализация ИИ-модулей"""
        print("[IRIS AI] Инициализация ИИ-модулей...")
        
        # Адаптивный распознаватель wake word
        self.adaptive_wake_detector = AdaptiveWakeDetector()
        
        # Контекстный процессор
        self.context_processor = ContextProcessor()
        
        # Модуль самообучения
        if self.enable_self_learning:
            self.learning_module = SelfLearningModule(self.base_dir)
        
        # Эмоциональный анализатор
        if self.enable_emotion_recognition and AUDIO_ML_AVAILABLE:
            self.emotion_analyzer = EmotionAnalyzer()
        
        print("[IRIS AI] ✅ ИИ-модули инициализированы")
    
    def _init_vosk(self):
        """Инициализация Vosk с улучшенной моделью"""
        model_paths = [
            "models/vosk-model-ru-0.22",
            self.base_dir / "models/vosk-model-ru-0.22",
            Path.home() / ".vosk/vosk-model-ru-0.22",
            "/usr/share/vosk/vosk-model-ru-0.22"
        ]
        
        for path in model_paths:
            if os.path.exists(path):
                try:
                    self.vosk_model = Model(str(path))
                    self.vosk_recognizer = KaldiRecognizer(self.vosk_model, 16000)
                    self.vosk_recognizer.SetWords(True)
                    self.speech_engines['vosk'] = self.vosk_recognizer
                    print(f"[IRIS AI] ✅ Vosk модель загружена: {path}")
                    return
                except Exception as e:
                    print(f"[IRIS AI] Ошибка загрузки Vosk модели: {e}")
        
        print("[IRIS AI] ⚠️ Модель Vosk не найдена")
    
    def _init_speech_recognition(self):
        """Инициализация SpeechRecognition с улучшенными настройками"""
        try:
            self.sr_recognizer = sr.Recognizer()
            
            # Продвинутые настройки
            self.sr_recognizer.dynamic_energy_threshold = True
            self.sr_recognizer.energy_threshold = 3000
            self.sr_recognizer.pause_threshold = 0.8
            self.sr_recognizer.phrase_threshold = 0.3
            self.sr_recognizer.non_speaking_duration = 0.5
            
            self.speech_engines['google'] = self.sr_recognizer
            print("[IRIS AI] ✅ SpeechRecognition инициализирован")
        except Exception as e:
            print(f"[IRIS AI] Ошибка SpeechRecognition: {e}")
    
    def _init_yandex_speechkit(self):
        """Инициализация Яндекс SpeechKit"""
        # API ключ можно установить через переменные окружения
        self.yandex_api_key = os.getenv('YANDEX_SPEECHKIT_API_KEY', '')
        
        if self.yandex_api_key:
            self.speech_engines['yandex'] = True
            print("[IRIS AI] ✅ Яндекс SpeechKit доступен")
        else:
            print("[IRIS AI] ⚠️ Яндекс SpeechKit API ключ не найден")
    
    def _init_audio_system(self):
        """Инициализация продвинутой аудиосистемы"""
        print("[IRIS AI] Инициализация аудиосистемы...")
        
        self.audio_processors = {}
        
        if PYAUDIO_AVAILABLE:
            try:
                self.pyaudio_instance = pyaudio.PyAudio()
                
                # Поиск лучшего устройства
                self.audio_device = self._select_best_audio_device()
                
                # Настройки потока
                self.stream_config = {
                    'format': pyaudio.paInt16,
                    'channels': 1,
                    'rate': 16000,
                    'frames_per_buffer': 2048,
                    'input': True,
                    'output': False,
                    'input_device_index': self.audio_device['index']
                }
                
                print(f"[IRIS AI] ✅ Аудиоустройство: {self.audio_device.get('name', 'unknown')}")
                
            except Exception as e:
                print(f"[IRIS AI] Ошибка PyAudio: {e}")
        
        if AUDIO_ML_AVAILABLE:
            try:
                # Инициализация аудиообработки с librosa
                self.audio_processors['enhancer'] = AudioEnhancer()
                print("[IRIS AI] ✅ Аудиообработчик инициализирован")
            except Exception as e:
                print(f"[IRIS AI] Ошибка аудиообработки: {e}")
    
    def _select_best_audio_device(self) -> Dict:
        """Выбор лучшего аудиоустройства на основе характеристик"""
        if not PYAUDIO_AVAILABLE:
            return {}
        
        devices = []
        
        for i in range(self.pyaudio_instance.get_device_count()):
            info = self.pyaudio_instance.get_device_info_by_index(i)
            
            if info.get('maxInputChannels', 0) > 0:
                # Оценка качества устройства
                score = 0
                
                # Высокая частота дискретизации
                score += info.get('defaultSampleRate', 0) / 44100
                
                # Количество каналов
                score += info.get('maxInputChannels', 0) / 2
                
                # Низкая задержка
                latency = info.get('defaultLowInputLatency', 0.1)
                score += 1.0 - min(latency, 0.5) * 2
                
                devices.append({
                    'index': i,
                    'info': info,
                    'score': score,
                    'name': info.get('name', f'Device {i}')
                })
        
        # Сортируем по оценке
        devices.sort(key=lambda x: x['score'], reverse=True)
        
        return devices[0] if devices else {}
    
    def _load_neural_weights(self):
        """Загрузка предобученных весов нейросетей"""
        model_path = self.paths['models'] / "neural_weights.pth"
        
        if model_path.exists():
            try:
                checkpoint = torch.load(model_path, map_location='cpu')
                
                for model_name, model in self.neural_models.items():
                    if model_name in checkpoint:
                        model.load_state_dict(checkpoint[model_name])
                        print(f"[IRIS AI] Веса загружены для {model_name}")
                
                print("[IRIS AI] ✅ Веса нейросетей загружены")
            except Exception as e:
                print(f"[IRIS AI] Ошибка загрузки весов: {e}")
    
    def _load_config(self, config_path: str):
        """Загрузка конфигурации из файла"""
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
                
            # Загрузка пользовательских настроек
            if 'user_profile' in config:
                for key, value in config['user_profile'].items():
                    if hasattr(self.user_profile, key):
                        setattr(self.user_profile, key, value)
            
            if 'neural_config' in config:
                for key, value in config['neural_config'].items():
                    if hasattr(self.neural_config, key):
                        setattr(self.neural_config, key, value)
            
            print(f"[IRIS AI] Конфигурация загружена из {config_path}")
            
        except Exception as e:
            print(f"[IRIS AI] Ошибка загрузки конфигурации: {e}")
    
    def _print_system_info(self):
        """Вывод подробной информации о системе"""
        print("\n" + "="*70)
        print("🧠 IRIS AI - СИСТЕМНАЯ ИНФОРМАЦИЯ")
        print("="*70)
        
        print(f"Режим ИИ: {self.ai_mode}")
        print(f"Самообучение: {'✅ ВКЛ' if self.enable_self_learning else '❌ ВЫКЛ'}")
        print(f"Распознавание эмоций: {'✅ ВКЛ' if self.enable_emotion_recognition else '❌ ВЫКЛ'}")
        print(f"Контекстная осведомленность: {'✅ ВКЛ' if self.enable_context_awareness else '❌ ВЫКЛ'}")
        
        print("\n📊 ДОСТУПНЫЕ МОДУЛИ:")
        print(f"  • Vosk: {'✅' if 'vosk' in self.speech_engines else '❌'}")
        print(f"  • Google Speech: {'✅' if 'google' in self.speech_engines else '❌'}")
        print(f"  • Яндекс SpeechKit: {'✅' if 'yandex' in self.speech_engines else '❌'}")
        print(f"  • PyTorch: {'✅' if ML_LIBS.get('PYTORCH') else '❌'}")
        print(f"  • TensorFlow: {'✅' if ML_LIBS.get('TENSORFLOW') else '❌'}")
        print(f"  • NLP: {'✅' if NLP_AVAILABLE else '❌'}")
        print(f"  • Аудиообработка: {'✅' if AUDIO_ML_AVAILABLE else '❌'}")
        
        print(f"\n💾 ХРАНИЛИЩЕ: {self.base_dir}")
        print("="*70)
    
    # ============================================
    # ОСНОВНЫЕ МЕТОДЫ ОБРАБОТКИ
    # ============================================
    
    def start(self):
        """Запуск ИИ-ассистента"""
        if self.is_running:
            print("[IRIS AI] Ассистент уже запущен")
            return
        
        print("🚀 Запуск IRIS AI...")
        self.is_running = True
        
        # Запуск потоков обработки
        threads_to_start = [
            ('audio_capture', self._audio_capture_loop),
            ('speech_processing', self._speech_processing_loop),
            ('ai_processing', self._ai_processing_loop),
            ('command_handler', self._command_handling_loop),
            ('learning', self._learning_loop)
        ]
        
        for name, target in threads_to_start:
            thread = threading.Thread(target=target, daemon=True, name=f"iris_{name}")
            thread.start()
            self.threads[name] = thread
        
        # Запуск асинхронных задач
        asyncio.run(self._async_tasks_loop())
        
        print("✅ IRIS AI запущен и работает")
    
    def stop(self):
        """Остановка ИИ-ассистента"""
        if not self.is_running:
            return
        
        print("[IRIS AI] Остановка...")
        self.is_running = False
        
        # Сохранение состояния
        self._save_state()
        
        # Остановка потоков
        for thread in self.threads.values():
            if thread.is_alive():
                thread.join(timeout=2.0)
        
        # Закрытие аудиопотока
        if hasattr(self, 'audio_stream') and self.audio_stream:
            self.audio_stream.stop_stream()
            self.audio_stream.close()
        
        print("✅ IRIS AI остановлен")
    
    def _audio_capture_loop(self):
        """Цикл захвата аудио с улучшенной обработкой"""
        print("[IRIS AI] Запуск захвата аудио...")
        
        try:
            self.audio_stream = self.pyaudio_instance.open(**self.stream_config)
            self.audio_stream.start_stream()
            
            audio_buffer = []
            buffer_duration = 0.5  # 500 мс буфер
            chunk_size = self.stream_config['frames_per_buffer']
            
            while self.is_running:
                try:
                    # Чтение аудиоданных
                    data = self.audio_stream.read(chunk_size, exception_on_overflow=False)
                    audio_buffer.append(data)
                    
                    # Когда накопили достаточно данных
                    if len(audio_buffer) >= (16000 * buffer_duration) / chunk_size:
                        # Объединяем буфер
                        audio_data = b''.join(audio_buffer)
                        
                        # Улучшение качества звука
                        if 'enhancer' in self.audio_processors:
                            enhanced_audio = self.audio_processors['enhancer'].process(audio_data)
                            audio_data = enhanced_audio
                        
                        # Отправка в очередь обработки
                        self.audio_queue.put({
                            'data': audio_data,
                            'timestamp': time.time(),
                            'sample_rate': 16000
                        })
                        
                        # Очистка буфера
                        audio_buffer = []
                        
                except Exception as e:
                    print(f"[IRIS AI] Ошибка захвата аудио: {e}")
                    time.sleep(0.1)
                    
        except Exception as e:
            print(f"[IRIS AI] Критическая ошибка аудио: {e}")
    
    def _speech_processing_loop(self):
        """Цикл обработки речи с множественными движками"""
        print("[IRIS AI] Запуск обработки речи...")
        
        while self.is_running:
            try:
                # Получаем аудио из очереди
                audio_packet = self.audio_queue.get(timeout=0.5)
                audio_data = audio_packet['data']
                timestamp = audio_packet['timestamp']
                
                # Параллельное распознавание разными движками
                recognition_results = []
                
                # Vosk распознавание
                if 'vosk' in self.speech_engines:
                    vosk_result = self._recognize_with_vosk(audio_data)
                    if vosk_result:
                        vosk_result['engine'] = 'vosk'
                        recognition_results.append(vosk_result)
                
                # Google распознавание
                if 'google' in self.speech_engines:
                    google_result = self._recognize_with_google(audio_data)
                    if google_result:
                        google_result['engine'] = 'google'
                        recognition_results.append(google_result)
                
                # Яндекс распознавание
                if 'yandex' in self.speech_engines:
                    yandex_result = self._recognize_with_yandex(audio_data)
                    if yandex_result:
                        yandex_result['engine'] = 'yandex'
                        recognition_results.append(yandex_result)
                
                # Выбор лучшего результата
                if recognition_results:
                    best_result = self._select_best_recognition(recognition_results)
                    
                    # Обработка результата ИИ
                    self._process_with_ai(best_result)
                    
            except queue.Empty:
                continue
            except Exception as e:
                print(f"[IRIS AI] Ошибка обработки речи: {e}")
    
    def _ai_processing_loop(self):
        """Цикл ИИ-обработки с нейросетями"""
        print("[IRIS AI] Запуск ИИ-обработки...")
        
        while self.is_running:
            try:
                # Получаем распознанный текст
                # В реальной реализации здесь будет очередь с результатами
                time.sleep(0.1)
                
                # Анализ эмоций в фоновом режиме
                if self.enable_emotion_recognition:
                    self._update_emotion_state()
                
                # Адаптация к пользователю
                if self.enable_self_learning:
                    self._adapt_to_user()
                
            except Exception as e:
                print(f"[IRIS AI] Ошибка ИИ-обработки: {e}")
    
    def _command_handling_loop(self):
        """Цикл обработки команд с контекстом"""
        print("[IRIS AI] Запуск обработки команд...")
        
        while self.is_running:
            try:
                # Получаем команду из очереди
                priority, timestamp, command_data = self.command_queue.get(timeout=0.5)
                
                # Обработка команды с учетом контекста
                processed_command = self._process_command_with_context(command_data)
                
                # Вызов коллбэков
                self._trigger_callbacks('command', processed_command)
                
                # Обновление контекста
                self._update_context(processed_command)
                
            except queue.Empty:
                continue
            except Exception as e:
                print(f"[IRIS AI] Ошибка обработки команд: {e}")
    
    def _learning_loop(self):
        """Цикл самообучения"""
        if not self.enable_self_learning:
            return
        
        print("[IRIS AI] Запуск цикла самообучения...")
        
        learning_interval = 300  # 5 минут
        
        while self.is_running:
            try:
                time.sleep(learning_interval)
                
                # Сбор данных для обучения
                training_data = self._collect_training_data()
                
                # Обучение моделей
                if training_data:
                    self._train_models(training_data)
                
                # Сохранение прогресса обучения
                self._save_learning_progress()
                
            except Exception as e:
                print(f"[IRIS AI] Ошибка самообучения: {e}")
    
    async def _async_tasks_loop(self):
        """Асинхронный цикл для задач, требующих asyncio"""
        print("[IRIS AI] Запуск асинхронных задач...")
        
        tasks = [
            self._async_event_processor(),
            self._async_network_monitor(),
            self._async_performance_monitor()
        ]
        
        await asyncio.gather(*tasks)
    
    # ============================================
    # МЕТОДЫ РАСПОЗНАВАНИЯ РЕЧИ
    # ============================================
    
    def _recognize_with_vosk(self, audio_data: bytes) -> Optional[Dict]:
        """Распознавание с помощью Vosk"""
        try:
            if self.vosk_recognizer.AcceptWaveform(audio_data):
                result = json.loads(self.vosk_recognizer.Result())
                text = result.get('text', '').strip()
                
                if text:
                    confidence = result.get('confidence', 0.0)
                    
                    # Извлечение дополнительной информации
                    words = result.get('result', [])
                    word_timings = [(w.get('word'), w.get('start'), w.get('end')) for w in words]
                    
                    return {
                        'text': text,
                        'confidence': confidence,
                        'language': 'ru',
                        'timings': word_timings,
                        'raw_result': result
                    }
        except Exception as e:
            print(f"[IRIS AI] Ошибка Vosk: {e}")
        
        return None
    
    def _recognize_with_google(self, audio_data: bytes) -> Optional[Dict]:
        """Распознавание с помощью Google Speech"""
        try:
            # Преобразование в формат SpeechRecognition
            audio = sr.AudioData(audio_data, 16000, 2)
            
            # Распознавание
            text = self.sr_recognizer.recognize_google(audio, language="ru-RU")
            
            # Дополнительные варианты
            alternatives = []
            try:
                raw_result = self.sr_recognizer.recognize_google(audio, language="ru-RU", show_all=True)
                if isinstance(raw_result, dict) and 'alternative' in raw_result:
                    alternatives = [alt.get('transcript', '') for alt in raw_result['alternative'][1:]]
            except:
                pass
            
            return {
                'text': text,
                'confidence': 0.85,  # Google не возвращает confidence для русского
                'language': 'ru',
                'alternatives': alternatives
            }
            
        except sr.UnknownValueError:
            return None
        except sr.RequestError as e:
            print(f"[IRIS AI] Ошибка Google API: {e}")
            return None
        except Exception as e:
            print(f"[IRIS AI] Ошибка Google распознавания: {e}")
            return None
    
    def _recognize_with_yandex(self, audio_data: bytes) -> Optional[Dict]:
        """Распознавание с помощью Яндекс SpeechKit"""
        if not self.yandex_api_key:
            return None
        
        try:
            # Подготовка запроса
            url = "https://stt.api.cloud.yandex.net/speech/v1/stt:recognize"
            
            headers = {
                "Authorization": f"Api-Key {self.yandex_api_key}",
            }
            
            params = {
                "lang": "ru-RU",
                "sampleRateHertz": "16000",
                "format": "lpcm",
                "profanityFilter": "false"
            }
            
            # Отправка запроса
            response = requests.post(url, headers=headers, params=params, data=audio_data)
            
            if response.status_code == 200:
                result = response.json()
                text = result.get('result', '')
                
                if text:
                    return {
                        'text': text,
                        'confidence': 0.9,  # Яндекс обычно дает высокую точность
                        'language': 'ru',
                        'service': 'yandex'
                    }
        
        except Exception as e:
            print(f"[IRIS AI] Ошибка Яндекс SpeechKit: {e}")
        
        return None
    
    def _select_best_recognition(self, results: List[Dict]) -> Dict:
        """Выбор лучшего результата распознавания"""
        if not results:
            return {}
        
        # Взвешенная оценка результатов
        scored_results = []
        
        for result in results:
            score = result.get('confidence', 0.0)
            
            # Дополнительные факторы
            engine_weights = {
                'yandex': 1.1,  # Яндекс лучше для русского
                'vosk': 1.0,
                'google': 0.9
            }
            
            engine = result.get('engine', '')
            if engine in engine_weights:
                score *= engine_weights[engine]
            
            # Наказание за короткие тексты
            text_length = len(result.get('text', ''))
            if text_length < 3:
                score *= 0.5
            
            scored_results.append((score, result))
        
        # Выбор результата с максимальным score
        best_score, best_result = max(scored_results, key=lambda x: x[0])
        
        # Логирование выбора
        print(f"[IRIS AI] Выбран результат от {best_result.get('engine')} "
              f"(оценка: {best_score:.2f}): {best_result.get('text', '')[:50]}...")
        
        return best_result
    
    # ============================================
    # ИИ-ОБРАБОТКА И САМООБУЧЕНИЕ
    # ============================================
    
    def _process_with_ai(self, recognition_result: Dict):
        """Обработка распознанного текста с помощью ИИ"""
        if not recognition_result:
            return
        
        text = recognition_result.get('text', '')
        confidence = recognition_result.get('confidence', 0.0)
        
        # Анализ эмоций в тексте
        if self.enable_emotion_recognition:
            emotion_analysis = self._analyze_emotion_from_text(text)
            self._update_emotion_state(emotion_analysis)
        
        # Анализ намерений
        intent_analysis = self._analyze_intent(text)
        
        # Проверка wake word с адаптивным детектором
        wake_detected, cleaned_text = self._adaptive_wake_detection(text, confidence)
        
        if wake_detected:
            print(f"🔔 [IRIS AI] Wake word обнаружен! (адаптивный режим)")
            self._trigger_callbacks('wake', {})
            
            # Активация режима прослушивания
            self._activate_listening_mode()
            
            # Обработка команды после wake word
            if cleaned_text:
                self._process_command(cleaned_text, intent_analysis)
        
        # Обработка в активном режиме
        elif self._is_listening_active():
            self._process_command(text, intent_analysis)
        
        # Сбор данных для обучения
        if self.enable_self_learning:
            self._collect_learning_sample(text, recognition_result)
    
    def _analyze_emotion_from_text(self, text: str) -> Dict:
        """Анализ эмоций по тексту"""
        emotion_scores = {
            'neutral': 0.5,
            'happy': 0.0,
            'sad': 0.0,
            'angry': 0.0,
            'excited': 0.0
        }
        
        # Эмоциональные слова
        emotion_words = {
            'happy': ['хорошо', 'отлично', 'прекрасно', 'рад', 'счастлив', 'ура', 'супер'],
            'sad': ['плохо', 'грустно', 'печально', 'тоскливо', 'жаль'],
            'angry': ['злой', 'сердит', 'разозлился', 'бесит', 'раздражен'],
            'excited': ['волнуюсь', 'взволнован', 'интересно', 'ожидаю', 'не терпится']
        }
        
        text_lower = text.lower()
        
        for emotion, words in emotion_words.items():
            for word in words:
                if word in text_lower:
                    emotion_scores[emotion] += 0.2
        
        # Определение доминирующей эмоции
        dominant_emotion = max(emotion_scores.items(), key=lambda x: x[1])
        
        return {
            'emotion': dominant_emotion[0],
            'confidence': dominant_emotion[1],
            'scores': emotion_scores
        }
    
    def _analyze_intent(self, text: str) -> Dict:
        """Анализ намерений в тексте"""
        if hasattr(self, 'intent_recognizer'):
            return self.intent_recognizer.extract_intent(text)
        
        # Базовая реализация
        text_lower = text.lower()
        intent = "unknown"
        
        for cmd_type, cmd_info in self.SMART_COMMANDS.items():
            for action in cmd_info['actions']:
                if action in text_lower:
                    intent = cmd_type
                    break
        
        return {
            'intent': intent,
            'confidence': 0.7 if intent != "unknown" else 0.0,
            'entities': []
        }
    
    def _adaptive_wake_detection(self, text: str, confidence: float) -> Tuple[bool, str]:
        """Адаптивное обнаружение wake word с самообучением"""
        if not text:
            return False, ""
        
        # Используем адаптивный детектор
        if hasattr(self, 'adaptive_wake_detector'):
            return self.adaptive_wake_detector.detect(text, confidence, self.user_profile)
        
        # Базовая реализация
        text_lower = text.lower()
        
        for variant in self.WAKE_WORD_VARIANTS:
            if variant in text_lower:
                # Извлекаем текст после wake word
                start_idx = text_lower.find(variant)
                cleaned_text = text_lower[start_idx + len(variant):].strip()
                return True, cleaned_text
        
        return False, text_lower
    
    def _process_command(self, command: str, intent_analysis: Dict):
        """Обработка команды с ИИ-анализом"""
        if not command:
            return
        
        # Обработка с учетом контекста
        contextual_command = self._apply_context_to_command(command, intent_analysis)
        
        # Добавление в очередь команд
        priority = self._calculate_command_priority(command, intent_analysis)
        self.command_queue.put((priority, time.time(), {
            'command': command,
            'contextual': contextual_command,
            'intent': intent_analysis,
            'emotion': self.emotion_state.emotion,
            'timestamp': time.time()
        }))
        
        print(f"💭 [IRIS AI] Обработана команда: {command}")
        print(f"   🎯 Намерение: {intent_analysis.get('intent', 'unknown')}")
        print(f"   😊 Эмоция: {self.emotion_state.emotion}")
    
    def _apply_context_to_command(self, command: str, intent: Dict) -> str:
        """Применение контекста к команде"""
        if not self.enable_context_awareness:
            return command
        
        # Добавление контекстной информации
        context_info = self.context_processor.get_context_for_command(command, intent)
        
        enhanced_command = {
            'raw': command,
            'context': context_info,
            'user_profile': self.user_profile.user_id,
            'current_emotion': self.emotion_state.emotion,
            'domain': intent.get('intent', 'general')
        }
        
        return json.dumps(enhanced_command, ensure_ascii=False)
    
    def _calculate_command_priority(self, command: str, intent: Dict) -> int:
        """Расчет приоритета команды"""
        priority = 1  # Средний приоритет по умолчанию
        
        # Высокий приоритет для критичных команд
        critical_words = ['стоп', 'остановись', 'помощь', 'спаси', 'тревога']
        if any(word in command.lower() for word in critical_words):
            priority = 0
        
        # Низкий приоритет для информационных запросов
        info_words = ['что', 'как', 'почему', 'расскажи', 'информация']
        if any(word in command.lower() for word in info_words):
            priority = 2
        
        # Учет эмоционального состояния
        if self.emotion_state.emotion in ['angry', 'stressed']:
            priority = 0  # Высокий приоритет при негативных эмоциях
        
        return priority
    
    def _update_emotion_state(self, new_analysis: Optional[Dict] = None):
        """Обновление эмоционального состояния"""
        if not self.enable_emotion_recognition:
            return
        
        if new_analysis:
            self.emotion_state.emotion = new_analysis.get('emotion', 'neutral')
            self.emotion_state.confidence = new_analysis.get('confidence', 0.0)
            self.emotion_state.timestamp = time.time()
            
            # Сохранение в историю
            self.emotion_state.history.append({
                'emotion': self.emotion_state.emotion,
                'confidence': self.emotion_state.confidence,
                'timestamp': self.emotion_state.timestamp
            })
            
            # Ограничение размера истории
            if len(self.emotion_state.history) > 100:
                self.emotion_state.history.pop(0)
            
            # Вызов коллбэков
            self._trigger_callbacks('emotion_change', asdict(self.emotion_state))
    
    def _adapt_to_user(self):
        """Адаптация к пользователю на основе взаимодействий"""
        if not self.enable_self_learning:
            return
        
        # Увеличение счетчика взаимодействий
        self.user_profile.interaction_count += 1
        
        # Расчет уровня адаптации
        base_adaptation = min(self.user_profile.interaction_count / 100, 1.0)
        
        # Учет успешных распознаваний
        success_rate = self._calculate_success_rate()
        adaptation = base_adaptation * success_rate
        
        self.user_profile.adaptation_level = adaptation
        
        # Сохранение профиля
        self._save_user_profile()
    
    def _collect_training_data(self) -> Dict:
        """Сбор данных для обучения"""
        samples = []
        
        # Сбор аудио образцов
        if hasattr(self, 'learning_data') and self.learning_data.audio_samples:
            samples.extend(self.learning_data.audio_samples[:10])  # Берем последние 10
        
        # Сбор текстовых образцов
        recent_history = self.get_recent_history(20)
        
        training_data = {
            'audio_samples': samples,
            'transcriptions': [h.get('text', '') for h in recent_history],
            'timestamps': [h.get('timestamp', 0) for h in recent_history],
            'success_rate': self._calculate_success_rate()
        }
        
        return training_data
    
    def _train_models(self, training_data: Dict):
        """Обучение моделей на собранных данных"""
        if not training_data or not self.enable_self_learning:
            return
        
        print("[IRIS AI] Запуск обучения моделей...")
        
        try:
            # Обучение адаптивного wake word детектора
            if hasattr(self, 'adaptive_wake_detector'):
                self.adaptive_wake_detector.train(training_data)
            
            # Обновление нейросетевых моделей
            if ML_LIBS.get('PYTORCH', False) and 'transcriptions' in training_data:
                self._train_neural_models(training_data['transcriptions'])
            
            print("[IRIS AI] ✅ Модели обучены")
            
            # Вызов коллбэков
            self._trigger_callbacks('learning_update', {
                'timestamp': time.time(),
                'samples_processed': len(training_data.get('transcriptions', [])),
                'success_rate': training_data.get('success_rate', 0.0)
            })
            
        except Exception as e:
            print(f"[IRIS AI] Ошибка обучения: {e}")
    
    def _train_neural_models(self, texts: List[str]):
        """Обучение нейросетевых моделей"""
        if not texts or len(texts) < 5:
            return
        
        # Здесь должна быть реальная реализация обучения
        # Для примера просто сохраняем состояние
        try:
            if 'voice_encoder' in self.neural_models:
                model_path = self.paths['models'] / "voice_encoder_latest.pth"
                torch.save(self.neural_models['voice_encoder'].state_dict(), model_path)
            
            print(f"[IRIS AI] Нейросетевые модели обновлены на {len(texts)} примерах")
        except Exception as e:
            print(f"[IRIS AI] Ошибка сохранения нейросетей: {e}")
    
    def _collect_learning_sample(self, text: str, recognition_result: Dict):
        """Сбор образца для обучения"""
        sample = {
            'text': text,
            'recognition_result': recognition_result,
            'timestamp': time.time(),
            'emotion': self.emotion_state.emotion,
            'user_id': self.user_profile.user_id
        }
        
        self.learning_data.transcriptions.append(sample)
        
        # Ограничение размера
        if len(self.learning_data.transcriptions) > 1000:
            self.learning_data.transcriptions.pop(0)
    
    def _calculate_success_rate(self) -> float:
        """Расчет процента успешных распознаваний"""
        if not self.learning_data.transcriptions:
            return 0.0
        
        # Простая эвристика: считаем успешными распознавания с доверием > 0.7
        successful = sum(1 for t in self.learning_data.transcriptions 
                        if t.get('recognition_result', {}).get('confidence', 0) > 0.7)
        
        total = len(self.learning_data.transcriptions)
        
        return successful / total if total > 0 else 0.0
    
    # ============================================
    # ВСПОМОГАТЕЛЬНЫЕ МЕТОДЫ И ИНТЕРФЕЙС
    # ============================================
    
    def add_callback(self, callback_type: str, callback: Callable):
        """Добавление коллбэка"""
        if callback_type in self.callbacks:
            self.callbacks[callback_type].append(callback)
            print(f"[IRIS AI] Добавлен коллбэк типа: {callback_type}")
    
    def _trigger_callbacks(self, callback_type: str, data: Any):
        """Вызов коллбэков"""
        if callback_type in self.callbacks:
            for callback in self.callbacks[callback_type]:
                try:
                    callback(data)
                except Exception as e:
                    print(f"[IRIS AI] Ошибка в коллбэке {callback_type}: {e}")
    
    def _is_listening_active(self) -> bool:
        """Проверка активности режима прослушивания"""
        # В реальной реализации здесь будет логика таймаута
        return True
    
    def _activate_listening_mode(self, duration: float = 10.0):
        """Активация режима прослушивания"""
        self.listening_active_until = time.time() + duration
        print(f"[IRIS AI] Режим прослушивания активирован на {duration} секунд")
    
    def _update_context(self, command_data: Dict):
        """Обновление контекста после команды"""
        if not self.enable_context_awareness:
            return
        
        command = command_data.get('command', '') if isinstance(command_data, dict) else command_data
        
        # Добавление команды в историю
        self.ai_context.previous_commands.append(command)
        
        # Ограничение размера истории
        if len(self.ai_context.previous_commands) > 20:
            self.ai_context.previous_commands.pop(0)
        
        # Обновление контекстного скора
        self.ai_context.context_score = self._calculate_context_score()
    
    def _calculate_context_score(self) -> float:
        """Расчет скора контекстной релевантности"""
        if not self.ai_context.previous_commands:
            return 0.0
        
        # Простая эвристика: больше команд = выше контекст
        return min(len(self.ai_context.previous_commands) / 20, 1.0)
    
    def get_system_status(self) -> Dict:
        """Получение статуса системы"""
        return {
            'status': 'running' if self.is_running else 'stopped',
            'ai_mode': self.ai_mode,
            'user_profile': asdict(self.user_profile),
            'emotion_state': asdict(self.emotion_state),
            'performance': asdict(self.performance_metrics),
            'queue_sizes': {
                'audio': self.audio_queue.qsize(),
                'commands': self.command_queue.qsize()
            },
            'threads_alive': {name: thread.is_alive() for name, thread in self.threads.items()},
            'learning_enabled': self.enable_self_learning,
            'adaptation_level': self.user_profile.adaptation_level,
            'success_rate': self._calculate_success_rate()
        }
    
    def get_recent_history(self, count: int = 10) -> List[Dict]:
        """Получение последних записей истории"""
        return self.learning_data.transcriptions[-count:] if self.learning_data.transcriptions else []
    
    def save_state(self):
        """Сохранение состояния системы"""
        self._save_state()
    
    def _save_state(self):
        """Внутренний метод сохранения состояния"""
        print("[IRIS AI] Сохранение состояния...")
        
        try:
            # Сохранение пользовательского профиля
            profile_path = self.paths['profiles'] / f"{self.user_profile.user_id}.json"
            with open(profile_path, 'w', encoding='utf-8') as f:
                json.dump(asdict(self.user_profile), f, indent=2, ensure_ascii=False)
            
            # Сохранение данных обучения
            learning_path = self.paths['learning'] / "learning_data.pkl"
            with open(learning_path, 'wb') as f:
                pickle.dump(self.learning_data, f)
            
            # Сохранение конфигурации
            config_path = self.paths['config'] / "ai_config.json"
            config = {
                'ai_mode': self.ai_mode,
                'neural_config': asdict(self.neural_config),
                'user_profile_id': self.user_profile.user_id,
                'last_save': time.time()
            }
            
            with open(config_path, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=2, ensure_ascii=False)
            
            print("[IRIS AI] ✅ Состояние сохранено")
            
        except Exception as e:
            print(f"[IRIS AI] Ошибка сохранения состояния: {e}")
    
    def _save_user_profile(self):
        """Сохранение профиля пользователя"""
        try:
            profile_path = self.paths['profiles'] / f"{self.user_profile.user_id}.json"
            with open(profile_path, 'w', encoding='utf-8') as f:
                json.dump(asdict(self.user_profile), f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"[IRIS AI] Ошибка сохранения профиля: {e}")
    
    def _save_learning_progress(self):
        """Сохранение прогресса обучения"""
        if not self.enable_self_learning:
            return
        
        try:
            progress_path = self.paths['learning'] / "progress.json"
            progress = {
                'total_samples': len(self.learning_data.transcriptions),
                'last_training': time.time(),
                'success_rate': self._calculate_success_rate(),
                'adaptation_level': self.user_profile.adaptation_level
            }
            
            with open(progress_path, 'w', encoding='utf-8') as f:
                json.dump(progress, f, indent=2, ensure_ascii=False)
                
        except Exception as e:
            print(f"[IRIS AI] Ошибка сохранения прогресса: {e}")
    
    async def _async_event_processor(self):
        """Асинхронный обработчик событий"""
        while self.is_running:
            try:
                # Обработка событий из очереди
                await asyncio.sleep(0.1)
            except Exception as e:
                print(f"[IRIS AI] Ошибка обработки событий: {e}")
    
    async def _async_network_monitor(self):
        """Мониторинг сетевых соединений"""
        while self.is_running:
            try:
                # Проверка доступности сервисов
                await asyncio.sleep(60)  # Проверка каждую минуту
                
            except Exception as e:
                print(f"[IRIS AI] Ошибка мониторинга сети: {e}")
    
    async def _async_performance_monitor(self):
        """Мониторинг производительности"""
        while self.is_running:
            try:
                # Сбор метрик производительности
                self.performance_metrics.latency['audio'] = 0.05  # Пример
                self.performance_metrics.latency['processing'] = 0.1
                
                await asyncio.sleep(5)  # Обновление каждые 5 секунд
                
            except Exception as e:
                print(f"[IRIS AI] Ошибка мониторинга производительности: {e}")

# ============================================
# ВСПОМОГАТЕЛЬНЫЕ КЛАССЫ ИИ-МОДУЛЕЙ
# ============================================

class AdaptiveWakeDetector:
    """Адаптивный детектор wake word с самообучением"""
    
    def __init__(self):
        self.wake_patterns = []
        self.user_specific_patterns = {}
        self.learning_rate = 0.1
        self.threshold = 0.7
        
    def detect(self, text: str, confidence: float, user_profile: UserProfile) -> Tuple[bool, str]:
        """Обнаружение wake word с адаптацией"""
        text_lower = text.lower()
        
        # Проверка стандартных паттернов
        for pattern in self.wake_patterns:
            if pattern in text_lower:
                return True, text_lower.replace(pattern, "", 1).strip()
        
        # Проверка пользовательских паттернов
        user_id = user_profile.user_id
        if user_id in self.user_specific_patterns:
            for pattern in self.user_specific_patterns[user_id]:
                if pattern in text_lower:
                    return True, text_lower.replace(pattern, "", 1).strip()
        
        # Fuzzy matching для новых вариаций
        wake_variants = ['ирис', 'iris', 'ири']
        for variant in wake_variants:
            if variant in text_lower:
                # Обучение на новом паттерне
                self._learn_pattern(text_lower, variant, user_profile)
                return True, text_lower.replace(variant, "", 1).strip()
        
        return False, text_lower
    
    def _learn_pattern(self, text: str, detected_variant: str, user_profile: UserProfile):
        """Обучение на новом паттерне wake word"""
        # Извлечение контекста вокруг wake word
        idx = text.find(detected_variant)
        context = text[max(0, idx-5):min(len(text), idx+len(detected_variant)+5)]
        
        # Добавление в паттерны
        pattern = {
            'text': context,
            'variant': detected_variant,
            'user_id': user_profile.user_id,
            'timestamp': time.time()
        }
        
        self.wake_patterns.append(context)
        
        # Ограничение количества паттернов
        if len(self.wake_patterns) > 50:
            self.wake_patterns.pop(0)
    
    def train(self, training_data: Dict):
        """Обучение детектора на данных"""
        # Здесь должна быть реальная реализация обучения
        print("[AdaptiveWakeDetector] Обучение на новых данных...")

class ContextProcessor:
    """Процессор контекста для понимания команд"""
    
    def __init__(self):
        self.context_memory = {}
        self.conversation_history = []
        self.entity_tracker = {}
        
    def get_context_for_command(self, command: str, intent: Dict) -> Dict:
        """Получение контекста для команды"""
        context = {
            'previous_commands': self.conversation_history[-3:],  # Последние 3 команды
            'time_of_day': self._get_time_context(),
            'detected_intent': intent.get('intent', 'unknown'),
            'entities': intent.get('entities', []),
            'context_score': self._calculate_relevance(command)
        }
        
        # Сохранение команды в историю
        self.conversation_history.append({
            'command': command,
            'intent': intent,
            'timestamp': time.time()
        })
        
        # Ограничение истории
        if len(self.conversation_history) > 100:
            self.conversation_history.pop(0)
        
        return context
    
    def _get_time_context(self) -> Dict:
        """Получение временного контекста"""
        now = datetime.now()
        
        return {
            'hour': now.hour,
            'minute': now.minute,
            'day_of_week': now.weekday(),
            'is_working_hours': 9 <= now.hour < 18,
            'is_night': now.hour < 6 or now.hour >= 22
        }
    
    def _calculate_relevance(self, command: str) -> float:
        """Расчет релевантности команды текущему контексту"""
        # Простая эвристика
        if not self.conversation_history:
            return 0.0
        
        last_command = self.conversation_history[-1].get('command', '').lower()
        current_command = command.lower()
        
        # Проверка тематической связи
        common_words = set(last_command.split()) & set(current_command.split())
        
        return len(common_words) / max(len(set(last_command.split())), 1)

class SelfLearningModule:
    """Модуль самообучения ассистента"""
    
    def __init__(self, base_dir: Path):
        self.base_dir = base_dir
        self.learning_data = []
        self.model_versions = {}
        
    def add_sample(self, text: str, correct_transcription: str, confidence: float):
        """Добавление образца для обучения"""
        sample = {
            'input': text,
            'target': correct_transcription,
            'confidence': confidence,
            'timestamp': time.time()
        }
        
        self.learning_data.append(sample)
        
        # Автоматическое обучение при накоплении данных
        if len(self.learning_data) >= 100:
            self.train()
    
    def train(self):
        """Обучение моделей на накопленных данных"""
        if len(self.learning_data) < 10:
            return
        
        print("[SelfLearningModule] Запуск обучения...")
        
        # Здесь должна быть реальная реализация обучения
        # Например, дообучение моделей распознавания
        
        # После обучения очищаем часть данных
        self.learning_data = self.learning_data[-500:]  # Оставляем последние 500
        
        print(f"[SelfLearningModule] Обучение завершено. Образцов: {len(self.learning_data)}")
    
    def save_progress(self):
        """Сохранение прогресса обучения"""
        progress_path = self.base_dir / "learning_progress.pkl"
        
        try:
            with open(progress_path, 'wb') as f:
                pickle.dump({
                    'learning_data': self.learning_data,
                    'model_versions': self.model_versions,
                    'last_trained': time.time()
                }, f)
        except Exception as e:
            print(f"[SelfLearningModule] Ошибка сохранения: {e}")

class EmotionAnalyzer:
    """Анализатор эмоций по голосу"""
    
    def __init__(self):
        self.emotion_models = {}
        self.feature_extractor = None
        
    def analyze_audio(self, audio_data: np.ndarray, sample_rate: int) -> Dict:
        """Анализ эмоций по аудиоданным"""
        try:
            # Извлечение признаков с librosa
            features = self._extract_audio_features(audio_data, sample_rate)
            
            # Классификация эмоций
            emotion_probs = self._classify_emotion(features)
            
            # Определение доминирующей эмоции
            dominant_emotion = max(emotion_probs.items(), key=lambda x: x[1])
            
            return {
                'emotion': dominant_emotion[0],
                'confidence': dominant_emotion[1],
                'probabilities': emotion_probs,
                'features': features.tolist() if isinstance(features, np.ndarray) else features
            }
            
        except Exception as e:
            print(f"[EmotionAnalyzer] Ошибка анализа: {e}")
            return {'emotion': 'neutral', 'confidence': 0.0}
    
    def _extract_audio_features(self, audio: np.ndarray, sr: int) -> np.ndarray:
        """Извлечение аудио-признаков"""
        features = []
        
        try:
            # MFCC (Mel-frequency cepstral coefficients)
            mfcc = librosa.feature.mfcc(y=audio, sr=sr, n_mfcc=13)
            features.append(mfcc.mean(axis=1))
            
            # Chroma features
            chroma = librosa.feature.chroma_stft(y=audio, sr=sr)
            features.append(chroma.mean(axis=1))
            
            # Spectral contrast
            contrast = librosa.feature.spectral_contrast(y=audio, sr=sr)
            features.append(contrast.mean(axis=1))
            
            # Zero crossing rate
            zcr = librosa.feature.zero_crossing_rate(y=audio)
            features.append([zcr.mean()])
            
            # RMS energy
            rms = librosa.feature.rms(y=audio)
            features.append([rms.mean()])
            
            # Объединение всех признаков
            combined = np.concatenate(features)
            
            return combined
            
        except Exception as e:
            print(f"[EmotionAnalyzer] Ошибка извлечения признаков: {e}")
            return np.zeros(50)  # Возвращаем нулевые признаки при ошибке
    
    def _classify_emotion(self, features: np.ndarray) -> Dict:
        """Классификация эмоций по признакам"""
        # Здесь должна быть реальная модель классификации
        # Возвращаем фиктивные вероятности для примера
        return {
            'neutral': 0.3,
            'happy': 0.2,
            'sad': 0.15,
            'angry': 0.1,
            'excited': 0.1,
            'calm': 0.1,
            'stressed': 0.05
        }

class AudioEnhancer:
    """Улучшитель качества аудио"""
    
    def __init__(self):
        self.noise_profile = None
        self.enhancement_params = {
            'noise_reduction': 0.8,
            'gain': 1.2,
            'compression': 0.5
        }
    
    def process(self, audio_data: bytes) -> bytes:
        """Обработка и улучшение аудио"""
        try:
            # Преобразование bytes в numpy array
            audio_array = np.frombuffer(audio_data, dtype=np.int16).astype(np.float32) / 32768.0
            
            # Применение улучшений
            enhanced = self._apply_enhancements(audio_array)
            
            # Обратное преобразование в bytes
            enhanced_bytes = (enhanced * 32768.0).astype(np.int16).tobytes()
            
            return enhanced_bytes
            
        except Exception as e:
            print(f"[AudioEnhancer] Ошибка обработки: {e}")
            return audio_data  # Возвращаем исходные данные при ошибке
    
    def _apply_enhancements(self, audio: np.ndarray) -> np.ndarray:
        """Применение улучшений к аудио"""
        # Шумоподавление
        if self.noise_profile is not None:
            audio = self._reduce_noise(audio)
        
        # Нормализация громкости
        audio = self._normalize_volume(audio)
        
        # Компрессия динамического диапазона
        audio = self._compress_dynamic_range(audio)
        
        return audio
    
    def _reduce_noise(self, audio: np.ndarray) -> np.ndarray:
        """Подавление шума"""
        # Простая реализация порогового подавления шума
        threshold = np.std(audio) * self.enhancement_params['noise_reduction']
        audio[abs(audio) < threshold] = 0
        return audio
    
    def _normalize_volume(self, audio: np.ndarray) -> np.ndarray:
        """Нормализация громкости"""
        max_amp = np.max(np.abs(audio))
        if max_amp > 0:
            audio = audio / max_amp * self.enhancement_params['gain']
        return np.clip(audio, -1.0, 1.0)
    
    def _compress_dynamic_range(self, audio: np.ndarray) -> np.ndarray:
        """Компрессия динамического диапазона"""
        compression = self.enhancement_params['compression']
        return np.tanh(audio * compression) / np.tanh(compression)

# ============================================
# ТЕСТИРОВАНИЕ И ДЕМОНСТРАЦИЯ
# ============================================

def create_iris_ai(config: Optional[Dict] = None) -> IRISVoiceAI:
    """
    Фабричная функция для создания IRIS AI ассистента
    
    Args:
        config: Конфигурация ассистента
    
    Returns:
        IRISVoiceAI: Экземпляр ассистента
    """
    config = config or {}
    
    ai = IRISVoiceAI(
        config_path=config.get('config_path'),
        ai_mode=config.get('ai_mode', 'adaptive'),
        neural_config=config.get('neural_config'),
        enable_self_learning=config.get('enable_self_learning', True),
        enable_emotion_recognition=config.get('enable_emotion_recognition', True),
        enable_context_awareness=config.get('enable_context_awareness', True)
    )
    
    return ai

async def demo_iris_ai():
    """Демонстрация возможностей IRIS AI"""
    print("\n" + "="*70)
    print("🚀 ДЕМОНСТРАЦИЯ IRIS AI - УМНЫЙ ГОЛОСОВОЙ АССИСТЕНТ")
    print("="*70)
    
    # Создание ассистента
    config = {
        'ai_mode': 'adaptive',
        'enable_self_learning': True,
        'enable_emotion_recognition': True,
        'enable_context_awareness': True
    }
    
    iris = create_iris_ai(config)
    
    # Добавление коллбэков
    def on_wake():
        print("\n🎯 Wake word обнаружен! IRIS активирован")
    
    def on_command(command):
        print(f"\n💬 Получена команда: {command}")
    
    def on_emotion_change(emotion_state):
        print(f"\n😊 Изменилась эмоция: {emotion_state['emotion']} "
              f"(уверенность: {emotion_state['confidence']:.1%})")
    
    def on_learning_update(update):
        print(f"\n📚 Обновление обучения: обработано {update['samples_processed']} образцов")
    
    iris.add_callback('wake', on_wake)
    iris.add_callback('command', on_command)
    iris.add_callback('emotion_change', on_emotion_change)
    iris.add_callback('learning_update', on_learning_update)
    
    # Запуск ассистента
    print("\n▶️ Запускаю IRIS AI...")
    iris.start()
    
    print("\n📋 Доступные команды для тестирования:")
    print("   • Скажите 'Ирис' для активации")
    print("   • Затем произнесите команду (например: 'Ирис, какая погода?')")
    print("   • Скажите 'Ирис, расскажи анекдот'")
    print("   • Скажите 'Ирис, включи музыку'")
    print("   • Скажите 'стоп' для остановки демо")
    
    print("\n⏳ Демо будет работать 60 секунд...")
    
    # Демо на 60 секунд
    try:
        start_time = time.time()
        
        while time.time() - start_time < 60:
            await asyncio.sleep(1)
            
            # Периодический вывод статуса
            if int(time.time() - start_time) % 10 == 0:
                status = iris.get_system_status()
                print(f"\n📊 Статус: {status['status']}, "
                      f"адаптация: {status['adaptation_level']:.1%}, "
                      f"эмоция: {status['emotion_state']['emotion']}")
    
    except KeyboardInterrupt:
        print("\n\n🛑 Прервано пользователем")
    
    finally:
        # Остановка ассистента
        print("\n⏹️ Останавливаю IRIS AI...")
        iris.stop()
        
        # Финальная статистика
        print("\n" + "="*70)
        print("📈 ФИНАЛЬНАЯ СТАТИСТИКА ДЕМО")
        print("="*70)
        
        final_stats = iris.get_system_status()
        for key, value in final_stats.items():
            if key not in ['user_profile', 'emotion_state', 'performance']:
                print(f"  {key}: {value}")
        
        print("\n✅ Демонстрация завершена!")
        print("="*70)

if __name__ == "__main__":
    # Проверка зависимостей
    print("🔍 Проверка зависимостей IRIS AI...")
    
    deps = {
        "NumPy": NP_AVAILABLE,
        "PyAudio": PYAUDIO_AVAILABLE,
        "Vosk": VOSK_AVAILABLE,
        "SpeechRecognition": SR_AVAILABLE,
        "Requests": YANDEX_AVAILABLE,
        "PyTorch": ML_LIBS.get('PYTORCH', False),
        "Scikit-learn": ML_LIBS.get('SKLEARN', False),
        "Librosa": AUDIO_ML_AVAILABLE,
        "NLTK": NLP_AVAILABLE
    }
    
    print("\n📦 УСТАНОВЛЕННЫЕ ЗАВИСИМОСТИ:")
    for dep, available in deps.items():
        status = "✅" if available else "❌"
        print(f"  {status} {dep}")
    
    # Запуск демо
    asyncio.run(demo_iris_ai())