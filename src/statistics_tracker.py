"""
IRIS Statistics Tracker v3.0 - Система статистики за все время
Отслеживание достижений, статистики игры и прогресса стримера
"""

import json
import os
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field, asdict
from pathlib import Path
from enum import Enum
import threading
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('Statistics')


class AchievementType(Enum):
    KILLS = "kills"
    HEADSHOTS = "headshots"
    CLUTCHES = "clutches"
    ACES = "aces"
    STREAM_TIME = "stream_time"
    WIN_STREAK = "win_streak"
    SESSIONS = "sessions"


@dataclass
class Achievement:
    """Достижение"""
    id: str
    name: str
    description: str
    type: str
    requirement: int
    unlocked: bool = False
    unlocked_at: Optional[float] = None
    progress: int = 0
    icon: str = "🏆"
    rarity: str = "common"


@dataclass
class SessionStats:
    """Статистика одной сессии"""
    session_id: str
    date: str
    duration_minutes: int
    kills: int = 0
    deaths: int = 0
    headshots: int = 0
    clutches: int = 0
    aces: int = 0
    rounds_won: int = 0
    rounds_lost: int = 0
    maps_played: List[str] = field(default_factory=list)
    best_weapon: str = ""
    highlight_moments: List[Dict] = field(default_factory=list)


@dataclass
class LifetimeStats:
    """Статистика за все время"""
    total_sessions: int = 0
    total_stream_minutes: int = 0
    total_kills: int = 0
    total_deaths: int = 0
    total_headshots: int = 0
    total_clutches: int = 0
    total_aces: int = 0
    total_rounds_won: int = 0
    total_rounds_lost: int = 0
    best_kd_ratio: float = 0.0
    best_kill_streak: int = 0
    longest_session_minutes: int = 0
    first_stream_date: Optional[str] = None
    favorite_map: str = ""
    favorite_weapon: str = ""
    current_win_streak: int = 0
    best_win_streak: int = 0


class StatisticsTracker:
    """
    Система отслеживания статистики Ирис
    Сохраняет всю историю достижений и прогресса
    """
    
    DEFAULT_ACHIEVEMENTS = [
        Achievement("first_blood", "Первая кровь", "Первое убийство с Ирис", "kills", 1, icon="🩸", rarity="common"),
        Achievement("killer_10", "Новичок", "10 убийств", "kills", 10, icon="🔫", rarity="common"),
        Achievement("killer_100", "Охотник", "100 убийств", "kills", 100, icon="💀", rarity="uncommon"),
        Achievement("killer_500", "Истребитель", "500 убийств", "kills", 500, icon="☠️", rarity="rare"),
        Achievement("killer_1000", "Легенда", "1000 убийств", "kills", 1000, icon="👑", rarity="epic"),
        Achievement("headshot_10", "Меткий стрелок", "10 хедшотов", "headshots", 10, icon="🎯", rarity="common"),
        Achievement("headshot_100", "Снайпер", "100 хедшотов", "headshots", 100, icon="🔭", rarity="rare"),
        Achievement("first_ace", "АС!", "Первый эйс", "aces", 1, icon="♠️", rarity="rare"),
        Achievement("ace_5", "Мастер эйсов", "5 эйсов", "aces", 5, icon="🃏", rarity="epic"),
        Achievement("first_clutch", "Клатч!", "Первый клатч", "clutches", 1, icon="💪", rarity="uncommon"),
        Achievement("clutch_10", "Спаситель", "10 клатчей", "clutches", 10, icon="🦸", rarity="rare"),
        Achievement("stream_1h", "Первый час", "1 час стримов", "stream_time", 60, icon="⏰", rarity="common"),
        Achievement("stream_10h", "Стример", "10 часов стримов", "stream_time", 600, icon="📺", rarity="uncommon"),
        Achievement("stream_100h", "Ветеран", "100 часов стримов", "stream_time", 6000, icon="🎖️", rarity="epic"),
        Achievement("win_streak_3", "Победная серия", "3 победы подряд", "win_streak", 3, icon="🔥", rarity="common"),
        Achievement("win_streak_5", "На кураже", "5 побед подряд", "win_streak", 5, icon="🌟", rarity="uncommon"),
        Achievement("win_streak_10", "Непобедимый", "10 побед подряд", "win_streak", 10, icon="💫", rarity="epic"),
        Achievement("sessions_10", "Постоянство", "10 сессий с Ирис", "sessions", 10, icon="📅", rarity="common"),
        Achievement("sessions_50", "Преданность", "50 сессий с Ирис", "sessions", 50, icon="💝", rarity="rare"),
        Achievement("sessions_100", "Неразлучны", "100 сессий с Ирис", "sessions", 100, icon="💖", rarity="legendary"),
    ]
    
    def __init__(self, data_dir: str = None, auto_save: bool = True):
        """
        Инициализация трекера статистики
        
        Args:
            data_dir: Директория для данных
            auto_save: Автосохранение
        """
        self.data_dir = Path(data_dir or os.path.expanduser("~/.iris_stats"))
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        self.auto_save = auto_save
        
        self.lifetime_stats = LifetimeStats()
        self.achievements: Dict[str, Achievement] = {}
        self.session_history: List[SessionStats] = []
        self.current_session: Optional[SessionStats] = None
        
        self.kill_streak = 0
        self.round_kills = 0
        
        self.weapon_kills: Dict[str, int] = {}
        self.map_stats: Dict[str, Dict[str, int]] = {}
        
        self._running = False
        self._lock = threading.Lock()
        
        self._init_achievements()
        self._load_data()
        
        print(f"[STATS] Система статистики инициализирована: {self.data_dir}")
    
    def _init_achievements(self):
        """Инициализация достижений"""
        for achievement in self.DEFAULT_ACHIEVEMENTS:
            self.achievements[achievement.id] = Achievement(
                id=achievement.id,
                name=achievement.name,
                description=achievement.description,
                type=achievement.type,
                requirement=achievement.requirement,
                icon=achievement.icon,
                rarity=achievement.rarity
            )
    
    def _load_data(self):
        """Загрузка сохранённых данных"""
        try:
            stats_file = self.data_dir / "lifetime_stats.json"
            if stats_file.exists():
                with open(stats_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    for key, value in data.items():
                        if hasattr(self.lifetime_stats, key):
                            setattr(self.lifetime_stats, key, value)
                print(f"[STATS] Загружена статистика: {self.lifetime_stats.total_kills} убийств")
        except Exception as e:
            logger.error(f"Ошибка загрузки статистики: {e}")
        
        try:
            achievements_file = self.data_dir / "achievements.json"
            if achievements_file.exists():
                with open(achievements_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    for ach_id, ach_data in data.items():
                        if ach_id in self.achievements:
                            self.achievements[ach_id].unlocked = ach_data.get('unlocked', False)
                            self.achievements[ach_id].unlocked_at = ach_data.get('unlocked_at')
                            self.achievements[ach_id].progress = ach_data.get('progress', 0)
                unlocked = sum(1 for a in self.achievements.values() if a.unlocked)
                print(f"[STATS] Загружены достижения: {unlocked}/{len(self.achievements)}")
        except Exception as e:
            logger.error(f"Ошибка загрузки достижений: {e}")
        
        try:
            weapons_file = self.data_dir / "weapon_stats.json"
            if weapons_file.exists():
                with open(weapons_file, 'r', encoding='utf-8') as f:
                    self.weapon_kills = json.load(f)
        except Exception as e:
            logger.error(f"Ошибка загрузки статистики оружия: {e}")
        
        try:
            maps_file = self.data_dir / "map_stats.json"
            if maps_file.exists():
                with open(maps_file, 'r', encoding='utf-8') as f:
                    self.map_stats = json.load(f)
        except Exception as e:
            logger.error(f"Ошибка загрузки статистики карт: {e}")
    
    def _save_data(self):
        """Сохранение данных"""
        with self._lock:
            try:
                stats_file = self.data_dir / "lifetime_stats.json"
                with open(stats_file, 'w', encoding='utf-8') as f:
                    json.dump(asdict(self.lifetime_stats), f, ensure_ascii=False, indent=2)
            except Exception as e:
                logger.error(f"Ошибка сохранения статистики: {e}")
            
            try:
                achievements_file = self.data_dir / "achievements.json"
                with open(achievements_file, 'w', encoding='utf-8') as f:
                    data = {}
                    for ach_id, ach in self.achievements.items():
                        data[ach_id] = {
                            'unlocked': ach.unlocked,
                            'unlocked_at': ach.unlocked_at,
                            'progress': ach.progress
                        }
                    json.dump(data, f, ensure_ascii=False, indent=2)
            except Exception as e:
                logger.error(f"Ошибка сохранения достижений: {e}")
            
            try:
                weapons_file = self.data_dir / "weapon_stats.json"
                with open(weapons_file, 'w', encoding='utf-8') as f:
                    json.dump(self.weapon_kills, f, ensure_ascii=False, indent=2)
            except Exception as e:
                logger.error(f"Ошибка сохранения статистики оружия: {e}")
            
            try:
                maps_file = self.data_dir / "map_stats.json"
                with open(maps_file, 'w', encoding='utf-8') as f:
                    json.dump(self.map_stats, f, ensure_ascii=False, indent=2)
            except Exception as e:
                logger.error(f"Ошибка сохранения статистики карт: {e}")
    
    def start_session(self) -> str:
        """
        Начать новую сессию
        
        Returns:
            ID сессии
        """
        session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        self.current_session = SessionStats(
            session_id=session_id,
            date=datetime.now().strftime("%Y-%m-%d"),
            duration_minutes=0
        )
        
        self.kill_streak = 0
        self.round_kills = 0
        
        self.lifetime_stats.total_sessions += 1
        
        if not self.lifetime_stats.first_stream_date:
            self.lifetime_stats.first_stream_date = datetime.now().strftime("%Y-%m-%d")
        
        self._check_achievement("sessions", self.lifetime_stats.total_sessions)
        
        self._running = True
        print(f"[STATS] Сессия начата: {session_id}")
        
        return session_id
    
    def end_session(self, duration_minutes: int = None):
        """Завершить сессию"""
        if not self.current_session:
            return
        
        if duration_minutes:
            self.current_session.duration_minutes = duration_minutes
        
        self.lifetime_stats.total_stream_minutes += self.current_session.duration_minutes
        
        if self.current_session.duration_minutes > self.lifetime_stats.longest_session_minutes:
            self.lifetime_stats.longest_session_minutes = self.current_session.duration_minutes
        
        self._check_achievement("stream_time", self.lifetime_stats.total_stream_minutes)
        
        if self.current_session.deaths > 0:
            kd = self.current_session.kills / self.current_session.deaths
            if kd > self.lifetime_stats.best_kd_ratio:
                self.lifetime_stats.best_kd_ratio = round(kd, 2)
        
        self._update_favorite_weapon()
        self._update_favorite_map()
        
        self.session_history.append(self.current_session)
        
        self._save_data()
        self._save_session_history()
        
        print(f"[STATS] Сессия завершена: {self.current_session.kills} убийств, {self.current_session.deaths} смертей")
        
        self.current_session = None
        self._running = False
    
    def record_kill(self, weapon: str = "", headshot: bool = False, 
                   map_name: str = "", victim: str = "") -> List[Achievement]:
        """
        Записать убийство
        
        Returns:
            Список новых разблокированных достижений
        """
        new_achievements = []
        
        with self._lock:
            self.lifetime_stats.total_kills += 1
            self.kill_streak += 1
            self.round_kills += 1
            
            if self.current_session:
                self.current_session.kills += 1
            
            if headshot:
                self.lifetime_stats.total_headshots += 1
                if self.current_session:
                    self.current_session.headshots += 1
            
            if weapon:
                self.weapon_kills[weapon] = self.weapon_kills.get(weapon, 0) + 1
                if self.current_session and not self.current_session.best_weapon:
                    self.current_session.best_weapon = weapon
            
            if map_name:
                if map_name not in self.map_stats:
                    self.map_stats[map_name] = {'kills': 0, 'deaths': 0, 'rounds': 0}
                self.map_stats[map_name]['kills'] += 1
            
            if self.kill_streak > self.lifetime_stats.best_kill_streak:
                self.lifetime_stats.best_kill_streak = self.kill_streak
            
            if self.round_kills == 5:
                self.lifetime_stats.total_aces += 1
                if self.current_session:
                    self.current_session.aces += 1
                    self.current_session.highlight_moments.append({
                        'type': 'ace',
                        'timestamp': time.time(),
                        'weapon': weapon
                    })
                ach = self._check_achievement("aces", self.lifetime_stats.total_aces)
                if ach:
                    new_achievements.append(ach)
            
            ach = self._check_achievement("kills", self.lifetime_stats.total_kills)
            if ach:
                new_achievements.append(ach)
            
            if headshot:
                ach = self._check_achievement("headshots", self.lifetime_stats.total_headshots)
                if ach:
                    new_achievements.append(ach)
        
        if self.auto_save and self.lifetime_stats.total_kills % 50 == 0:
            self._save_data()
        
        return new_achievements
    
    def record_death(self, attacker: str = "", weapon: str = "", map_name: str = ""):
        """Записать смерть"""
        with self._lock:
            self.lifetime_stats.total_deaths += 1
            self.kill_streak = 0
            
            if self.current_session:
                self.current_session.deaths += 1
            
            if map_name and map_name in self.map_stats:
                self.map_stats[map_name]['deaths'] += 1
    
    def record_round_end(self, won: bool, map_name: str = ""):
        """Записать окончание раунда"""
        with self._lock:
            self.round_kills = 0
            
            if won:
                self.lifetime_stats.total_rounds_won += 1
                self.lifetime_stats.current_win_streak += 1
                
                if self.lifetime_stats.current_win_streak > self.lifetime_stats.best_win_streak:
                    self.lifetime_stats.best_win_streak = self.lifetime_stats.current_win_streak
                
                if self.current_session:
                    self.current_session.rounds_won += 1
                
                self._check_achievement("win_streak", self.lifetime_stats.current_win_streak)
            else:
                self.lifetime_stats.total_rounds_lost += 1
                self.lifetime_stats.current_win_streak = 0
                
                if self.current_session:
                    self.current_session.rounds_lost += 1
            
            if map_name:
                if map_name not in self.map_stats:
                    self.map_stats[map_name] = {'kills': 0, 'deaths': 0, 'rounds': 0}
                self.map_stats[map_name]['rounds'] += 1
    
    def record_clutch(self, enemies_killed: int = 1, map_name: str = "") -> Optional[Achievement]:
        """Записать клатч"""
        with self._lock:
            self.lifetime_stats.total_clutches += 1
            
            if self.current_session:
                self.current_session.clutches += 1
                self.current_session.highlight_moments.append({
                    'type': 'clutch',
                    'timestamp': time.time(),
                    'enemies': enemies_killed
                })
            
            return self._check_achievement("clutches", self.lifetime_stats.total_clutches)
    
    def _check_achievement(self, achievement_type: str, current_value: int) -> Optional[Achievement]:
        """Проверить и разблокировать достижение"""
        for ach_id, ach in self.achievements.items():
            if ach.type == achievement_type and not ach.unlocked:
                ach.progress = current_value
                
                if current_value >= ach.requirement:
                    ach.unlocked = True
                    ach.unlocked_at = time.time()
                    print(f"[STATS] 🏆 Достижение разблокировано: {ach.icon} {ach.name}")
                    return ach
        return None
    
    def _update_favorite_weapon(self):
        """Обновить любимое оружие"""
        if self.weapon_kills:
            self.lifetime_stats.favorite_weapon = max(
                self.weapon_kills, 
                key=self.weapon_kills.get
            )
    
    def _update_favorite_map(self):
        """Обновить любимую карту"""
        if self.map_stats:
            self.lifetime_stats.favorite_map = max(
                self.map_stats,
                key=lambda m: self.map_stats[m].get('rounds', 0)
            )
    
    def _save_session_history(self):
        """Сохранить историю сессий"""
        try:
            history_file = self.data_dir / "session_history.json"
            
            recent_sessions = self.session_history[-100:]
            data = [asdict(s) for s in recent_sessions]
            
            with open(history_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"Ошибка сохранения истории сессий: {e}")
    
    def get_lifetime_summary(self) -> Dict[str, Any]:
        """Получить сводку статистики за все время"""
        return {
            'total_sessions': self.lifetime_stats.total_sessions,
            'total_hours': round(self.lifetime_stats.total_stream_minutes / 60, 1),
            'total_kills': self.lifetime_stats.total_kills,
            'total_deaths': self.lifetime_stats.total_deaths,
            'kd_ratio': round(
                self.lifetime_stats.total_kills / max(1, self.lifetime_stats.total_deaths), 2
            ),
            'total_headshots': self.lifetime_stats.total_headshots,
            'headshot_percent': round(
                self.lifetime_stats.total_headshots / max(1, self.lifetime_stats.total_kills) * 100, 1
            ),
            'total_aces': self.lifetime_stats.total_aces,
            'total_clutches': self.lifetime_stats.total_clutches,
            'best_kill_streak': self.lifetime_stats.best_kill_streak,
            'best_win_streak': self.lifetime_stats.best_win_streak,
            'favorite_weapon': self.lifetime_stats.favorite_weapon,
            'favorite_map': self.lifetime_stats.favorite_map,
            'first_stream': self.lifetime_stats.first_stream_date,
        }
    
    def get_unlocked_achievements(self) -> List[Achievement]:
        """Получить разблокированные достижения"""
        return [a for a in self.achievements.values() if a.unlocked]
    
    def get_next_achievements(self, limit: int = 3) -> List[Tuple[Achievement, float]]:
        """
        Получить ближайшие достижения к разблокировке
        
        Returns:
            Список (достижение, прогресс в процентах)
        """
        locked = [a for a in self.achievements.values() if not a.unlocked]
        
        with_progress = []
        for ach in locked:
            progress_percent = min(100, (ach.progress / ach.requirement) * 100)
            with_progress.append((ach, progress_percent))
        
        with_progress.sort(key=lambda x: x[1], reverse=True)
        return with_progress[:limit]
    
    def format_stats_message(self) -> str:
        """Сформировать текстовое сообщение со статистикой"""
        stats = self.get_lifetime_summary()
        
        message = f"""📊 Твоя статистика за всё время:

🎯 Убийств: {stats['total_kills']} (K/D: {stats['kd_ratio']})
💀 Смертей: {stats['total_deaths']}
🎯 Хедшотов: {stats['total_headshots']} ({stats['headshot_percent']}%)
♠️ Эйсов: {stats['total_aces']}
💪 Клатчей: {stats['total_clutches']}
🔥 Лучшая серия: {stats['best_kill_streak']} убийств

⏱️ Время стримов: {stats['total_hours']} часов
📺 Сессий: {stats['total_sessions']}
🗺️ Любимая карта: {stats['favorite_map'] or 'Пока нет'}
🔫 Любимое оружие: {stats['favorite_weapon'] or 'Пока нет'}

🏆 Достижений: {len(self.get_unlocked_achievements())}/{len(self.achievements)}"""
        
        return message


if __name__ == "__main__":
    print("=== Тест системы статистики Ирис ===\n")
    
    tracker = StatisticsTracker()
    
    session_id = tracker.start_session()
    print(f"Сессия: {session_id}\n")
    
    new_achs = tracker.record_kill(weapon="ak47", headshot=True, map_name="de_dust2")
    for ach in new_achs:
        print(f"Новое достижение: {ach.icon} {ach.name}")
    
    tracker.record_kill(weapon="ak47", headshot=False)
    tracker.record_kill(weapon="awp", headshot=True)
    tracker.record_death(attacker="Enemy", weapon="m4a4")
    tracker.record_round_end(won=True, map_name="de_dust2")
    
    for i in range(5):
        tracker.record_kill(weapon="ak47")
    
    tracker.end_session(duration_minutes=45)
    
    print("\n" + tracker.format_stats_message())
    
    print("\n\nБлижайшие достижения:")
    for ach, progress in tracker.get_next_achievements():
        print(f"  {ach.icon} {ach.name}: {progress:.1f}%")
    
    print("\nТест завершен!")
