"""Registration mail transport and validation; secrets stay on the backend."""
import hashlib
import hmac
import os
import re
import smtplib
import ssl
from email.message import EmailMessage
from email.utils import formataddr
from html import escape

from fastapi import HTTPException
from ...web_configs import WEB_CONFIGS


def normalize_email(value: str) -> str:
    email = value.strip().lower()
    if len(email) > 254 or not re.fullmatch(r"[A-Za-z0-9.!#$%&'*+/=?^_`{|}~-]+@[A-Za-z0-9](?:[A-Za-z0-9.-]*[A-Za-z0-9])?\.[A-Za-z]{2,63}", email):
        raise HTTPException(400, "请输入有效的邮箱地址")
    return email


def code_digest(email: str, code: str) -> str:
    key = WEB_CONFIGS.TOKEN_JWT_SECURITY_KEY
    if not key:
        raise HTTPException(503, "登录服务未配置 JWT 密钥")
    return hmac.new(key.encode(), (email + ':' + code).encode(), hashlib.sha256).hexdigest()


def send_registration_code(email: str, code: str):
    username = os.getenv('SMTP_USERNAME', '')
    password = os.getenv('SMTP_PASSWORD', '')
    if not username or not password:
        raise HTTPException(503, "验证码邮件服务未配置，请联系管理员")
    message = EmailMessage()
    message['From'] = formataddr(('智游知境', username))
    message['To'] = email
    message['Subject'] = '【智游知境】验证邮箱，开启你的旅程'
    message.set_content(
        '智游知境 · AI 数字人景区导览\n\n'
        '你好，欢迎来到智游知境！\n'
        '你正在注册智游知境账号，请在注册页面输入以下验证码，完成邮箱验证。\n\n'
        f'注册验证码：{code}\n\n'
        '验证码将在发送后 10 分钟失效，仅用于本次注册。\n'
        '请勿将验证码转发或告知他人。\n'
        '如果这不是你的操作，请忽略此邮件，无需回复。\n\n'
        '山水之间，智游相伴。\n智游知境\n此邮件由系统自动发送，请勿直接回复。'
    )
    safe_code = escape(code)
    message.add_alternative(f'''<!doctype html>
<html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"></head>
<body style="margin:0;padding:0;background:#f5f3ff;color:#30285e;font-family:Arial,'Microsoft YaHei',sans-serif;">
<div style="display:none;max-height:0;overflow:hidden;opacity:0;">完成邮箱验证，开启你的智游旅程。验证码有效期为10分钟。</div>
<table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="background:#f5f3ff;"><tr><td align="center" style="padding:32px 16px;">
<table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="max-width:520px;background:#ffffff;border:1px solid #e8e2f5;border-radius:20px;">
<tr><td style="padding:32px 28px 24px;border-bottom:1px solid #eeeaf6;">
<div style="font-size:24px;font-weight:bold;color:#6d48c8;">智游知境</div>
<div style="margin-top:8px;font-size:13px;line-height:1.6;color:#817994;">AI 数字人景区导览 · 山水之间，智游相伴</div>
</td></tr>
<tr><td style="padding:28px;">
<h1 style="margin:0 0 16px;font-size:22px;line-height:1.5;color:#30285e;">验证邮箱，开启你的旅程</h1>
<p style="margin:0 0 12px;font-size:15px;line-height:1.8;color:#625a75;">你好，欢迎来到智游知境！</p>
<p style="margin:0 0 24px;font-size:15px;line-height:1.8;color:#625a75;">你正在注册智游知境账号。请在注册页面输入下方验证码，完成邮箱验证。</p>
<table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="background:#f4f0ff;border:1px solid #e5dcfa;border-radius:14px;"><tr><td align="center" style="padding:22px 12px;">
<div style="font-size:13px;color:#74668d;">注册验证码</div>
<div style="margin:12px 0;font-family:Consolas,monospace;font-size:36px;line-height:1.4;letter-spacing:6px;font-weight:bold;color:#6840c2;">{safe_code}</div>
<div style="font-size:13px;line-height:1.8;color:#74668d;">发送后 <strong>10 分钟</strong>内有效 · 仅用于本次注册</div>
</td></tr></table>
<p style="margin:24px 0 0;font-size:13px;line-height:1.9;color:#817994;">请勿将验证码转发或告知他人。<br>如果这不是你的操作，请忽略此邮件，无需回复。</p>
</td></tr>
<tr><td style="padding:20px 28px;border-top:1px solid #eeeaf6;font-size:12px;line-height:1.8;color:#938aA5;">智游知境<br>此邮件由系统自动发送，请勿直接回复。</td></tr>
</table></td></tr></table></body></html>''', subtype='html')
    try:
        with smtplib.SMTP_SSL(os.getenv('SMTP_HOST', 'smtp.qq.com'),
                              int(os.getenv('SMTP_PORT', '465')),
                              timeout=15, context=ssl.create_default_context()) as smtp:
            smtp.login(username, password)
            smtp.send_message(message)
    except (OSError, smtplib.SMTPException, ValueError):
        raise HTTPException(502, "验证码发送失败，请稍后重试或联系管理员") from None
