import json
from pathlib import Path
from tempfile import TemporaryDirectory
from shutil import copyfile
import pytest
from scripts.check_delivery import check_content_scope, ROOT

def test_delivered_content_contains_only_summer_palace_records():
    assert check_content_scope()['scenic_spots'] == 16

def test_scope_check_rejects_unrelated_record():
    with TemporaryDirectory() as folder:
        root=Path(folder)
        (root/'data').mkdir()
        copyfile(ROOT/'data/summer_palace_locations.json',root/'data/summer_palace_locations.json')
        (root/'data/scenic_content_audit.json').write_text(json.dumps({'spots':[{'name':'外部测试景点'}]},ensure_ascii=False),encoding='utf8')
        with pytest.raises(AssertionError,match='Unrelated scenic'):
            check_content_scope(root)
