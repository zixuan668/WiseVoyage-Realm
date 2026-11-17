import ast, unittest
from pathlib import Path
from types import SimpleNamespace

class NativeScenicOwnerTests(unittest.TestCase):
    def owner(self, headers=None, cookies=None):
        source=Path('server/base/routers/tour_experience.py').read_text(encoding='utf-8')
        node=next(n for n in ast.parse(source).body if isinstance(n,ast.FunctionDef) and n.name=='scenic_draft_owner')
        calls=[]
        def verify(token):
            calls.append(token)
            if token=='invalid': raise ValueError('invalid token')
            return 17
        scope={'Request':object,'get_current_user_info':verify}
        exec(compile(ast.Module(body=[node],type_ignores=[]),'owner-test','exec'),scope)
        return scope['scenic_draft_owner'](SimpleNamespace(headers=headers or {},cookies=cookies or {}))
    def test_native_owner_uses_verified_account(self):
        self.assertEqual(self.owner({'authorization':'Bearer valid'},{'scenic_draft':'browser'}),'app:17')
    def test_anonymous_browser_owner_is_unchanged(self):
        self.assertEqual(self.owner(cookies={'scenic_draft':'browser'}),'browser')
    def test_invalid_token_never_falls_back_to_browser(self):
        with self.assertRaises(ValueError): self.owner({'authorization':'Bearer invalid'},{'scenic_draft':'browser'})
if __name__=='__main__':unittest.main()
