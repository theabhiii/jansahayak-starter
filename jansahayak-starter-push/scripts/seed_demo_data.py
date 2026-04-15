from pathlib import Path
import json

path = Path(__file__).resolve().parents[1] / "apps" / "api" / "app" / "data" / "schemes.json"
records = json.loads(path.read_text(encoding="utf-8"))
print(f"Loaded {len(records)} scheme records from {path}")
