"""无需数据库或云端密钥，检查后端签名与官方 JS SDK 算法一致。"""
import ast
import hashlib
import json
import os
import pathlib
import subprocess

root = pathlib.Path(__file__).resolve().parents[1]
module = ast.parse((root / "server/base/routers/xingyun.py").read_text(encoding="utf-8"))
function = next(node for node in module.body if isinstance(node, ast.FunctionDef) and node.name == "signed_headers")
scope = {"os": os, "time": __import__("time"), "json": json, "hashlib": hashlib}
exec(compile(ast.Module(body=[function], type_ignores=[]), "<signed_headers>", "exec"), scope)
old = {key: os.environ.get(key) for key in ("XINGYUN_APP_ID", "XINGYUN_APP_SECRET")}
try:
    os.environ.update(XINGYUN_APP_ID="test-id", XINGYUN_APP_SECRET="test-secret")
    for method, body in [
        ("POST", {"config": {"z": "颐 和园😀", "a": [1, True, None, {"b": "长廊"}]}}),
        ("DELETE", {"stop_reason": "user stop", "session_id": "test-session", "request_id": "test-request"}),
    ]:
        js = """
const crypto = require('node:crypto');
const body = JSON.parse(process.argv[1]);
function sort(x) {
 if (Array.isArray(x)) return x.map(sort);
 if (x && typeof x === 'object') return Object.fromEntries(Object.keys(x).sort().map(k => [k, sort(x[k])]));
 return x;
}
const canonical = JSON.stringify(sort(body)).replace(/[\u0080-\uffff]/g, c => String.fromCharCode(92) + 'u' + c.charCodeAt(0).toString(16).padStart(4, '0')).replace(/ /g, '');
console.log(crypto.createHash('md5').update('/user/v1/ttsa/session' + process.argv[2].toLowerCase() + canonical + 'test-secret' + '1700000000').digest('hex'));
"""
        expected = subprocess.check_output(["node", "-e", js, json.dumps(body), method], text=True).strip()
        headers = scope["signed_headers"](method, body, 1700000000)
        assert headers["X-TOKEN"] == expected, (method, headers["X-TOKEN"], expected)
        assert headers["X-APP-ID"] == "test-id"
        assert headers["X-TIMESTAMP"] == "1700000000"
    print("PASS: POST/DELETE signatures match JavaScript, including nested Chinese/emoji payloads.")
finally:
    for key, value in old.items():
        if value is None:
            os.environ.pop(key, None)
        else:
            os.environ[key] = value