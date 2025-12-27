"""
IRIS Session Memory v3.0 - Система памяти сессий
Сохранение контекста разговоров, игровых событий и предпочтений
"""

import json
import os
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field, asdict
from pathlib import Path
import threading
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('SessionMemory')


@dataclass
class MemoryEntry:
    """Запись в памяти"""
    id: str
    category: str
    content: str
    importance: float = 0.5
    timestamp: float = field(default_factory=time.time)
    access_count: int = 0
    tags: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ConversationEntry:
    """Запись разговора"""
    role: str
    content: str
    timestamp: float = field(default_factory=time.time)
    emotion: str = "neutral"
    context: Dict[str, Any] = field(default_factory=dict)


@dataclass
class GameEventEntry:
    """Запись игрового события"""
    event_type: str
    data: Dict[str, Any]
    timestamp: float = field(default_factory=time.time)
    reaction: Optional[str] = None
    map_name: str = ""
    round_number: int = 0


@dataclass
class UserPreference:
    """Предпочтение пользователя"""
    key: str
    value: Any
    confidence: float = 0.5
    updated_at: float = field(default_factory=time.time)
    source: str = "inferred"


class SessionMemory:
    """
    Система памяти сессий Ирис
    Сохраняет контекст разговоров, игровые события, предпочтения пользователя
    """
    
    def __init__(self, 
                 data_dir: str = None,
                 max_conversation_history: int = 100,
                 max_game_events: int = 500,
                 auto_save_interval: int = 60):
        """
        Инициализация системы памяти
        
        Args:
            data_dir: Директория для хранения данных
            max_conversation_history: Макс. кол-во записей разговора
            max_game_events: Макс. кол-во игровых событий
            auto_save_interval: Интервал автосохранения (секунды)
        """
        self.data_dir = Path(data_dir or os.path.expanduser("~/.iris_memory"))
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        self.max_conversation_history = max_conversation_history
        self.max_game_events = max_game_events
        self.auto_save_interval = auto_save_interval
        
        self.current_session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        self.conversation_history: List[ConversationEntry] = []
        self.game_events: List[GameEventEntry] = []
        self.user_preferences: Dict[str, UserPreference] = {}
        self.long_term_memory: List[MemoryEntry] = []
        
        self.session_context = {
            'streamer_name': '',
            'current_game': 'CS2',
            'current_map': '',
            'session_start': time.time(),
            'total_kills': 0,
            'total_deaths': 0,
            'mood': 'neutral',
            'energy_level': 0.5,
        }
        
        self._running = False
        self._save_thread = None
        self._lock = threading.Lock()
        
        self._load_persistent_data()
        
        print(f"[MEMORY] Система памяти инициализирована: {self.data_dir}")
        print(f"[MEMORY] ID сессии: {self.current_session_id}")
    
    def _get_file_path(self, filename: str) -> Path:
        """Получить путь к файлу данных"""
        return self.data_dir / filename
    
    def _load_persistent_data(self):
        """Загрузка сохранённых данных"""
        try:
            prefs_file = self._get_file_path("user_preferences.json")
            if prefs_file.exists():
                with open(prefs_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    for key, pref_data in data.items():
                        self.user_preferences[key] = UserPreference(**pref_data)
                print(f"[MEMORY] Загружено {len(self.user_preferences)} предпочтений")
        except Exception as e:
            logger.error(f"Ошибка загрузки предпочтений: {e}")
        
        try:
            memory_file = self._get_file_path("long_term_memory.json")
            if memory_file.exists():
                with open(memory_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    for entry_data in data:
                        self.long_term_memory.append(MemoryEntry(**entry_data))
                print(f"[MEMORY] Загружено {len(self.long_term_memory)} записей памяти")
        except Exception as e:
            logger.error(f"Ошибка загрузки памяти: {e}")
        
        try:
            history_file = self._get_file_path("recent_conversation.json")
            if history_file.exists():
                with open(history_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    
                    cutoff_time = time.time() - 24 * 3600
                    for entry_data in data:
                        if entry_data.get('timestamp', 0) > cutoff_time:
                            self.conversation_history.append(ConversationEntry(**entry_data))
                print(f"[MEMORY] Загружено {len(self.conversation_history)} записей разговора")
        except Exception as e:
            logger.error(f"Ошибка загрузки истории: {e}")
    
    def _save_persistent_data(self):
        """Сохранение данных на диск"""
        with self._lock:
            try:
                prefs_file = self._get_file_path("user_preferences.json")
                with open(prefs_file, 'w', encoding='utf-8') as f:
                    data = {k: asdict(v) for k, v in self.user_preferences.items()}
                    json.dump(data, f, ensure_ascii=False, indent=2)
            except Exception as e:
                logger.error(f"Ошибка сохранения предпочтений: {e}")
            
            try:
                memory_file = self._get_file_path("long_term_memory.json")
                with open(memory_file, 'w', encoding='utf-8') as f:
                    data = [asdict(entry) for entry in self.long_term_memory]
                    json.dump(data, f, ensure_ascii=False, indent=2)
            except Exception as e:
                logger.error(f"Ошибка сохранения памяти: {e}")
            
            try:
                history_file = self._get_file_path("recent_conversation.json")
                with open(history_file, 'w', encoding='utf-8') as f:
                    data = [asdict(entry) for entry in self.conversation_history[-50:]]
                    json.dump(data, f, ensure_ascii=False, indent=2)
            except Exception as e:
                logger.error(f"Ошибка сохранения истории: {e}")
    
    def _auto_save_loop(self):
        """Цикл автосохранения"""
        while self._running:
            time.sleep(self.auto_save_interval)
            if self._running:
                self._save_persistent_data()
    
    def add_conversation(self, role: str, content: str, 
                        emotion: str = "neutral", 
                        context: Dict[str, Any] = None):
        """
        Добавить запись разговора
        
        Args:
            role: Роль (user, assistant, system)
            content: Содержание
            emotion: Эмоция
            context: Дополнительный контекст
        """
        entry = ConversationEntry(
            role=role,
            content=content,
            emotion=emotion,
            context=context or {}
        )
        
        with self._lock:
            self.conversation_history.append(entry)
            
            if len(self.conversation_history) > self.max_conversation_history:
                old_entries = self.conversation_history[:10]
                self._archive_conversations(old_entries)
                self.conversation_history = self.conversation_history[10:]
    
    def add_game_event(self, event_type: str, data: Dict[str, Any],
                      reaction: str = None):
        """
        Добавить игровое событие
        
        Args:
            event_type: Тип события (kill, death, round_end, etc.)
            data: Данные события
            reaction: Реакция Ирис
        """
        entry = GameEventEntry(
            event_type=event_type,
            data=data,
            reaction=reaction,
            map_name=self.session_context.get('current_map', ''),
            round_number=data.get('round', 0)
        )
        
        with self._lock:
            self.game_events.append(entry)
            
            if event_type == 'kill':
                self.session_context['total_kills'] = self.session_context.get('total_kills', 0) + 1
            elif event_type == 'death':
                self.session_context['total_deaths'] = self.session_context.get('total_deaths', 0) + 1
            
            if len(self.game_events) > self.max_game_events:
                self.game_events = self.game_events[-self.max_game_events:]
    
    def set_preference(self, key: str, value: Any, 
                      confidence: float = 0.5, source: str = "inferred"):
        """
        Установить предпочтение пользователя
        
        Args:
            key: Ключ предпочтения
            value: Значение
            confidence: Уверенность (0.0-1.0)
            source: Источник (explicit, inferred, learned)
        """
        with self._lock:
            if key in self.user_preferences:
                existing = self.user_preferences[key]
                if source == "explicit" or confidence > existing.confidence:
                    self.user_preferences[key] = UserPreference(
                        key=key,
                        value=value,
                        confidence=confidence,
                        source=source
                    )
            else:
                self.user_preferences[key] = UserPreference(
                    key=key,
                    value=value,
                    confidence=confidence,
                    source=source
                )
    
    def get_preference(self, key: str, default: Any = None) -> Any:
        """Получить предпочтение пользователя"""
        with self._lock:
            if key in self.user_preferences:
                pref = self.user_preferences[key]
                pref.access_count = getattr(pref, 'access_count', 0) + 1
                return pref.value
            return default
    
    def remember(self, content: str, category: str = "general",
                importance: float = 0.5, tags: List[str] = None,
                metadata: Dict[str, Any] = None):
        """
        Запомнить важную информацию
        
        Args:
            content: Содержание
            category: Категория (general, user_info, game_fact, preference)
            importance: Важность (0.0-1.0)
            tags: Теги для поиска
            metadata: Дополнительные данные
        """
        import uuid
        entry = MemoryEntry(
            id=str(uuid.uuid4()),
            category=category,
            content=content,
            importance=importance,
            tags=tags or [],
            metadata=metadata or {}
        )
        
        with self._lock:
            self.long_term_memory.append(entry)
            
            if importance >= 0.8:
                self._save_persistent_data()
    
    def recall(self, query: str = None, category: str = None,
              tags: List[str] = None, limit: int = 10) -> List[MemoryEntry]:
        """
        Вспомнить информацию
        
        Args:
            query: Поисковый запрос
            category: Фильтр по категории
            tags: Фильтр по тегам
            limit: Максимум результатов
            
        Returns:
            Список найденных записей
        """
        with self._lock:
            results = []
            
            for entry in self.long_term_memory:
                if category and entry.category != category:
                    continue
                
                if tags and not any(tag in entry.tags for tag in tags):
                    continue
                
                if query:
                    query_lower = query.lower()
                    if query_lower not in entry.content.lower():
                        continue
                
                entry.access_count += 1
                results.append(entry)
            
            results.sort(key=lambda x: (x.importance, x.access_count), reverse=True)
            return results[:limit]
    
    def get_recent_conversation(self, count: int = 10) -> List[Dict[str, Any]]:
        """Получить последние записи разговора"""
        with self._lock:
            entries = self.conversation_history[-count:]
            return [asdict(entry) for entry in entries]
    
    def get_conversation_context(self, max_tokens: int = 2000) -> str:
        """
        Получить контекст разговора для LLM
        
        Args:
            max_tokens: Примерный лимит символов
            
        Returns:
            Текстовый контекст
        """
        with self._lock:
            context_parts = []
            
            for pref_key in ['streamer_name', 'communication_style', 'humor_level']:
                if pref_key in self.user_preferences:
                    pref = self.user_preferences[pref_key]
                    context_parts.append(f"Пользователь: {pref_key}={pref.value}")
            
            for entry in self.conversation_history[-20:]:
                role_name = "Пользователь" if entry.role == "user" else "Ирис"
                context_parts.append(f"{role_name}: {entry.content}")
            
            context = "\n".join(context_parts)
            
            if len(context) > max_tokens:
                context = context[-max_tokens:]
            
            return context
    
    def get_session_summary(self) -> Dict[str, Any]:
        """Получить сводку текущей сессии"""
        with self._lock:
            session_duration = time.time() - self.session_context.get('session_start', time.time())
            
            kills = sum(1 for e in self.game_events if e.event_type == 'kill')
            deaths = sum(1 for e in self.game_events if e.event_type == 'death')
            
            return {
                'session_id': self.current_session_id,
                'duration_minutes': int(session_duration / 60),
                'total_kills': kills,
                'total_deaths': deaths,
                'kd_ratio': round(kills / max(1, deaths), 2),
                'conversation_count': len(self.conversation_history),
                'events_count': len(self.game_events),
                'current_map': self.session_context.get('current_map', 'Unknown'),
                'current_mood': self.session_context.get('mood', 'neutral'),
            }
    
    def _archive_conversations(self, entries: List[ConversationEntry]):
        """Архивировать старые разговоры в память"""
        for entry in entries:
            if len(entry.content) > 50:
                self.remember(
                    content=f"[{entry.role}] {entry.content[:200]}",
                    category="conversation_archive",
                    importance=0.3,
                    metadata={'original_timestamp': entry.timestamp}
                )
    
    def update_session_context(self, key: str, value: Any):
        """Обновить контекст сессии"""
        with self._lock:
            self.session_context[key] = value
    
    def get_session_context(self, key: str = None) -> Any:
        """Получить контекст сессии"""
        with self._lock:
            if key:
                return self.session_context.get(key)
            return dict(self.session_context)
    
    def start(self):
        """Запуск системы памяти"""
        if self._running:
            return
        
        self._running = True
        self._save_thread = threading.Thread(
            target=self._auto_save_loop,
            daemon=True,
            name="MemoryAutoSave"
        )
        self._save_thread.start()
        print("[MEMORY] Система памяти запущена")
    
    def stop(self):
        """Остановка системы памяти"""
        if not self._running:
            return
        
        self._running = False
        
        if self._save_thread:
            self._save_thread.join(timeout=2.0)
        
        self._save_persistent_data()
        
        self._save_session_log()
        
        print("[MEMORY] Система памяти остановлена")
    
    def _save_session_log(self):
        """Сохранить лог сессии"""
        try:
            sessions_dir = self.data_dir / "sessions"
            sessions_dir.mkdir(exist_ok=True)
            
            session_file = sessions_dir / f"session_{self.current_session_id}.json"
            
            session_data = {
                'session_id': self.current_session_id,
                'summary': self.get_session_summary(),
                'context': self.session_context,
                'conversation_count': len(self.conversation_history),
                'events_count': len(self.game_events),
            }
            
            with open(session_file, 'w', encoding='utf-8') as f:
                json.dump(session_data, f, ensure_ascii=False, indent=2)
                
        except Exception as e:
            logger.error(f"Ошибка сохранения лога сессии: {e}")


if __name__ == "__main__":
    print("=== Тест системы памяти Ирис ===\n")
    
    memory = SessionMemory()
    memory.start()
    
    memory.set_preference("streamer_name", "TestStreamer", confidence=1.0, source="explicit")
    memory.set_preference("humor_level", "high", confidence=0.7, source="inferred")
    
    memory.add_conversation("user", "Привет, Ирис!")
    memory.add_conversation("assistant", "Привет! Рада тебя видеть!", emotion="happy")
    memory.add_conversation("user", "Как дела?")
    memory.add_conversation("assistant", "Отлично! Готова помогать на стриме!", emotion="excited")
    
    memory.add_game_event("kill", {"weapon": "ak47", "headshot": True}, "Красивый хедшот!")
    memory.add_game_event("kill", {"weapon": "awp", "headshot": False}, "Снайпер в деле!")
    memory.add_game_event("death", {"attacker": "Enemy", "weapon": "m4a4"}, "Бывает...")
    
    memory.remember(
        "Стример любит агрессивный стиль игры",
        category="user_info",
        importance=0.8,
        tags=["playstyle", "preference"]
    )
    
    print("Последние разговоры:")
    for conv in memory.get_recent_conversation(5):
        print(f"  [{conv['role']}]: {conv['content']}")
    
    print(f"\nПредпочтение 'streamer_name': {memory.get_preference('streamer_name')}")
    
    print("\nПоиск в памяти 'стиль':")
    for entry in memory.recall(query="стиль"):
        print(f"  - {entry.content}")
    
    print(f"\nСводка сессии: {memory.get_session_summary()}")
    
    time.sleep(1)
    memory.stop()
    
    print("\nТест завершен!")
