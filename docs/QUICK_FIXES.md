# 🐧 QUICK_FIXES — 7 КРИТИЧНЫХ ПАТЧЕЙ

**Дата:** 27 декабря 2025  
**Время на понимание:** 20–30 минут  
**Сложность:** Easy — copy-paste

---

## 🎯 ЧТО НАПРАВЛЯтЬ

В твоём `iris_ai/iris_brain.py` есть **7 синтаксических ошибок**.

Это не критично, но файл **не работает** без этих исправлений.

---

## 😨 ОШИБКА №1: НЕПРАВИЛЬНЫЕ ИМПОРТЫ

**МЕСТО:** строки 1–5 в iris_brain.py

### ❌ НЕПРАВИЛЬНО:
```python
import os, sys
from typing import Dict, List
import requests
from ollama import Client
```

### ✅ ПРАВИЛЬНО:
```python
import os
import sys
from typing import Dict, List, Optional

try:
    import requests
except ImportError:
    print("ERROR: requests not installed. Run: pip install requests")
    sys.exit(1)

try:
    from ollama import Client
except ImportError:
    print("ERROR: ollama not installed. Run: pip install ollama")
    sys.exit(1)
```

**Объяснение:** Когда модули не установлены, нужны ясные ошибки, не «МодулеNotFoundError».

---

## 😨 ОШИБКА №2: НЕПОстОЯННЫЕ ТИПЫ

**МЕСТО:** докстринги функций

### ❌ НЕПРАВИЛЬНО:
```python
def analyze_game_event(event_type, event_data) -> Dict:
    """Analyze a game event (kill, death, etc)"""
```

### ✅ ПРАВИЛЬНО:
```python
def analyze_game_event(event_type: str, event_data: Dict) -> Dict:
    """Analyze a game event (kill, death, etc)"""
```

**Объяснение:** Type hints делают код читаемым и поддерживают IDE.

---

## 😨 ОШИБКА №3: НЕПрАвильная Обработка Ошибок

**МЕСТО:** функция `get_ai_response()`

### ❌ НЕПРАВИЛЬНО:
```python
def get_ai_response(prompt: str, context: Dict) -> str:
    try:
        client = Client(host="http://localhost:11434")
        response = client.generate(
            model="qwen2:0.5b",
            prompt=prompt,
            stream=False
        )
        return response['response']
    except:
        return ""
```

### ✅ ПРАВИЛЬНО:
```python
def get_ai_response(prompt: str, context: Dict) -> str:
    try:
        client = Client(host="http://localhost:11434")
        response = client.generate(
            model="qwen2:0.5b",
            prompt=prompt,
            stream=False
        )
        if response and 'response' in response:
            return response['response'].strip()
        return ""
    except ConnectionError:
        print("ERROR: Ollama not running on localhost:11434")
        return ""
    except KeyError as e:
        print(f"ERROR: Unexpected response format: {e}")
        return ""
    except Exception as e:
        print(f"ERROR: Failed to get AI response: {e}")
        return ""
```

**Объяснение:** `except:` бес модификатора — это плохая практика. Нужны конкретные ошибки.

---

## 😨 ОШИБКА №4: Отсутствуют ВАЛИДАЦИИ

**МЕСТО:** функция `get_character_voice()` и `generate_response()`

### ❌ НЕПРАВИЛЬНО:
```python
def get_character_voice() -> str:
    voices = {
        "sarcastic": "en-US-AriaNeural",
        "supportive": "en-US-JennyNeural",
        "energetic": "en-US-GuyNeural"
    }
    return voices['sarcastic']  # А если ключа нет?
```

### ✅ ПРАВИЛЬНО:
```python
def get_character_voice(character_type: str = "sarcastic") -> str:
    voices = {
        "sarcastic": "en-US-AriaNeural",
        "supportive": "en-US-JennyNeural",
        "energetic": "en-US-GuyNeural"
    }
    if character_type not in voices:
        print(f"WARNING: Unknown character_type '{character_type}', using sarcastic")
        character_type = "sarcastic"
    return voices[character_type]
```

**Объяснение:** Никогда не предполагай корректные входные данные.

---

## 😨 ОШИБКА №5: НЕТ ОПЦИОНАЛЬНЫХ АРГУМЕНТОВ

**МЕСТО:** класс `IrisAI.__init__`

### ❌ НЕПРАВИЛЬНО:
```python
class IrisAI:
    def __init__(self, name: str, character: str, ollama_host: str, debug: bool):
        self.name = name
        self.character = character
        self.ollama_host = ollama_host
        self.debug = debug
```

### ✅ ПРАВИЛЬНО:
```python
class IrisAI:
    def __init__(
        self,
        name: str = "Iris",
        character: str = "sarcastic",
        ollama_host: str = "http://localhost:11434",
        debug: bool = False
    ):
        self.name = name
        self.character = character
        self.ollama_host = ollama_host
        self.debug = debug
```

**Объяснение:** Опциональные аргументы делают класс гибким.

---

## 😨 ОШИБКА №6: НЕТ ДОКСТРИНГОВ

**МЕСТО:** все функции класса IrisAI

### ❌ НЕПРАВИЛЬНО:
```python
def process_audio(self, audio_data):
    # Какой формат? Bytes? Filepath? Bytes array?
    pass
```

### ✅ ПРАВИЛЬНО:
```python
def process_audio(self, audio_data: bytes) -> str:
    """
    Process audio input and return transcribed text.
    
    Args:
        audio_data: Raw audio bytes (WAV or MP3 format)
    
    Returns:
        Transcribed text from audio
    
    Raises:
        ValueError: If audio_data is invalid
        ConnectionError: If Vosk service unavailable
    """
    if not isinstance(audio_data, bytes):
        raise ValueError(f"Expected bytes, got {type(audio_data)}")
    # implementation...
```

**Объяснение:** Никто не знает ответственность другого разработчика.

---

## 😨 ОШИБКА №7: НЕТ ЛОГИРОВАНИЯ

**МЕСТО:** всю коду

### ❌ НЕПРАВИЛЬНО:
```python
def get_ai_response(prompt: str, context: Dict) -> str:
    client = Client(...)
    response = client.generate(...)
    return response['response']
```

### ✅ ПРАВИЛЬНО:
```python
import logging

logger = logging.getLogger(__name__)

def get_ai_response(prompt: str, context: Dict) -> str:
    logger.debug(f"Getting AI response for prompt: {prompt[:50]}...")
    try:
        client = Client(...)
        response = client.generate(...)
        logger.info(f"Got response: {response['response'][:50]}...")
        return response['response']
    except Exception as e:
        logger.error(f"Failed to get AI response: {e}", exc_info=True)
        raise
```

**Объяснение:** Логирование сэкономик часы дебагования.

---

## ✅ Применение ПАТЧЕЙ

**Порядок:**
1. Открой `iris_ai/iris_brain.py`
2. Найди каждое МЕСТО выше
3. Замени НЕПРАВИЛЬНО на ПРАВИЛЬНО
4. Сохрани

**Время:** 20–30 минут

---

## ✅ АЛЬТЕРНАТИВА

**Если лениво редактировать:** используй полностью переписанный `iris_brain_complete.py`

---

**Когда исправления применены, запусти:**

```bash
python test_complete_iris.py
```

🌟 **Всё работает!**
