# 🧘 Tazala — Telegram Info-Detox Bot

> Сброс 100k+ непрочитанных, авто-папки, Wrapped-карточка — всё через Telegram-бота.

## 🔥 Что делает

- **QR-авторизация** — безопасный вход без номера телефона
- **Сканирование** — анализ всех диалогов (мёртвые, зомби, активные)
- **Кнопка Дзен** — обнуление непрочитанных + создание умных папок
- **Wrapped-карточка** — красивая статистика для шаринга

## 🏗 Стек

- Python 3.12 + FastAPI + Telethon (MTProto)
- aiogram 3 (Telegram Bot)
- Redis (ephemeral sessions)
- Docker Compose

## 🚀 Быстрый старт

```bash
cp .env.example .env
# Заполнить .env своими ключами
docker compose up
```

## 🔒 Безопасность

- Сессии живут только в Redis (TTL 5 мин)
- `client.log_out()` после каждой операции
- Zero-Knowledge: ничего не сохраняется на диск

## 📄 Лицензия

MIT
