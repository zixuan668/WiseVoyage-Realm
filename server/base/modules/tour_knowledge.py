"""Reviewed scenic dossiers, usable without a remote model or a running database."""
import json
from functools import lru_cache
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]


@lru_cache(maxsize=1)
def load_book():
    return json.loads((ROOT / "data/summer_palace_knowledge.json").read_text(encoding="utf-8"))


def dossier_for(spot: dict | None):
    if not spot:
        return None
    # Namesakes in another city must never inherit this park's historical facts.
    if spot.get("city") not in (None, "", "北京", "北京市"):
        return None
    if spot.get("latitude") and not 39.97 < float(spot["latitude"]) < 40.02:
        return None
    if spot.get("longitude") and not 116.24 < float(spot["longitude"]) < 116.30:
        return None
    return load_book()["spots"].get(spot.get("spot_name"))


def sources_for(dossier, source_ids=None):
    if not dossier:
        return []
    if source_ids is None:
        return list(dossier["sources"])
    registry = load_book()["sources"]
    return [dict(id=key, title=registry[key][0], url=registry[key][1]) for key in dict.fromkeys(source_ids) if key in registry]


def clean_sentences(text: str, count=3, limit=240):
    import re
    parts = [x.strip() for x in re.findall(r"[^。！？\n]+[。！？]?", text) if x.strip()]
    answer = ""
    for part in parts[:count]:
        if len(answer)+len(part) > limit:
            if answer: break
            cut=part[:limit-1]
            boundary=max(cut.rfind("，"),cut.rfind("；"),cut.rfind("："))
            return (cut[:boundary] if boundary>limit//2 else cut)+"。"
        answer += part
    return answer
