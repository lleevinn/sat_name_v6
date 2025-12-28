# 🛳 ПОЛНАЯ ФАЙЛОВАЯ СТРОКТУРА IRIS

## 📄 Обзор

VERBOSE README для тех, кто хочет всё понять с нуля.

---

## 📄 ФАЙЛОВАЯ СТРОКТУРА

```
sit_name_v6/
├─── README.md
├─── SYSTEM_MEMORY_RESTORE.md              🖐 гВОБОДНЫЙ: восстановление контекста
├─── requirements.txt                     зависимости Python
├─── pyproject.toml                       метаданные проекта
├─── setup.py                            установка
├─── uv.lock                             фиксация версий
├─── .env.example                        образец .env
├─── .gitignore
├─── 📄 docs/                               вся документация
│  ├─ 00_MAIN_SYSTEM_PROMPT.md              👋 👋 👋 📄 НАНО тО ДО ПОНиМая в новом чате
│  ├─ CHECKPOINT.md                       📄 текущее состояние живого данные
│  ├─ NEXT_SESSION_START.md               ✅ ПРИОРИТЕТЫ таск для при старте
│  ├─ PROJECT_MASTER_CONTEXT.md           🛰 СООО КА архитектура
│  ├─ DEV_LOG.md                          📅 история наработок
│  ├─ IRIS_PROJECT_VISION.md              🌸 ВИДЕНИЕ КОНЦЕПЦИИ
│  ├─ MEMORY_BANK.md                      🧠 гЛАВНЫЕ принципы (фиксед)
│  ├─ QUICK_FIXES.md                      😨 быстрые патчи
│  ├─ VOICE_SETUP.md                      🎤 как установить голос
│  ├─ PROJECT_STRUCTURE.md                🛳 ЭТОТ ФАЙЛ
│  ├── 00_START_HERE_NAVIGATION.md         навигация (если получился полутер)
│  ├─ START_HERE.md                       быстрый старт
│  ├─ 00_ЧИТАЙ_ЭТОТ_ФАЙЛ_ПЕРВЫМ.md  введение
│  └─ README_ПОНИМАНИЕ.md              что я понял
├─── 💕 src/                                 ОСНОВНОЙ КОД
│  ├─ iris_brain.py                       ᾞ0 МОЗГ (анализ атак и реакции)
│  ├─ cs2_gsi.py                          Ἲe GSI listener для CS2 (ПОЛНО)
│  ├─ voice_input.py                      🎤 всё для голоса (запись, распоз)
│  ├─ tts_engine.py                       🔊 синтез речи
│  ├─ prompt_builder.py                   ❓ конструктор посылающих
│  ├─ context_builder.py                  🌲 анализ ситуации в игре
⌂  ├─ achievements.py                     🎆 достижения
│  ├─ statistics_tracker.py               📊 статистика
⌂  ├─ session_memory.py                   🧰 память про грру
⌂  ├─ queue_manager.py                    🚚 ждание ответов от LLM
⌂  ├─ iris_smart_engine.py                🧠 регулятор экономиъ лстреости
⌂  ├─ iris_visual.py                      🜟 визуализация
⌂  ├─ streamelements_client.py             🎉 интеграция StreamElements
⌂  ├─ windows_audio.py                    👠💻 Windows audio API
⌂  ├─ voice_recognition.py                🌲 распоз речи
⌂  ├─ utils/                              спомогательные
⌂  └─ iris_core/                          эксперименты
├─── 😨 iris_ai/                             ПОНЫТКИ / ДЕМО
│  ├─ iris_main.py                       демо
│  ├─ iris_launcher.py                    до что работает
│  ├─ iris_server.py                      flask сервер
⌂  ├─ iris_tts_integration.py             тесты TTS
⌂  ├─ iris_speech_recognition.py          тесты голоса
⌂  └─ *.md                                документация (как работать)
└─── 📂 attached_assets/                   прикрепленные ассеты
```

---

## 📄 КАК НАВИГИРОВАТЬ?

### 🌸 ЕСЛИ НОВОе ЛЮБОМ

1. **`docs/00_MAIN_SYSTEM_PROMPT.md`** → скопирать в старт промпта
2. **`docs/NEXT_SESSION_START.md`** → делать работу
3. **`docs/PROJECT_MASTER_CONTEXT.md`** → восполнительно

### 📅 ЕСЛИ НУЖНО ОСВОМКА КОДА

1. **`docs/QUICK_FIXES.md`** → патчи для iris_brain.py
2. **`docs/VOICE_SETUP.md`** → как поднять голос

### 🌟 ЕСЛИ НУЖНО НАБОРОМ КОНТЕКСТА

1. **`docs/IRIS_PROJECT_VISION.md`** → всеї деталь
2. **`docs/MEMORY_BANK.md`** → гдавные принципы

### 🖐 ЕСЛИ СВАЛКА КОНТЕКСТА

**`SYSTEM_MEMORY_RESTORE.md`** → воскреси всё данные

---

## 📄 ФАЙЛЫ ДЛЯ ПОМОЩИ (optional)

Находятся в **`iris_ai/`**:

| Файл | Что это |
|---|---|
| `HOW_TO_RUN.md` | Как днапустить |
| `IRIS_QUICK_START.md` | Ускоренный старт |
| `IRIS_SERVER_README.md` | инфо о сервере |

---

**Всё чисто. Готово к работе.** 🌸
