uv run python main.py --sensitivity 1 $(xwininfo -int -name "Counter-Strike 2" | grep -oP "(?<=Window id: )\d+")
