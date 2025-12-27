import json
import time
import threading
from flask import Flask, request, jsonify
from dataclasses import dataclass, field
from typing import Optional, Callable, Dict, List, Any, Tuple
from collections import deque

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
                print(f"[CS2 GSI] Ошибка обработки: {e}")
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
        
        # ════════════════════════════════════════════════════════════
        # ✅ НОВОЕ: ОБРАБОТКА ВСЕХ ИГРОКОВ И ИХ ПОЗИЦИЙ
        # ════════════════════════════════════════════════════════════
        all_players_data = data.get('allplayers', {})
        if all_players_data:
            self.all_players_positions = {}
            self.all_players_states = {}
            
            for steamid, player_info in all_players_data.items():
                if steamid == self.player.name:  # Пропускаем себя
                    continue
                
                # Позиции врагов
                position = player_info.get('position', {})
                self.all_players_positions[steamid] = {
                    'x': position.get('x', 0),
                    'y': position.get('y', 0),
                    'z': position.get('z', 0),
                    'team': player_info.get('team', 'unknown'),
                    'name': player_info.get('name', 'unknown')
                }
                
                # Статус всех
                state = player_info.get('state', {})
                self.all_players_states[steamid] = {
                    'alive': state.get('health', 0) > 0,
                    'health': state.get('health', 0),
                    'team': player_info.get('team', 'unknown'),
                    'name': player_info.get('name', 'unknown')
                }
        
        # ════════════════════════════════════════════════════════════
        # ✅ НОВОЕ: ОБРАБОТКА ГРЕНАД
        # ════════════════════════════════════════════════════════════
        all_grenades_data = data.get('allgrenades', {})
        if all_grenades_data:
            self.all_grenades = []
            for grenade_id, grenade_info in all_grenades_data.items():
                self.all_grenades.append({
                    'type': grenade_info.get('type', 'unknown'),
                    'position': {
                        'x': grenade_info.get('position', {}).get('x', 0),
                        'y': grenade_info.get('position', {}).get('y', 0),
                        'z': grenade_info.get('position', {}).get('z', 0)
                    },
                    'team': grenade_info.get('team', 'unknown'),
                    'owner': grenade_info.get('owner', 'unknown')
                })
        
        # ════════════════════════════════════════════════════════════
        # ✅ НОВОЕ: ОБРАБОТКА ВРЕМЕНИ РАУНДА
        # ════════════════════════════════════════════════════════════
        phase_countdowns = data.get('phase_countdowns', {})
        if phase_countdowns:
            # phase_countdowns содержит информацию о времени разных фаз
            self.phase_countdown = phase_countdowns.get('phase', 0)
        
        # ✅ Сохраняем текущее состояние как предыдущее
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
                print(f"[CS2 GSI] Ошибка callback: {e}")

    def _emit_kill_event(self, kill_count: int):
        self.kill_streak += kill_count
        event_data = {
            'kills_this_action': kill_count,
            'round_kills': self.player.round_kills,
            'total_kills': self.player.kills,
            'kill_streak': self.kill_streak,
            'headshot': self.player.round_killhs > 0,
            'weapon': self.player.weapon,
            'clutch': self.clutch_situation,
            'clutch_enemies': self.clutch_enemies
        }
        
        if self.player.round_kills >= 5:
            event_data['ace'] = True
            self._emit_event('ace', event_data)
        elif self.player.round_kills >= 4:
            self._emit_event('quadra_kill', event_data)
        elif self.player.round_kills >= 3:
            self._emit_event('triple_kill', event_data)
        elif self.player.round_kills >= 2:
            self._emit_event('double_kill', event_data)
        else:
            self._emit_event('kill', event_data)

    def _emit_death_event(self):
        self.kill_streak = 0
        event_data = {
            'total_deaths': self.player.deaths,
            'kd_ratio': self.player.kills / max(1, self.player.deaths),
            'round': self.map.round
        }
        self._emit_event('death', event_data)

    def _emit_damage_event(self, damage: int):
        event_data = {
            'damage': damage,
            'current_health': self.player.health,
            'armor': self.player.armor
        }
        
        if self.player.health <= 25:
            self._emit_event('low_health', event_data)
        elif damage >= 50:
            self._emit_event('heavy_damage', event_data)

    def _emit_round_start_event(self):
        self.kill_streak = 0
        self.round_start_kills = self.player.kills
        self.clutch_situation = False
        event_data = {
            'round': self.map.round,
            'ct_score': self.map.ct_score,
            't_score': self.map.t_score,
            'money': self.player.money,
            'equip_value': self.player.equip_value
        }
        
        if self.player.money < 2000:
            event_data['eco_round'] = True
        
        self._emit_event('round_start', event_data)

    def _emit_round_end_event(self):
        round_kills = self.player.kills - self.round_start_kills
        event_data = {
            'round': self.map.round,
            'win_team': self.round.win_team,
            'player_team': self.player.team,
            'won': self.round.win_team.lower() == self.player.team.lower() if self.round.win_team else False,
            'round_kills': round_kills,
            'clutch_win': self.clutch_situation and round_kills > 0
        }
        
        if round_kills >= 3:
            event_data['mvp_candidate'] = True
        
        self._emit_event('round_end', event_data)

    def _emit_bomb_planted_event(self):
        event_data = {
            'round': self.map.round,
            'player_team': self.player.team
        }
        self._emit_event('bomb_planted', event_data)

    def _emit_bomb_defused_event(self):
        event_data = {
            'round': self.map.round,
            'player_team': self.player.team,
            'ninja_defuse': self.player.health <= 10
        }
        self._emit_event('bomb_defused', event_data)

    def _emit_bomb_exploded_event(self):
        event_data = {
            'round': self.map.round,
            'player_team': self.player.team
        }
        self._emit_event('bomb_exploded', event_data)

    def _emit_match_end_event(self):
        event_data = {
            'ct_score': self.map.ct_score,
            't_score': self.map.t_score,
            'player_team': self.player.team,
            'won': (self.player.team == 'CT' and self.map.ct_score > self.map.t_score) or
                   (self.player.team == 'T' and self.map.t_score > self.map.ct_score),
            'kills': self.player.kills,
            'deaths': self.player.deaths,
            'assists': self.player.assists,
            'mvps': self.player.mvps,
            'map': self.map.name
        }
        self._emit_event('match_end', event_data)

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
        print(f"[CS2 GSI] Сервер запущен на порту {self.port}")

    def stop(self):
        self.is_running = False

    # ════════════════════════════════════════════════════════════
    # МЕТОДЫ ПОЛУЧЕНИЯ ИНФОРМАЦИИ
    # ════════════════════════════════════════════════════════════

    def get_player_stats(self) -> Dict:
        return {
            'name': self.player.name,
            'team': self.player.team,
            'health': self.player.health,
            'armor': self.player.armor,
            'money': self.player.money,
            'kills': self.player.kills,
            'deaths': self.player.deaths,
            'assists': self.player.assists,
            'kd_ratio': round(self.player.kills / max(1, self.player.deaths), 2),
            'mvps': self.player.mvps,
            'score': self.player.score
        }

    def get_match_info(self) -> Dict:
        return {
            'map': self.map.name,
            'mode': self.map.mode,
            'round': self.map.round,
            'ct_score': self.map.ct_score,
            't_score': self.map.t_score,
            'phase': self.map.phase
        }

    # ✅ НОВЫЕ МЕТОДЫ ДЛЯ АНАЛИЗА

    def get_enemy_positions(self) -> List[Dict]:
        """Получить позиции всех врагов"""
        enemies = []
        for steamid, pos in self.all_players_positions.items():
            if pos['team'] != self.player.team:
                enemies.append(pos)
        return enemies

    def get_alive_enemies_count(self) -> int:
        """Сколько живых врагов"""
        count = 0
        for steamid, state in self.all_players_states.items():
            if state['alive'] and state['team'] != self.player.team:
                count += 1
        return count

    def get_grenades_nearby(self, distance: float = 500) -> List[Dict]:
        """Получить гренады рядом (в метрах)"""
        nearby = []
        for grenade in self.all_grenades:
            gx, gy = grenade['position']['x'], grenade['position']['y']
            px, py = self.player.position
            dist = ((gx - px)**2 + (gy - py)**2)**0.5
            if dist <= distance:
                nearby.append(grenade)
        return nearby

    def get_player_health_status(self) -> str:
        """Статус здоровья"""
        if self.player.health <= 1:
            return "critical"
        elif self.player.health <= 15:
            return "very_low"
        elif self.player.health <= 30:
            return "low"
        elif self.player.health <= 60:
            return "medium"
        else:
            return "healthy"

    def get_ammo_status(self) -> str:
        """Статус патронов"""
        total = self.player.ammo_in_magazine + self.player.ammo_in_reserve
        if total == 0:
            return "empty"
        elif total <= 3:
            return "critical"
        elif total <= 10:
            return "low"
        elif total <= 30:
            return "medium"
        else:
            return "plenty"

    def analyze_threat_level(self) -> int:
        """Уровень угрозы (1-10)"""
        threat = 5
        
        if self.player.health <= 15:
            threat += 5
        if (self.player.ammo_in_magazine + self.player.ammo_in_reserve) <= 5:
            threat += 2
        if self.player.money < 2000:
            threat += 1
        if self.get_alive_enemies_count() >= 3:
            threat += 2
        
        return min(threat, 10)

    def get_round_time_remaining(self) -> float:
        """Оставшееся время раунда в секундах"""
        return self.phase_countdown

    def generate_config_file(self) -> str:
        config = f'''\"Iris Stream Assistant v2.1\"
{{
	\"uri\" \"http://localhost:{self.port}/\"
	\"timeout\" \"5.0\"
	\"buffer\"  \"0.1\"
	\"throttle\" \"0.1\"
	\"heartbeat\" \"10.0\"
	
	\"auth\"
	{{
		\"token\" \"iris_stream_assistant\"
	}}
	
	\"data\"
	{{
		\"provider\"              \"1\"
		\"match_stats\"           \"1\"
		\"player_id\"             \"1\"
		\"player_state\"          \"1\"
		\"player_match_stats\"    \"1\"
		\"player_weapons\"        \"1\"
		\"player_position\"       \"1\"
		\"round\"                 \"1\"
		\"phase_countdowns\"      \"1\"
		\"bomb\"                  \"1\"
		\"map\"                   \"1\"
		\"map_round_wins\"        \"1\"
		\"allplayers_id\"         \"1\"
		\"allplayers_state\"      \"1\"
		\"allplayers_match_stats\"    \"1\"
		\"allplayers_weapons\"        \"1\"
		\"allplayers_position\"       \"1\"
		\"allgrenades\"           \"1\"
	}}
}}
'''
        return config

    def save_config_file(self, path: str = "gamestate_integration_iris.cfg"):
        config = self.generate_config_file()
        with open(path, 'w') as f:
            f.write(config)
        print(f"[CS2 GSI] Конфиг сохранён: {path}")
        print(f"[CS2 GSI] Скопируйте его в: /steamapps/common/Counter-Strike Global Offensive/game/csgo/cfg/")
        return path
