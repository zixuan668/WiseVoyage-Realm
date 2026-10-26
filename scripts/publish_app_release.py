"""Publish an actual signed APK to the local pickup page; never create placeholder files."""
import argparse
import hashlib
import json
import shutil
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('apk', type=Path)
    args = parser.parse_args()
    source = args.apk.resolve()
    with zipfile.ZipFile(source) as archive:
        if 'AndroidManifest.xml' not in archive.namelist() or not archive.read('AndroidManifest.xml'):
            raise ValueError('Not an Android APK')
        if archive.testzip():
            raise ValueError('APK checksum failure')
    manifest = json.loads((ROOT / 'app/manifest.json').read_text(encoding='utf-8-sig'))
    target = ROOT / 'static/app'
    target.mkdir(parents=True, exist_ok=True)
    destination = target / 'zhiyou-guide.apk'
    if source != destination.resolve():
        shutil.copy2(source, destination)
    release = dict(version=manifest['versionName'], package='cn.zhiyou.guide',
                   sha256=hashlib.sha256(destination.read_bytes()).hexdigest(), bytes=destination.stat().st_size)
    (target / 'release.json').write_text(json.dumps(release, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(release))


if __name__ == '__main__':
    main()
