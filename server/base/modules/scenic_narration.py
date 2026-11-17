"""Build complete narration only from maintained scenic data."""
import hashlib
import json


def narration_text(spot) -> str:
    sections = [('description', '景点介绍'), ('history_detail', '历史与文化'),
                ('tour_tips', '值得留意'), ('photo_tips', '拍照建议'),
                ('best_season', '季节建议'), ('service_facilities', '服务设施')]
    paragraphs = [f'{label}。{value}' for field, label in sections
                  if (value := str(getattr(spot, field, '') or '').strip())]
    return f'{spot.spot_name}。\n' + '\n'.join(paragraphs) if paragraphs else ''


def narration_revision(text: str, voice_identity: str) -> str:
    return hashlib.sha256(json.dumps(['xingyun-recording-v1', text, voice_identity],
                                    ensure_ascii=False).encode()).hexdigest()


def voice_identity(binding) -> str:
    # No credentials or access-bearing URLs are included in public output.
    return json.dumps([binding.guide_id, binding.app_id, binding.voice_label], ensure_ascii=False)


def recording_file(root, record):
    from pathlib import Path
    directory = Path(root).resolve()
    path = (directory / record.file_name).resolve()
    return path if path.parent == directory and path.is_file() and path.stat().st_size > 100 else None
