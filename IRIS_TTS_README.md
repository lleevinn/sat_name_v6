# 🎤 IRIS TTS Emotion Engine

**IRIS с женским голосом, эмоциями и живым диалогом!**

> Ето JARVIS для CS2! 😂

---

## ✨ Основные фичи

### 1. 🔊 Женский голос
- **Бархатный**, нежный, приятный
- Поддерживает русский язык
- Открывает системные голоса (TTS)

### 2. 😮 Шесть эмоций

| Эмоция | Скорость | Громкость | Описание |
|---|---|---|---|
| **CALM** | 150 | 0.8 | Спокойная, медленная |
| **NORMAL** | 170 | 0.85 | Обычная, стандартная |
| **EXCITED** | 200 | 0.95 | Восторженная, быстрая |
| **URGENT** ⚠️ | 220 | 1.0 | КРИТИЧЕСКАЯ, макс быстрая |
| **WORRIED** | 140 | 0.75 | Озабоченная, печальная |
| **FLIRTY** | 160 | 0.9 | Заигрывающая, теплая |

### 3. 🛫 Приоритетная очередь

```python
Priority 1: low_health      ⚠️  КРИТИЧЕСКОЕ
Priority 2: low_ammo        ⚠️  КРИТИЧЕСКОЕ
Priority 3: death           🔴 Важное
Priority 4: double/triple   🔴 Важное
Priority 5: kill            🔢 Обычное
```

**Критические события всегда говорятся ПЕРВЫМИ!**

### 4. 🐀 Контекстная память

- Помнит всю историю разговора
- Знает текущие состояние игры
- Не повторяется
- Учитывает статистику эмоций

### 5. 🎮 Осы еваю все эмоции

- Кура тона в зависимости от ситуации
- Модифицирует скорость речи
- Читает звук драматично

---

## 🚀 Квикстарт (Локально)

### Установка зависимостей

```bash
pip install pyttsx3
```

### На Windows

```bash
pip install pyttsx3 pypiwin32
python -m pip install --upgrade pyttsx3
```

### На Linux

```bash
sudo apt-get install espeak
pip install pyttsx3
```

### На macOS

```bash
brew install espeak
pip install pyttsx3
```

---

## 📄 Модули

### 1. `iris_tts_emotion.py` ✨

**Основной TTS Engine** с женским голосом и эмоциями.

**Основные классы:**

```python
from iris_tts_emotion import IRISTTSEngine, EmotionType

# Создание IRIS
iris = IRISTTSEngine()

# Звук инициализации
iris.init_sound()

# Ответ на убийство
iris.on_kill({'weapon': 'AWP', 'headshot': True, 'round_kills': 1})

# Выждать окончания
iris.wait_for_speech()
```

### 2. `iris_tts_integration.py` 🔗

**Интеграция** TTS Engine с обработчиком событий.

**Основные классы:**

```python
from iris_tts_integration import IRISGameEventListener

# Создание слушателя
listener = IRISGameEventListener()

# Обработка событиям
listener.process_kill_event({'weapon': 'AK-47', 'headshot': True, 'round_kills': 1})
listener.process_death_event({'kd_ratio': 1.5})
listener.process_low_health_event({'current_health': 15, 'armor': 25})
listener.process_low_ammo_event({'weapon': 'AK-47', 'ammo_magazine': 3})

# Включить молчание для сосредоточения
listener.enable_silence(duration=10.0)

# А на наиболее критические ее эмоции всеравно говорят 😂
```

---

## 📜 Поддерживаемые события

| Событие | Приоритет | Эмоция | Описание |
|---|---|---|---|
| **kill** | 5 | EXCITED | Поны убийства |
| **double_kill** | 4 | EXCITED | Двойное убийство |
| **triple_kill** | 3 | EXCITED | Тройное убийство |
| **death** | 4 | CALM | Навернюка и поддержка |
| **low_health** | 1 | URGENT | Мало жизни 🔴 |
| **low_ammo** | 2 | URGENT | Мало патронов 🔴 |
| **game_start** | 5 | EXCITED | Начало раунда |
| **round_end** | 5 | EXCITED/CALM | Конец раунда |
| **custom** | 5 | NORMAL | Пользовательское |

---

## 👮 Кодовые примеры

### Пример 1: Основные события

```python
from iris_tts_emotion import IRISTTSEngine, EmotionType
import time

iris = IRISTTSEngine()
iris.init_sound()

# Убийство с headshot
time.sleep(1)
iris.on_kill({
    'weapon': 'AWP',
    'headshot': True,
    'round_kills': 1
})
iris.wait_for_speech()

# Двойное убийство
time.sleep(1)
iris.on_kill({
    'weapon': 'AK-47',
    'headshot': False,
    'round_kills': 2
})
iris.wait_for_speech()

# Чрезвычайно низкое здоровье
time.sleep(1)
iris.on_low_health({
    'current_health': 5,
    'armor': 0
})
iris.wait_for_speech()
```

### Пример 2: Молчание в критические моменты

```python
from iris_tts_integration import IRISGameEventListener
import time

listener = IRISGameEventListener()

# Вораг рядом - включить молчание
listener.enable_silence(duration=10.0)

# Но IRIS всеравно поступит в случае КРИТИЧЕСКого низкого HP
listener.process_low_health_event({
    'current_health': 12,
    'armor': 0
})  # Это вОСПОДИТЕТСЯ даже в молчании!
listener.wait_for_speech()

# Отключить молчание
listener.disable_silence()
```

### Пример 3: Кастомные сообщения с эмоциями

```python
from iris_tts_emotion import IRISTTSEngine

iris = IRISTTSEngine()

# Теплые комплименты
iris.on_custom_message(
    "Ты прався как девушка-киравца! Никто так не плайит!",
    emotion_name='flirty'
)
```

---

## 📊 Получение статистики

```python
from iris_tts_integration import IRISGameEventListener

listener = IRISGameEventListener()

# Процесс нескольких событий...
listener.process_kill_event({'weapon': 'AWP', 'headshot': True, 'round_kills': 1})
listener.process_low_health_event({'current_health': 25, 'armor': 50})

# Получить статистику
stats = listener.get_stats()
print(f"Всего сообщений: {stats['total_messages']}")
print(f"Уникальные эмоции: {stats['emotion_distribution']}")
print(f"Последнее сообщение: {stats['last_message']['text']}")
```

---

## 🌟 Дальные планы

### Етап 2: Speech Recognition 🎬
- распознавание речи игрока
- Понимание команд
- Інтерактивные диалоги

### Етап 3: CS2 GSI Integration 🎮
- Подключение к реальным событиям игры
- Динамические ответы
- Контекстные подсказки

### Етап 4: Advanced Personality 😎
- Шутки и высмеяния
- Тактические подсказки
- Предсказания следующих действий

---

## 🛠️ Настройка женского голоса

### Windows (SAPI5)

Голоса устанавливаются автоматически. Проверьте:

```python
import pyttsx3
engine = pyttsx3.init()
voices = engine.getProperty('voices')
for voice in voices:
    print(f"{voice.id}: {voice.name}")
```

### Linux (eSpeak)

```bash
sudo apt-get install espeak espeak-ng
```

### macOS (NSSpeechSynthesizer)

Голоса тут бесплатные.

---

## 👋 Нужна помощь?

**Открыто репозиторию:**
- 📕 [sat_name_v6](https://github.com/lleevinn/sat_name_v6)

**Основные файлы:**
- `iris_ai/iris_tts_emotion.py` - Основной энджин
- `iris_ai/iris_tts_integration.py` - Интеграция
- `test_iris_tts.py` - тесты

---

## 🙋 Спасибо что пользуете IRIS! 👋

**IRIS - это не просто бот, это твой помощник в игре! 🌟**
