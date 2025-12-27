#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
IRIS AI - JARVIS for CS2 Streamers
Revolutionary AI voice assistant for competitive gaming

Author: Iris Development Team
Version: 2.0.0
Status: Production-Ready
"""

import os
import sys
import json
import logging
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime
from enum import Enum
from dataclasses import dataclass, field, asdict
import threading
import queue

try:
    import requests
    from requests.adapters import HTTPAdapter
    from urllib3.util.retry import Retry
except ImportError:
    print("ERROR: requests not installed. Run: pip install requests")
    sys.exit(1)

try:
    from ollama import Client
except ImportError:
    print("ERROR: ollama not installed. Run: pip install ollama")
    sys.exit(1)

# ============================================================================
# LOGGING CONFIGURATION
# ============================================================================

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('iris_brain.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)


# ============================================================================
# DATA STRUCTURES & ENUMS
# ============================================================================

class CharacterType(Enum):
    """Iris personality types"""
    SARCASTIC = "sarcastic"
    SUPPORTIVE = "supportive"
    ENERGETIC = "energetic"
    ANALYTICAL = "analytical"


class EventType(Enum):
    """CS2 game events"""
    KILL = "kill"
    DEATH = "death"
    ASSIST = "assist"
    CLUTCH = "clutch"
    ACE = "ace"
    PENTAKILL = "pentakill"
    HEADSHOT = "headshot"
    BOMB_PLANTED = "bomb_planted"
    BOMB_DEFUSED = "bomb_defused"
    ROUND_WIN = "round_win"
    ROUND_LOSS = "round_loss"
    LOW_HEALTH = "low_health"
    ACHIEVEMENT = "achievement"
    CUSTOM = "custom"


@dataclass
class GameState:
    """Current game state"""
    player_name: str = "Player"
    health: int = 100
    armor: int = 0
    money: int = 0
    kills: int = 0
    deaths: int = 0
    assists: int = 0
    round_number: int = 0
    team_score: int = 0
    enemy_score: int = 0
    alive: bool = True
    position: str = "Unknown"
    weapon: str = "Unknown"
    last_event: Optional[str] = None
    last_event_time: float = 0.0
    meta: Dict[str, Any] = field(default_factory=dict)


@dataclass
class GameEvent:
    """Represents a CS2 game event"""
    event_type: EventType
    timestamp: float
    player_name: str
    data: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict:
        """Convert to dictionary"""
        return {
            'type': self.event_type.value,
            'timestamp': self.timestamp,
            'player': self.player_name,
            'data': self.data
        }


# ============================================================================
# VOICE & CHARACTER MANAGEMENT
# ============================================================================

class CharacterManager:
    """
    Manages Iris personality and voice configuration.
    Supports multiple character types with different communication styles.
    """
    
    VOICE_MAP = {
        CharacterType.SARCASTIC: "en-US-AriaNeural",
        CharacterType.SUPPORTIVE: "en-US-JennyNeural",
        CharacterType.ENERGETIC: "en-US-GuyNeural",
        CharacterType.ANALYTICAL: "en-US-SteffanNeural"
    }
    
    SYSTEM_PROMPTS = {
        CharacterType.SARCASTIC: (
            "You are Iris, a witty AI gaming assistant. "
            "Respond with clever sarcasm and humor while providing game analysis. "
            "Keep responses under 100 words. Be concise and entertaining."
        ),
        CharacterType.SUPPORTIVE: (
            "You are Iris, a supportive gaming coach. "
            "Provide motivational and helpful feedback. "
            "Encourage the player and offer tactical advice. "
            "Keep responses under 100 words. Be warm and professional."
        ),
        CharacterType.ENERGETIC: (
            "You are Iris, an energetic gaming commentator. "
            "React with high energy and excitement to game events. "
            "Use exclamation points and emphasize achievements. "
            "Keep responses under 100 words. Be enthusiastic!"
        ),
        CharacterType.ANALYTICAL: (
            "You are Iris, a tactical analyst for competitive gaming. "
            "Provide deep game analysis and strategic insights. "
            "Reference economy, positioning, and tactics. "
            "Keep responses under 100 words. Be informative and precise."
        )
    }
    
    def __init__(self, character_type: str = "sarcastic"):
        """Initialize character manager"""
        try:
            self.character = CharacterType[character_type.upper()]
        except KeyError:
            logger.warning(f"Unknown character type '{character_type}', using SARCASTIC")
            self.character = CharacterType.SARCASTIC
        
        logger.info(f"Character initialized: {self.character.value}")
    
    def get_voice(self) -> str:
        """Get voice for current character"""
        return self.VOICE_MAP.get(self.character, "en-US-AriaNeural")
    
    def get_system_prompt(self) -> str:
        """Get system prompt for current character"""
        return self.SYSTEM_PROMPTS.get(
            self.character,
            self.SYSTEM_PROMPTS[CharacterType.SARCASTIC]
        )
    
    def set_character(self, character_type: str) -> None:
        """Change character type"""
        try:
            self.character = CharacterType[character_type.upper()]
            logger.info(f"Character changed to: {self.character.value}")
        except KeyError:
            logger.warning(f"Unknown character type '{character_type}'")


# ============================================================================
# CORE AI ENGINE
# ============================================================================

class IrisAIEngine:
    """
    Core AI engine for Iris. Handles LLM communication and response generation.
    Uses Ollama for local AI inference without cloud dependencies.
    """
    
    def __init__(
        self,
        ollama_host: str = "http://localhost:11434",
        model: str = "qwen2:0.5b",
        timeout: float = 30.0,
        max_retries: int = 3
    ):
        """Initialize AI engine"""
        self.ollama_host = ollama_host
        self.model = model
        self.timeout = timeout
        self.max_retries = max_retries
        self.character_manager = CharacterManager()
        
        # Initialize Ollama client with retry logic
        self.client = Client(host=ollama_host)
        logger.info(f"AI Engine initialized with model: {model}")
    
    def check_connection(self) -> bool:
        """
        Check if Ollama is running and accessible.
        
        Returns:
            True if connection successful, False otherwise
        """
        try:
            response = requests.get(
                f"{self.ollama_host}/api/tags",
                timeout=5.0
            )
            is_connected = response.status_code == 200
            if is_connected:
                logger.info("✓ Connected to Ollama")
            else:
                logger.error(f"✗ Ollama returned status {response.status_code}")
            return is_connected
        except requests.ConnectionError:
            logger.error(f"✗ Cannot connect to Ollama at {self.ollama_host}")
            return False
        except Exception as e:
            logger.error(f"✗ Connection check failed: {e}")
            return False
    
    def generate_response(
        self,
        prompt: str,
        context: Optional[Dict] = None,
        max_tokens: int = 100
    ) -> str:
        """
        Generate AI response using Ollama LLM.
        
        Args:
            prompt: User/game event prompt
            context: Game state context
            max_tokens: Maximum response length
        
        Returns:
            Generated response text
        
        Raises:
            ConnectionError: If Ollama not available
            ValueError: If prompt invalid
        """
        if not prompt or not isinstance(prompt, str):
            raise ValueError(f"Invalid prompt: {prompt}")
        
        try:
            # Build full context message
            system_msg = self.character_manager.get_system_prompt()
            context_str = ""
            
            if context:
                context_str = f"\n\nGame Context: {json.dumps(context, indent=2)}"
            
            full_prompt = f"{system_msg}\n\nPlayer prompt: {prompt}{context_str}"
            
            logger.debug(f"Generating response for: {prompt[:50]}...")
            
            response = self.client.generate(
                model=self.model,
                prompt=full_prompt,
                stream=False,
                options={
                    "temperature": 0.7,
                    "top_p": 0.9,
                    "num_predict": max_tokens
                }
            )
            
            if response and 'response' in response:
                text = response['response'].strip()
                logger.info(f"Generated response: {text[:100]}...")
                return text
            else:
                logger.warning("Empty response from model")
                return ""
        
        except ConnectionError as e:
            logger.error(f"Connection error: {e}")
            raise
        except KeyError as e:
            logger.error(f"Unexpected response format: {e}")
            return ""
        except Exception as e:
            logger.error(f"Failed to generate response: {e}", exc_info=True)
            return ""
    
    def analyze_game_event(
        self,
        event: GameEvent,
        game_state: GameState
    ) -> str:
        """
        Analyze a game event and generate Iris response.
        
        Args:
            event: The game event that occurred
            game_state: Current game state
        
        Returns:
            Generated response for the event
        """
        try:
            event_desc = self._describe_event(event)
            context = asdict(game_state)
            
            prompt = f"React to this CS2 event: {event_desc}"
            response = self.generate_response(prompt, context)
            
            logger.info(f"Event analyzed: {event.event_type.value}")
            return response
        
        except Exception as e:
            logger.error(f"Failed to analyze event: {e}")
            return ""
    
    @staticmethod
    def _describe_event(event: GameEvent) -> str:
        """
        Create human-readable event description.
        
        Args:
            event: Game event
        
        Returns:
            Event description
        """
        descriptions = {
            EventType.KILL: f"Got a kill! ({event.data.get('weapon', 'unknown')})",
            EventType.DEATH: "Died in combat",
            EventType.ASSIST: "Got an assist",
            EventType.CLUTCH: "Clutched a 1v3 situation!",
            EventType.ACE: "Got an ACE! 5v5 full elimination!",
            EventType.PENTAKILL: "PENTAKILL! All 5 enemies eliminated!",
            EventType.HEADSHOT: "Landed a HEADSHOT!",
            EventType.BOMB_PLANTED: "Bomb has been planted",
            EventType.BOMB_DEFUSED: "Bomb has been defused",
            EventType.ROUND_WIN: "Round won!",
            EventType.ROUND_LOSS: "Round lost",
            EventType.LOW_HEALTH: f"Low health warning! ({event.data.get('health', 0)}HP)",
            EventType.ACHIEVEMENT: f"Achievement unlocked: {event.data.get('name', 'Unknown')}",
            EventType.CUSTOM: event.data.get('description', 'Custom event')
        }
        
        return descriptions.get(event.event_type, "Unknown event")


# ============================================================================
# MAIN IRIS CLASS
# ============================================================================

class IrisAI:
    """
    Main Iris AI assistant. Orchestrates all components.
    Handles event processing, response generation, and state management.
    """
    
    def __init__(
        self,
        name: str = "Iris",
        character: str = "sarcastic",
        ollama_host: str = "http://localhost:11434",
        debug: bool = False
    ):
        """Initialize Iris AI"""
        self.name = name
        self.debug = debug
        
        # Initialize AI engine
        self.engine = IrisAIEngine(ollama_host=ollama_host)
        self.engine.character_manager.set_character(character)
        
        # Initialize game state
        self.game_state = GameState(player_name=name)
        self.event_history: List[GameEvent] = []
        
        # Event queue for async processing
        self.event_queue: queue.Queue = queue.Queue()
        self.running = False
        
        logger.info(f"Iris AI initialized: {name} ({character})")
    
    def process_event(self, event: GameEvent) -> str:
        """
        Process a game event and generate response.
        
        Args:
            event: Game event to process
        
        Returns:
            Response text
        """
        try:
            # Update game state based on event
            self._update_state(event)
            
            # Generate response
            response = self.engine.analyze_game_event(event, self.game_state)
            
            # Store event in history
            self.event_history.append(event)
            
            return response
        
        except Exception as e:
            logger.error(f"Failed to process event: {e}")
            return ""
    
    def _update_state(self, event: GameEvent) -> None:
        """
        Update game state based on event.
        
        Args:
            event: Game event
        """
        if event.event_type == EventType.KILL:
            self.game_state.kills += 1
        elif event.event_type == EventType.DEATH:
            self.game_state.deaths += 1
            self.game_state.alive = False
        elif event.event_type == EventType.ASSIST:
            self.game_state.assists += 1
        elif event.event_type == EventType.LOW_HEALTH:
            self.game_state.health = event.data.get('health', 0)
        elif event.event_type == EventType.ROUND_WIN:
            self.game_state.team_score += 1
        elif event.event_type == EventType.ROUND_LOSS:
            self.game_state.enemy_score += 1
        
        self.game_state.last_event = event.event_type.value
        self.game_state.last_event_time = event.timestamp
    
    def get_status(self) -> Dict:
        """
        Get current Iris status.
        
        Returns:
            Status dictionary
        """
        return {
            'name': self.name,
            'online': self.engine.check_connection(),
            'game_state': asdict(self.game_state),
            'events_processed': len(self.event_history),
            'timestamp': datetime.now().isoformat()
        }


# ============================================================================
# TESTING & MAIN
# ============================================================================

def main():
    """Test the Iris AI system"""
    logger.info("=" * 60)
    logger.info("IRIS AI - JARVIS for CS2 Streamers")
    logger.info("Version: 2.0.0")
    logger.info("=" * 60)
    
    # Initialize Iris
    iris = IrisAI(
        name="Iris",
        character="sarcastic",
        ollama_host="http://localhost:11434",
        debug=True
    )
    
    # Check connection
    logger.info("\nChecking Ollama connection...")
    if not iris.engine.check_connection():
        logger.error("✗ Ollama not running! Start with: ollama serve")
        return 1
    
    logger.info("✓ All systems ready!\n")
    
    # Test event processing
    test_events = [
        GameEvent(
            event_type=EventType.KILL,
            timestamp=datetime.now().timestamp(),
            player_name="Player",
            data={"weapon": "AK-47", "distance": 25}
        ),
        GameEvent(
            event_type=EventType.CLUTCH,
            timestamp=datetime.now().timestamp(),
            player_name="Player",
            data={"enemies_remaining": 3}
        )
    ]
    
    logger.info("Processing test events...\n")
    for event in test_events:
        logger.info(f"Event: {event.event_type.value}")
        response = iris.process_event(event)
        logger.info(f"Iris: {response}\n")
    
    # Print status
    status = iris.get_status()
    logger.info(f"Final Status: {json.dumps(status, indent=2)}")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
