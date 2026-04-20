from src.server import generate_pir
import json

print("calling generate_pir...")
result = generate_pir.fn(
    scope="APT29 attacks against Norwegian infrastructure",
    timeframe="last 6 months",
    target_entities=["Norway"],
    perspectives=["neutral"],
    threat_actors=["APT29"],
    priority_focus="attack vectors",
)
print(json.dumps(json.loads(result), indent=2))
