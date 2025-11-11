#!/bin/bash

set -e  # Остановиться при ошибке

PROJECT_DIR="$(pwd)"
VENV_DIR="$PROJECT_DIR/.venv"

echo "📁 Проект: $PROJECT_DIR"
echo "🐍 Проверка Python..."

PYTHON_BIN=$(which python3 || which python)
if [[ -z "$PYTHON_BIN" ]]; then
  echo "❌ Python не найден. Установи Python 3.x."
  exit 1
fi

echo "✅ Python найден: $PYTHON_BIN"

# Создание .venv
if [ -d "$VENV_DIR" ]; then
  echo "ℹ️  Виртуальное окружение уже существует: $VENV_DIR"
else
  echo "⚙️  Создаём виртуальное окружение..."
  $PYTHON_BIN -m venv .venv
fi

# Активация
echo "🚀 Активируем окружение..."
source "$VENV_DIR/bin/activate"

# Установка зависимостей из всех *_require*.txt файлов
REQUIREMENT_FILES=$(find "$PROJECT_DIR" -maxdepth 1 -type f -iname "*require*.txt")

if [ -z "$REQUIREMENT_FILES" ]; then
  echo "⚠️  Файлы с зависимостями не найдены."
else
  for file in $REQUIREMENT_FILES; do
    echo "📦 Установка зависимостей из: $file"
    pip install -r "$file"
  done
fi

# Готово
echo "✅ Всё готово! Окружение активировано."
echo "💡 Используй: source .venv/bin/activate"
