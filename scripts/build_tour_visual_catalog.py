"""Refresh reviewed official image references, not model-generated illustrations.

Images remain on their original public hosts; no third-party photo is copied
into the repository. Review source pages before changing the mapping below.
"""
import json
import re
from pathlib import Path
from urllib.parse import urljoin
import requests

ROOT = Path(__file__).resolve().parents[1]
OFFICIAL = 'https://www.summerpalace.net.cn'
PAGES = {'长廊': '/gallery_detail/369.html', '昆明湖': '/laka_spot/detail/355.html', '十七孔桥': '/laka_spot/detail/362.html', '南湖岛': '/laka_spot/detail/360.html', '铜牛': '/laka_spot/detail/361.html', '石舫': '/laka_spot/detail/413.html', '仁寿殿': '/court_life/detail/346.html', '德和园': '/court_life/detail/344.html', '玉澜堂': '/court_life/detail/347.html', '乐寿堂': '/court_life/detail/350.html', '排云殿': '/longevity/detailqianshan/381.html', '佛香阁': '/longevity/detailqianshan/382.html', '谐趣园': '/longevity/detailhouhu/372.html', '苏州街': '/longevity/detailhouhu/373.html'}
NAMES = {'长廊': 'Long Corridor', '昆明湖': 'Kunming Lake', '十七孔桥': 'Seventeen-Arch Bridge', '南湖岛': 'South Lake Island', '铜牛': 'Bronze Ox', '石舫': 'Marble Boat', '仁寿殿': 'Hall of Benevolence and Longevity', '德和园': 'Garden of Virtue and Harmony', '玉澜堂': 'Hall of Jade Ripples', '乐寿堂': 'Hall of Joyful Longevity', '排云殿': 'Hall of Dispelling Clouds', '佛香阁': 'Tower of Buddhist Incense', '谐趣园': 'Garden of Harmonious Interests', '苏州街': 'Suzhou Street'}


def build():
    catalog = {}
    for name, path in PAGES.items():
        url = OFFICIAL + path
        response = requests.get(url, timeout=15)
        response.raise_for_status()
        response.encoding = 'utf-8'
        # Article photos are uploaded JPGs. Header QR codes and decorative
        # theme images are excluded. This site also embeds JPGs in SVG images.
        candidates = list(dict.fromkeys(re.findall(
            r'(?:src|xlink:href)=["\'](/Uploads/Picture/[^"\']+\.jpg)["\']', response.text)))
        candidates = [p for p in candidates if '2025/09/05/' not in p]
        catalog[name] = dict(images=[dict(url=urljoin(url, p), source=url,
            zh=name + ' · 官网参考图片', en=NAMES[name] + ' · official reference') for p in candidates[:3]], timeline=[])
    corridor = catalog['长廊']
    for year, zh, en in [(1750, '长廊始建。', 'The Long Corridor was first built.'),
                         (1886, '长廊重建。', 'The Long Corridor was rebuilt.')]:
        corridor['timeline'].append(dict(year=year, zh=zh, en=en, source=OFFICIAL + PAGES['长廊']))
    catalog['十七孔桥']['timeline'] = [dict(year=1750, zh='十七孔桥始建。',
        en='The Seventeen-Arch Bridge was first built.', source=OFFICIAL + PAGES['十七孔桥'])]
    (ROOT / 'data/tour_visual_catalog.json').write_text(json.dumps(catalog, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print('Updated official references:', {name: len(item['images']) for name, item in catalog.items()})


if __name__ == '__main__':
    build()
