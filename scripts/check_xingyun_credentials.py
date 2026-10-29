"""检查本机星云应用凭据是否可用（会话分配是否成功）。

用法：python scripts/check_xingyun_credentials.py [guide_id]
- 读取根目录 .env，解密数据库里该导游的星云绑定，直接请求星云网关。
- 成功分配资源包后会立即 DELETE 释放会话，避免占用/浪费。
- 退出码：0 可用；2 账号积分不足（错误码 5）；3 其他云端错误；1 本地异常。
"""
from __future__ import annotations

import os
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)


def load_env() -> None:
    for raw in open(os.path.join(ROOT, ".env"), encoding="utf-8"):
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ[key.strip()] = value.strip().strip('"').strip("'")


def main() -> int:
    load_env()
    import httpx
    from sqlmodel import Session

    from server.base.database.init_db import DB_ENGINE
    from server.base.models.xingyun import XingyunGuideBinding
    from server.base.modules.xingyun_access import decrypt_secret
    from server.base.routers.xingyun import GATEWAY, signed_headers

    guide_id = int(sys.argv[1]) if len(sys.argv) > 1 else 1
    with Session(DB_ENGINE) as db:
        binding = db.get(XingyunGuideBinding, guide_id)
        if not binding:
            print(f"导游 {guide_id} 没有星云绑定")
            return 1
        app_id = binding.app_id
        secret = decrypt_secret(binding.secret_encrypted)
    print(f"导游 {guide_id}，App ID {app_id[:6]}…{app_id[-4:]}")

    body = {
        "request_id": f"credential-check-{int(time.time())}",
        "config": {"framedata_proto_version": 2, "walk_version": 3},
    }
    try:
        with httpx.Client(timeout=30, trust_env=False) as client:
            create = client.post(GATEWAY, json=body,
                                 headers=signed_headers("POST", body, app_id=app_id, app_secret=secret))
            payload = create.json()
    except Exception as error:  # noqa: BLE001 - 网络异常需要给出可读结论
        print(f"请求星云失败：{type(error).__name__}: {error}")
        return 1

    code = payload.get("error_code")
    reason = payload.get("error_reason") or ""
    data = payload.get("data") or {}
    if create.is_success and data.get("resource_pack"):
        session_id = str(data.get("session_id") or "")
        print("云端会话已分配：凭据可用，账号有可用积分。")
        stop_body = {"stop_reason": "credential_check", "request_id": body["request_id"]}
        if session_id:
            stop_body["session_id"] = session_id
        try:
            with httpx.Client(timeout=30, trust_env=False) as client:
                client.request("DELETE", GATEWAY, json=stop_body,
                               headers=signed_headers("DELETE", stop_body,
                                                      app_id=app_id, app_secret=secret))
            print("已释放测试会话。")
        except Exception as error:  # noqa: BLE001
            print(f"警告：测试会话释放失败，请稍后在后台确认：{type(error).__name__}: {error}")
        return 0

    print(f"云端拒绝会话：error_code={code}，error_reason={reason}")
    if code == 5:
        print("结论：App ID/Secret 有效，但该应用所属星云账号积分不足，需要在星云平台充值或领取积分后重试。")
        return 2
    print("结论：不是积分不足，请核对应用状态、人物配置或平台公告。")
    return 3


if __name__ == "__main__":
    raise SystemExit(main())
