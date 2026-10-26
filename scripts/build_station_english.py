"""Export existing reviewed public translations for backend offline consultation."""
import json
from pathlib import Path

root = Path(__file__).resolve().parents[1]
translations = json.loads((root/'frontend/src/i18n/en.json').read_text(encoding='utf-8'))
public = {key: value for key, value in translations.items() if len(key) > 100}
(root/'data/station_public_english.json').write_text(json.dumps(public, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
print(f'Exported {len(public)} existing public content translations.')
