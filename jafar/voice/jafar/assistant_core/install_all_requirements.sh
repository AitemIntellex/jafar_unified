source ~/Projects/.venv/bin/activate
for req in $(find ~/Projects -type f -name "requirements.txt" -not -path "*/.venv/*"); do
    echo "Устанавливаем зависимости из $req"
    pip install -r "$req"
done
