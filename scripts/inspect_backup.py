"""Inspecciona un archivo backup.json."""
import json
import sys
from pathlib import Path

p = Path(sys.argv[1])
d = json.load(p.open(encoding="utf-8"))
print("version:", d.get("version"))
print("created_at:", d.get("created_at"))
print("users:", len(d.get("users", [])))
print("participants:", len(d.get("participants", [])))
print("predictions:", len(d.get("predictions", [])))
print("position_predictions:", len(d.get("position_predictions", [])))
print()
print("--- PARTICIPANTS ---")
for item in d.get("participants", []):
    print(" ", item.get("nombre"), "|", item.get("email"))
print()
linked = sum(1 for u in d.get("users", []) if u.get("participant_email"))
print(f"users with participant_email: {linked}/{len(d.get('users', []))}")
