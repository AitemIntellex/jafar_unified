#!/bin/bash

# 📄 os_scripts/generate_structure.sh

OUTPUT_FILE="$HOME/Projects/jafar_v2/generated_files/project_structure.md"
TARGET_DIR="$HOME/Projects/jafar_v2"

echo "📦 Структура проекта Jafar (обновлено: $(date))" > "$OUTPUT_FILE"
echo '```' >> "$OUTPUT_FILE"
tree -a -L 3 "$TARGET_DIR" >> "$OUTPUT_FILE"
echo '```' >> "$OUTPUT_FILE"

echo "✅ Структура обновлена: $OUTPUT_FILE"
