"""Build/check offline English copy, including every public attraction detail field.

Examples:
  python scripts/build_ui_english.py --content-only --check
  python scripts/build_ui_english.py --content-only --base-url http://127.0.0.1:8001

Only public application copy is translated. Credentials and visitor records are
never included in translation requests. Runtime language switching is offline.
"""
import argparse
import hashlib
import json
import os
import re
import zipfile
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEST = ROOT / 'frontend/src/i18n/en.json'
CJK = re.compile(r'[\u3400-\u9fff]')
PUBLIC_FIELDS = {
    'scenic_spot_info': ('spot_name', 'description', 'history_detail', 'photo_tips',
                        'service_facilities', 'tour_tips', 'city', 'location', 'best_season', 'tags'),
    'tour_route': ('name', 'description', 'theme'),
}
POLICY = '''Translate Chinese public interface copy and complete attraction descriptions
for a scenic AI guide into natural English. Return a JSON object mapping the supplied
numeric IDs to translations, including every ID exactly once. Translate ALL sentences,
paragraphs, warnings and qualifications; do not summarize or add facts. Keep paragraph
breaks. Preserve all {p0}/{p1}/other placeholders and numeric facts exactly; month
numbers may become English month names, and Chinese counts may become English words
or digits. Do not round numbers. Preserve units, URLs,
HTML and technical identifiers. Render Chinese names and quotations in English or
romanization, with no Chinese characters left in the translated text.
Use: 智游知境=Zhiyou Zhijing, 颐和园=Summer Palace,
仁寿殿=Hall of Benevolence and Longevity, 长廊=Long Corridor,
佛香阁=Tower of Buddhist Incense, 昆明湖=Kunming Lake,
十七孔桥=Seventeen-Arch Bridge, 苏州街=Suzhou Street, 石舫=Marble Boat,
铜牛=Bronze Ox, 排云殿=Hall of Dispelling Clouds, 德和园=Garden of Virtue and Harmony,
乐寿堂=Hall of Joy and Longevity, 谐趣园=Garden of Harmonious Interests,
玉澜堂=Hall of Jade Ripples, 文昌阁=Wenchang Pavilion, 文昌院=Wenchang Gallery,
玉带桥=Jade Belt Bridge, 南湖岛=South Lake Island, 万寿山=Longevity Hill,
文轩=Wenxuan. Return translations only, with no reasoning.'''


def collect_public_copy(tables):
    entries = set()
    for name, fields in PUBLIC_FIELDS.items():
        for item in tables.get(name, []):
            if item.get('delete'):
                continue
            for field in fields:
                value = item.get(field)
                if isinstance(value, str) and CJK.search(value):
                    values = re.split('[;；]', value) if field == 'tags' else [value]
                    entries.update(piece.strip() for piece in values if CJK.search(piece))
    return entries


def read_pack(path):
    if path.is_dir():
        return json.loads((path / 'resources.json').read_text(encoding='utf-8'))['tables']
    with zipfile.ZipFile(path) as archive:
        manifests = [name for name in archive.namelist() if name.endswith('/resources.json') or name == 'resources.json']
        if len(manifests) != 1:
            raise ValueError('Resource pack must contain exactly one resources.json')
        return json.loads(archive.read(manifests[0]))['tables']


def numeric_facts_match(source, target):
    months = ('January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December')
    for number, month in enumerate(months, 1):
        target = re.sub(r'\b' + month + r'\b', str(number), target)
    required = Counter(re.findall(r'\d+(?:\.\d+)?', source))
    actual = Counter(re.findall(r'\d+(?:\.\d+)?', target))
    if required - actual:
        return False
    # An English ordinal such as "16th year" can faithfully represent 十六年.
    digits = {'零': 0, '〇': 0, '一': 1, '二': 2, '两': 2, '三': 3, '四': 4, '五': 5, '六': 6, '七': 7, '八': 8, '九': 9}
    units = {'十': 10, '百': 100, '千': 1000}
    allowed = Counter()
    for phrase in re.findall(r'[零〇一二两三四五六七八九十百千]+', source):
        if not any(char in units for char in phrase):
            value = int(''.join(str(digits[char]) for char in phrase))
        else:
            value, current = 0, 0
            for char in phrase:
                if char in digits:
                    current = digits[char]
                else:
                    value += (current or 1) * units[char]
                    current = 0
            value += current
        allowed[str(value)] += 1
    return not ((actual - required) - allowed)


def valid_translation(source, target):
    return (isinstance(target, str) and bool(target.strip()) and not CJK.search(target)
            and sorted(re.findall(r'\{\w+\}', source)) == sorted(re.findall(r'\{\w+\}', target))
            and numeric_facts_match(source, target))


def missing_translations(entries, existing):
    return sorted(value for value in entries if not existing.get(value) or CJK.search(existing[value]))


def batches(values, limit=4500):
    chunk, size = [], 0
    for value in values:
        if chunk and (size + len(value) > limit or len(chunk) >= 24):
            yield chunk
            chunk, size = [], 0
        chunk.append(value)
        size += len(value)
    if chunk:
        yield chunk


def translate_batch(client, model, values):
    pending = {str(i): value for i, value in enumerate(values)}
    converted = {}
    feedback = ''
    batch_key = hashlib.sha256(json.dumps(values, ensure_ascii=False).encode()).hexdigest()[:12]
    cache_dir = ROOT / 'work_dirs'
    cache_dir.mkdir(parents=True, exist_ok=True)
    for _attempt in range(3):
        answer = client.chat.completions.create(model=model, messages=[
            {'role': 'system', 'content': POLICY + feedback},
            {'role': 'user', 'content': json.dumps(pending, ensure_ascii=False)}],
            response_format={'type': 'json_object'}, temperature=0.1, max_tokens=8192)
        result = json.loads(answer.choices[0].message.content)
        retry = {}
        errors = []
        for index, value in pending.items():
            target = result.get(index)
            if valid_translation(value, target):
                converted[value] = target
            else:
                retry[index] = value
                numerals = re.findall(r"\d+(?:\.\d+)?", value)
                placeholders = re.findall(r"\{\w+\}", value)
                errors.append(f'ID {index}: required Arabic numeral tokens {numerals} '
                              f'and placeholders {placeholders}. '
                              'Spell Chinese-written counts as English words, not additional digits. Remove all Chinese characters.')
        if not retry:
            return converted
        (cache_dir / f'english-public-copy-batch-{batch_key}.json').write_text(
            json.dumps(converted, ensure_ascii=False, indent=2), encoding='utf-8')
        (cache_dir / f'english-public-copy-rejected-{batch_key}.json').write_text(
            json.dumps({index: {'source': value, 'target': result.get(index)} for index, value in retry.items()},
                       ensure_ascii=False, indent=2), encoding='utf-8')
        pending = retry
        feedback = '\nPrevious attempt failed validation. Correct ONLY these IDs:\n' + '\n'.join(errors)
    raise RuntimeError('Incomplete translation or changed numbers/placeholders; catalog not updated')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--pack', type=Path, default=ROOT / 'resources/summer-palace-content.zip')
    parser.add_argument('--base-url', help='Also collect current public backend content, including recent database edits')
    parser.add_argument('--content-only', action='store_true')
    parser.add_argument('--check', action='store_true', help='Check coverage without API calls or file changes')
    args = parser.parse_args()
    entries = collect_public_copy(read_pack(args.pack))
    if not args.content_only:
        source_catalog = ROOT / 'work_dirs/ui-source-catalog.json'
        if source_catalog.exists():
            entries.update(json.loads(source_catalog.read_text(encoding='utf-8')))
    if args.base_url:
        import requests
        session = requests.Session()
        session.trust_env = False
        tables = {}
        for name, endpoint, key in [('scenic_spot_info', 'spots', 'spot_list'), ('tour_route', 'routes', 'route_list')]:
            response = session.get(args.base_url.rstrip('/') + '/tour-session/' + endpoint, timeout=20)
            response.raise_for_status()
            tables[name] = response.json()['data'][key]
        entries.update(collect_public_copy(tables))
    existing = json.loads(DEST.read_text(encoding='utf-8'))
    overrides = json.loads((ROOT / 'frontend/src/i18n/overrides.en.json').read_text(encoding='utf-8'))
    existing.update(overrides)
    todo = missing_translations(entries, existing)
    print(f'Public copy: {len(entries)} unique entries; missing English: {len(todo)}', flush=True)
    if args.check:
        if todo:
            print('Missing entry lengths:', ', '.join(str(len(value)) for value in todo), flush=True)
            raise SystemExit(1)
        return
    if todo:
        from dotenv import load_dotenv
        from openai import OpenAI
        load_dotenv(ROOT / '.env', override=True)
        client = OpenAI(api_key=os.environ['LLM_API_KEY'], base_url=os.environ['LLM_API_BASE'], timeout=90, max_retries=1)
        checkpoint = ROOT / 'work_dirs/english-public-copy.checkpoint.json'
        checkpoint.parent.mkdir(parents=True, exist_ok=True)
        cached = json.loads(checkpoint.read_text(encoding='utf-8')) if checkpoint.exists() else {}
        for saved_batch in checkpoint.parent.glob('english-public-copy-batch-*.json'):
            cached.update(json.loads(saved_batch.read_text(encoding='utf-8')))
        translated = {value: cached[value] for value in todo if valid_translation(value, cached.get(value))}
        chunks = list(batches([value for value in todo if value not in translated]))
        with ThreadPoolExecutor(max_workers=2) as pool:
            futures = [pool.submit(translate_batch, client, os.getenv('LLM_MODEL_NAME', 'deepseek-chat'), chunk) for chunk in chunks]
            for index, future in enumerate(as_completed(futures), 1):
                translated.update(future.result())
                checkpoint.write_text(json.dumps(translated, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
                print(f'Translated {index}/{len(chunks)} batches', flush=True)
        existing.update(translated)
    existing.update(overrides)
    if missing_translations(entries, existing):
        raise RuntimeError('Coverage check failed; catalog not updated')
    DEST.write_text(json.dumps(dict(sorted(existing.items())), ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print('English catalog ready:', len(existing), flush=True)


if __name__ == '__main__':
    main()
