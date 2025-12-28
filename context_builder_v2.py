"""
CONTEXT BUILDER v2.0 - АНАЛИЗАТОР СИТУАЦИЙ
Она АНАЛИЗИРУЕТ ситуацию, IRIS ГЕНЕРИРУЕТ фразы через Groq LLM
Определяет ситуации (критиЧное ХП, clutch, бомба, экономия)
"""

from typing import Dict, List, Optional
from enum import Enum
from dataclasses import dataclass
from datetime import datetime
from collections import deque


class SituationType(Enum):
    """Типы ситуаций в игре"""
    NORMAL = "normal"
    CLUTCH = "clutch"  # 1v5, 1v4
    LOW_HEALTH_CRITICAL = "low_health_critical"  # <= 15 HP
    LOW_HEALTH_WARNING = "low_health_warning"  # <= 30 HP
    LOW_AMMO_CRITICAL = "low_ammo_critical"  # <= 3
    LOW_AMMO_WARNING = "low_ammo_warning"  # <= 10
    LOW_MONEY_ECONOMY = "low_money_economy"  # < 2400
    FULL_BUY = "full_buy"  # >= 8000
    MEGA_KILL_STREAK = "mega_kill_streak"  # >= 10
    HIGH_KILL_STREAK = "high_kill_streak"  # >= 3
    MULTI_KILL_ROUND = "multi_kill_round"  # >= 3
    ACE = "ace"  # 5
    BOMB_PLANTED = "bomb_planted"


@dataclass
class GameContext:
    """Контекст игровой ситуации"""
    health: int
    armor: int
    weapon: str
    ammo_current: int
    ammo_reserve: int
    ammo_total: int
    money: int
    kill_streak: int
    round_kills: int
    deaths_this_round: int
    situations: List[SituationType]
    recent_events: List[Dict]
    team_alive: int
    enemy_alive: int
    has_bomb: bool
    bomb_planted: bool
    round_number: int
    timestamp: datetime
    situation_description: str  # ОПИСАНИЕ для LLM


class SmartContextBuilder:
    """Понимает ситуацию, ставит ценки IRIS"""
    
    def __init__(self):
        self.recent_events: deque = deque(maxlen=10)
        self.last_situation = None
        
    def build(self, player, cs2_gsi, event_type: str, event_data: Dict) -> GameContext:
        """
        Собрать контекст
        Определить ситуацию
        IRIS САМА генерирует фразу через LLM!
        """
        
        # Базовые данные
        health = getattr(player, 'health', 100)
        armor = getattr(player, 'armor', 0)
        weapon = getattr(player, 'active_weapon', 'unknown')
        money = getattr(player, 'money', 0)
        kill_streak = getattr(player, 'kill_streak', 0)
        round_kills = getattr(player, 'round_kills', 0)
        deaths_this_round = getattr(player, 'deaths_in_round', 0)
        
        ammo_current = getattr(player, 'ammo_current', 0)
        ammo_reserve = getattr(player, 'ammo_reserve', 0)
        ammo_total = ammo_current + ammo_reserve
        
        # Бомба
        has_bomb = event_data.get('has_bomb', False)
        bomb_planted = event_data.get('bomb_planted', False)
        
        # Враги
        team_alive = getattr(cs2_gsi, 'players_alive_ct', 5) if cs2_gsi else 5
        enemy_alive = getattr(cs2_gsi, 'players_alive_t', 5) if cs2_gsi else 5
        
        # Анализ ситуаций
        situations = self._analyze_situations(
            health, ammo_total, money, kill_streak, round_kills,
            team_alive, enemy_alive, bomb_planted
        )
        
        # Сохранить событие
        self.recent_events.append({
            'type': event_type,
            'timestamp': datetime.now(),
            'weapon': weapon,
            'health': health,
            'money': money,
            'round_kills': round_kills
        })
        
        # ОПИСАНИЕ ситуации ДЛЯ LLM
        situation_desc = self._build_situation_description(
            health, ammo_total, money, kill_streak, round_kills,
            team_alive, enemy_alive, weapon, bomb_planted, situations
        )
        
        context = GameContext(
            health=health,
            armor=armor,
            weapon=weapon,
            ammo_current=ammo_current,
            ammo_reserve=ammo_reserve,
            ammo_total=ammo_total,
            money=money,
            kill_streak=kill_streak,
            round_kills=round_kills,
            deaths_this_round=deaths_this_round,
            situations=situations,
            recent_events=list(self.recent_events),
            team_alive=team_alive,
            enemy_alive=enemy_alive,
            has_bomb=has_bomb,
            bomb_planted=bomb_planted,
            round_number=event_data.get('round_number', 0),
            timestamp=datetime.now(),
            situation_description=situation_desc
        )
        
        self.last_situation = situations
        return context
    
    def _analyze_situations(self, health: int, ammo: int, money: int, 
                           kill_streak: int, round_kills: int,
                           team_alive: int, enemy_alive: int,
                           bomb_planted: bool) -> List[SituationType]:
        """Анализ активных ситуаций"""
        situations = []
        
        if health <= 15:
            situations.append(SituationType.LOW_HEALTH_CRITICAL)
        elif health <= 30:
            situations.append(SituationType.LOW_HEALTH_WARNING)
        
        if ammo <= 3:
            situations.append(SituationType.LOW_AMMO_CRITICAL)
        elif ammo <= 10:
            situations.append(SituationType.LOW_AMMO_WARNING)
        
        if money < 2400:
            situations.append(SituationType.LOW_MONEY_ECONOMY)
        elif money >= 8000:
            situations.append(SituationType.FULL_BUY)
        
        if kill_streak >= 10:
            situations.append(SituationType.MEGA_KILL_STREAK)
        elif kill_streak >= 3:
            situations.append(SituationType.HIGH_KILL_STREAK)
        
        if round_kills >= 5:
            situations.append(SituationType.ACE)
        elif round_kills >= 3:
            situations.append(SituationType.MULTI_KILL_ROUND)
        
        if self._is_clutch(team_alive, enemy_alive):
            situations.append(SituationType.CLUTCH)
        
        if bomb_planted:
            situations.append(SituationType.BOMB_PLANTED)
        
        if not situations:
            situations.append(SituationType.NORMAL)
        
        return situations
    
    def _is_clutch(self, team_alive: int, enemy_alive: int) -> bool:
        """Определить clutch"""
        if team_alive <= 2 and enemy_alive >= 3:
            return True
        if team_alive == 1 and enemy_alive >= 2:
            return True
        return False
    
    def _build_situation_description(self, health: int, ammo: int, money: int,
                                     kill_streak: int, round_kills: int,
                                     team_alive: int, enemy_alive: int,
                                     weapon: str, bomb_planted: bool,
                                     situations: List[SituationType]) -> str:
        """
        Остроить описание ситуации для LLM
        IRIS ПРОЧИТАЕТ ЭТО И САМА ВСЕГО СКАЖЕТ
        """
        
        desc = f"""
ЦУНКО О ГЕНЕРАЦИИ:
- ЦНГ: {health} (critical: {health <= 15}, low: {health <= 30})
- ПАТРОНЫ: {ammo} (critical: {ammo <= 3}, low: {ammo <= 10})
- ДЕНьГИ: {money} (poor: {money < 2400}, rich: {money >= 8000})
- КИЛЛ СТРИК: {kill_streak} (mega: {kill_streak >= 10}, high: {kill_streak >= 3})
- КИЛЛ В РАУНДЕ: {round_kills} (ace: {round_kills >= 5}, multi: {round_kills >= 3})
- КОМАНДА: {team_alive} вы все (vs {enemy_alive} врагов)
- ОРУЖИЕ: {weapon}
- БОМБА: {bomb_planted}
- КЛУТЧ: {self._is_clutch(team_alive, enemy_alive)}

АКТИВНЫЕ СИТУАЦИИ: {[s.value for s in situations]}
"""
        
        return desc
    
    def get_situation_priority(self, situations: List[SituationType]) -> int:
        """Определить приоритет для ттс"""
        priority_map = {
            SituationType.LOW_HEALTH_CRITICAL: 100,
            SituationType.LOW_AMMO_CRITICAL: 95,
            SituationType.ACE: 90,
            SituationType.CLUTCH: 85,
            SituationType.BOMB_PLANTED: 80,
            SituationType.MEGA_KILL_STREAK: 75,
            SituationType.MULTI_KILL_ROUND: 65,
            SituationType.LOW_HEALTH_WARNING: 50,
            SituationType.LOW_AMMO_WARNING: 45,
            SituationType.HIGH_KILL_STREAK: 55,
            SituationType.LOW_MONEY_ECONOMY: 40,
            SituationType.NORMAL: 10,
        }
        
        return max([priority_map.get(s, 0) for s in situations])
