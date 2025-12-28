import json
import time
import threading
import logging
import sys
import os
from flask import Flask, request, jsonify
from dataclasses import dataclass, field
from typing import Optional, Callable, Dict, List, Any, Tuple
from collections import deque

# Настройка кодировки для Windows
if sys.platform == 'win32':
    os.environ['PYTHONIOENCODING'] = 'utf-8'
    sys.stdout.reconfigure(encoding='utf-8')

# Логирование
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - [%(name)s] - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('cs2_gsi.log', encoding='utf-8')
    ]
)
logger = logging.getLogger(__name__)

# ════════════════════════════════════════════════════════════
# DATACLASSES
# ════════════════════════════════════════════════════════════

@dataclass
class PlayerState:
    name: str = ""
    team: str = ""
    health: int = 100
    armor: int = 0
    helmet: bool = False
    money: int = 0
    round_kills: int = 0
    round_killhs: int = 0
    equip_value: int = 0
    kills: int = 0
    assists: int = 0
    deaths: int = 0
    mvps: int = 0
    score: int = 0
    weapon: str = ""
    
    # ✅ НОВЫЕ ПОЛЯ ДЛЯ REAL-TIME ИНФОРМАЦИИ
    ammo_in_magazine: int = 0          # Патроны в магазине
    ammo_in_reserve: int = 0           # Патроны в резерве
    defuse_kit: bool = False           # Есть ли кит дефьюза
    has_bomb: bool = False             # Есть ли бомба
    fatigue: int = 100                 # Усталость (0-100)
    
    # ✅ КООРДИНАТЫ НА КАРТЕ
    position: Tuple[float, float] = (0, 0)  # (x, y)
    position_z: float = 0.0            # z координата (высота)
    
    # ✅ ВРЕМЕНА ОБНОВЛЕНИЙ
    last_health_update_time: float = 0
    last_ammo_warning_time: float = 0

@dataclass
class RoundState:
    phase: str = ""
    bomb: str = ""
    win_team: str = ""

@dataclass
class MapState:
    name: str = ""
    mode: str = ""
    phase: str = ""
    round: int = 0
    ct_score: int = 0
    t_score: int = 0

@dataclass
class GameEvent:
    event_type: str
    data: Dict[str, Any]
    timestamp: float = field(default_factory=time.time)

# ════════════════════════════════════════════════════════════
# ГЛАВНЫЙ КЛАСС GSI
# ════════════════════════════════════════════════════════════

class CS2GameStateIntegration:
    def __init__(self,
                 port: int = 3000,
                 event_callback: Optional[Callable[[GameEvent], None]] = None):
        self.port = port
        self.event_callback = event_callback
        self.player = PlayerState()
        self.round = RoundState()
        self.map = MapState()
        self.previous_state: Dict = {}
        self.events_history: deque = deque(maxlen=100)
        self.kill_streak = 0
        self.round_start_kills = 0
        self.clutch_situation = False
        self.clutch_enemies = 0
        
        # ✅ НОВЫЕ ПОЛЯ ДЛЯ FULL DATA TRACKING
        self.all_grenades: List[Dict] = []          # ВСЕ ГРЕНАДЫ В ИГРЕ
        self.all_players_positions: Dict = {}       # ПОЗИЦИИ ВСЕХ ВРАГОВ {steamid: {x, y, z}}
        self.all_players_states: Dict = {}          # СТАТУС ВСЕХ {steamid: {alive, team}}
        self.phase_countdown: float = 0.0           # ВРЕМЯ ОСТАВШЕЕСЯ В РАУНДЕ
        
        self.app = Flask(__name__)
        self._setup_routes()
        self.server_thread = None
        self.is_running = False

    def _setup_routes(self):
        @self.app.route('/', methods=['POST'])
        def gsi_handler():
            try:
                data = request.get_json()
                if data:
                    self._process_game_state(data)
                return jsonify({"status": "ok"})
            except Exception as e:
                logger.error(f"[CS2 GSI] Ошибка обработки: {e}")
                return jsonify({"status": "error"}), 500

        @self.app.route('/health', methods=['GET'])
        def health_check():
            return jsonify({
                "status": "running",
                "player": self.player.name,
                "map": self.map.name,
                "round": self.map.round
            })

    def _process_game_state(self, data: Dict):
        """Обработка состояния игры с полным сбором информации"""
        
        # ════════════════════════════════════════════════════════════
        # ОБРАБОТКА ИГРОКА
        # ════════════════════════════════════════════════════════════
        player_data = data.get('player', {})
        if player_data:
            state = player_data.get('state', {})
            match_stats = player_data.get('match_stats', {})
            weapons = player_data.get('weapons', {})
            position_data = player_data.get('position', {})  # ✅ ПОЗИЦИЯ
            
            # Сохраняем старые значения
            old_health = self.player.health
            old_kills = self.player.kills
            old_deaths = self.player.deaths
            old_round_kills = self.player.round_kills
            old_ammo = (self.player.ammo_in_magazine + self.player.ammo_in_reserve)
            
            # ✅ Основные параметры
            self.player.name = player_data.get('name', self.player.name)
            self.player.team = player_data.get('team', self.player.team)
            self.player.health = state.get('health', self.player.health)
            self.player.armor = state.get('armor', self.player.armor)
            self.player.helmet = state.get('helmet', self.player.helmet)
            self.player.money = state.get('money', self.player.money)
            self.player.round_kills = state.get('round_kills', self.player.round_kills)
            self.player.round_killhs = state.get('round_killhs', self.player.round_killhs)
            self.player.equip_value = state.get('equip_value', self.player.equip_value)
            
            # ✅ Статистика матча
            self.player.kills = match_stats.get('kills', self.player.kills)
            self.player.assists = match_stats.get('assists', self.player.assists)
            self.player.deaths = match_stats.get('deaths', self.player.deaths)
            self.player.mvps = match_stats.get('mvps', self.player.mvps)
            self.player.score = match_stats.get('score', self.player.score)
            
            # ✅ Оружие и патроны
            for weapon_key, weapon_data in weapons.items():
                if weapon_data.get('state') == 'active':
                    self.player.weapon = weapon_data.get('name', '')
                    self.player.ammo_in_magazine = weapon_data.get('ammo_clip', 0)
                    self.player.ammo_in_reserve = weapon_data.get('ammo_clip_reserve', 0)
                    break
            
            # ✅ НОВОЕ: Дополнительные параметры
            self.player.defuse_kit = state.get('defusekit', False)
            self.player.has_bomb = state.get('bomb', False)
            self.player.fatigue = state.get('fatigue', 100)
            self.player.last_health_update_time = time.time()
            
            # ✅ НОВОЕ: ПОЗИЦИЯ НА КАРТЕ
            if position_data:
                self.player.position = (
                    position_data.get('x', 0),
                    position_data.get('y', 0)
                )
                self.player.position_z = position_data.get('z', 0)
            
            # ✅ СОБЫТИЯ
            new_ammo = (self.player.ammo_in_magazine + self.player.ammo_in_reserve)
            if new_ammo < old_ammo and new_ammo <= 10 and new_ammo > 0:
                if time.time() - self.player.last_ammo_warning_time > 3.0:
                    self._emit_event('low_ammo_warning', {
                        'ammo_magazine': self.player.ammo_in_magazine,
                        'ammo_reserve': self.player.ammo_in_reserve,
                        'total_ammo': new_ammo,
                        'weapon': self.player.weapon
                    })
                    self.player.last_ammo_warning_time = time.time()
            
            if self.player.kills > old_kills:
                self._emit_kill_event(self.player.kills - old_kills)
            
            if self.player.deaths > old_deaths:
                self._emit_death_event()
            
            if self.player.health < old_health and self.player.health > 0:
                self._emit_damage_event(old_health - self.player.health)
        
        # ════════════════════════════════════════════════════════════
        # ОБРАБОТКА РАУНДА
        # ════════════════════════════════════════════════════════════
        round_data = data.get('round', {})
        if round_data:
            old_phase = self.round.phase
            old_bomb = self.round.bomb
            self.round.phase = round_data.get('phase', self.round.phase)
            self.round.bomb = round_data.get('bomb', self.round.bomb)
            self.round.win_team = round_data.get('win_team', self.round.win_team)
            
            if self.round.phase == 'freezetime' and old_phase != 'freezetime':
                self._emit_round_start_event()
            
            if self.round.phase == 'over' and old_phase != 'over':
                self._emit_round_end_event()
            
            if self.round.bomb == 'planted' and old_bomb != 'planted':
                self._emit_bomb_planted_event()
            
            if self.round.bomb == 'defused' and old_bomb != 'defused':
                self._emit_bomb_defused_event()
            
            if self.round.bomb == 'exploded' and old_bomb != 'exploded':
                self._emit_bomb_exploded_event()
        
        # ════════════════════════════════════════════════════════════
        # ОБРАБОТКА КАРТЫ И МАТЧА
        # ════════════════════════════════════════════════════════════
        map_data = data.get('map', {})
        if map_data:
            old_round = self.map.round
            self.map.name = map_data.get('name', self.map.name)
            self.map.mode = map_data.get('mode', self.map.mode)
            self.map.phase = map_data.get('phase', self.map.phase)
            self.map.round = map_data.get('round', self.map.round)
            team_ct = map_data.get('team_ct', {})
            team_t = map_data.get('team_t', {})
            self.map.ct_score = team_ct.get('score', self.map.ct_score)
            self.map.t_score = team_t.get('score', self.map.t_score)
            
            if self.map.phase == 'gameover':
                self._emit_match_end_event()
        
        # Сохраняем текущее состояние как предыдущее
        self.previous_state = data

    # ════════════════════════════════════════════════════════════
    # EMITTERS (СОБЫТИЯ)
    # ════════════════════════════════════════════════════════════

    def _emit_event(self, event_type: str, data: Dict = None):
        event = GameEvent(event_type=event_type, data=data or {})
        self.events_history.append(event)
        if self.event_callback:
            try:
                self.event_callback(event)
            except Exception as e:
                logger.error(f"[CS2 GSI] Ошибка callback: {e}")

    def _emit_kill_event(self, kill_count: int):
        self.kill_streak += kill_count
        self._emit_event('kill', {'kills': kill_count, 'round_kills': self.player.round_kills})

    def _emit_death_event(self):
        self.kill_streak = 0
        self._emit_event('death', {'total_deaths': self.player.deaths})

    def _emit_damage_event(self, damage: int):
        self._emit_event('damage', {'damage': damage, 'health': self.player.health})

    def _emit_round_start_event(self):
        self.kill_streak = 0
        self._emit_event('round_start', {'round': self.map.round})

    def _emit_round_end_event(self):
        self._emit_event('round_end', {'round': self.map.round})

    def _emit_bomb_planted_event(self):
        self._emit_event('bomb_planted', {})

    def _emit_bomb_defused_event(self):
        self._emit_event('bomb_defused', {})

    def _emit_bomb_exploded_event(self):
        self._emit_event('bomb_exploded', {})

    def _emit_match_end_event(self):
        self._emit_event('match_end', {'map': self.map.name})

    # ════════════════════════════════════════════════════════════
    # УПРАВЛЕНИЕ СЕРВЕРОМ
    # ════════════════════════════════════════════════════════════

    def start(self):
        if self.is_running:
            return
        
        self.is_running = True
        self.server_thread = threading.Thread(
            target=lambda: self.app.run(host='0.0.0.0', port=self.port, debug=False, use_reloader=False),
            daemon=True
        )
        self.server_thread.start()
        logger.info(f"[CS2 GSI] Сервер запущен на порту {self.port}")

    def stop(self):
        self.is_running = False

    def get_player_stats(self) -> Dict:
        return {
            'name': self.player.name,
            'team': self.player.team,
            'health': self.player.health,
            'kills': self.player.kills,
            'deaths': self.player.deaths
        }

    def get_match_info(self) -> Dict:
        return {
            'map': self.map.name,
            'round': self.map.round,
            'ct_score': self.map.ct_score,
            't_score': self.map.t_score
        }


def main():
    """Главная функция для запуска CS2 GSI сервера."""
    logger.info("\n" + "="*70)
    logger.info("[CS2 GSI] 🎮 Counter-Strike 2 Game State Integration")
    logger.info("="*70)
    
    # Инициализируем GSI
    gsi = CS2GameStateIntegration(port=3000)
    
    logger.info("[CS2 GSI] ✅ Инициализирован")
    logger.info("[CS2 GSI] 🚀 Запускаю сервер...")
    logger.info("[CS2 GSI] 📡 Слушаю события CS2 на :3000")
    logger.info("[CS2 GSI] ⌨️  Для выхода: Ctrl+C\n")
    
    gsi.start()
    
    try:
        # Просто держим процесс живым
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        logger.info("\n[CS2 GSI] Остановка сервера...")
        gsi.stop()
    finally:
        logger.info("[CS2 GSI] До свидания! 🎮")


if __name__ == '__main__':
    main()
