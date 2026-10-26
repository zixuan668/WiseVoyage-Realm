import importlib.util
import json
import unittest
from pathlib import Path

spec = importlib.util.spec_from_file_location('english_catalog', Path(__file__).parents[1] / 'build_ui_english.py')
catalog = importlib.util.module_from_spec(spec)
spec.loader.exec_module(catalog)


class EnglishCatalogTests(unittest.TestCase):
    def test_collects_whole_detail_paragraphs_and_individual_tags(self):
        fields = {field: field + '中文第一段。\n第二段。' for field in (
            'description', 'history_detail', 'photo_tips', 'tour_tips', 'service_facilities', 'location', 'best_season')}
        entries = catalog.collect_public_copy({'scenic_spot_info': [{**fields, 'tags': '建筑;文化；园林',
            'api_key': '不能发送的密钥', 'private_notes': '不能发送的记录'}]})
        for value in fields.values():
            self.assertIn(value, entries)
        self.assertTrue({'建筑', '文化', '园林'}.issubset(entries))
        self.assertNotIn('不能发送的密钥', entries)
        self.assertNotIn('不能发送的记录', entries)
        self.assertNotIn('建筑;文化；园林', entries)

    def test_deleted_content_is_not_collected(self):
        self.assertEqual(catalog.collect_public_copy({'scenic_spot_info': [
            {'spot_name': '删除的景点', 'delete': True}]}), set())

    def test_rejects_missing_placeholders_changed_measurements_and_partial_chinese(self):
        source = '全长728米，{p0}处，共273间。'
        self.assertTrue(catalog.valid_translation(source, '728 meters long, {p0} locations, 273 bays.'))
        self.assertFalse(catalog.valid_translation(source, '728 meters long, 273 bays.'))
        self.assertFalse(catalog.valid_translation(source, '780 meters long, {p0} locations, 273 bays.'))
        self.assertFalse(catalog.valid_translation(source, '728米，{p0} locations, 273 bays.'))
        self.assertFalse(catalog.valid_translation(source, ''))
        self.assertTrue(catalog.valid_translation('11月下旬', 'Late November'))
        self.assertTrue(catalog.valid_translation('嘉庆十六年即1811年', 'The 16th year of Jiaqing, 1811'))
        self.assertFalse(catalog.valid_translation('嘉庆十六年即1811年', 'The 18th year of Jiaqing, 1811'))

    def test_batches_do_not_split_sentences_or_exceed_limits(self):
        values = ['第一段。\n第二段。'] * 30
        chunks = list(catalog.batches(values, limit=40))
        self.assertEqual([value for chunk in chunks for value in chunk], values)
        self.assertTrue(all(sum(map(len, chunk)) <= 40 and len(chunk) <= 24 for chunk in chunks))

    def test_all_bundled_scenic_and_route_content_has_complete_english(self):
        tables = catalog.read_pack(catalog.ROOT / 'resources/summer-palace-content.zip')
        entries = catalog.collect_public_copy(tables)
        existing = json.loads(catalog.DEST.read_text(encoding='utf-8'))
        self.assertEqual(catalog.missing_translations(entries, existing), [])
        for spot in tables['scenic_spot_info']:
            for field in ('history_detail', 'photo_tips', 'tour_tips', 'service_facilities'):
                with self.subTest(spot=spot['spot_name'], field=field):
                    self.assertTrue(catalog.valid_translation(spot[field], existing.get(spot[field])))


if __name__ == '__main__':
    unittest.main()
