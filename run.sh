uv run python main.py $(xwininfo -int -name "Counter-Strike 2" | grep -oP "(?<=Window id: )\d+")
