import asyncio
import requests
from datetime import datetime, timezone, timedelta
from telethon import TelegramClient


def send_telegram_text(message: str, token: str, chat_id: str) -> dict:
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    r = requests.post(url, data={"chat_id": chat_id, "text": message}, timeout=10)
    r.raise_for_status()
    return r.json()

# ─────────────────────────────────────────
# CONFIG — กรอกข้อมูลก่อนรัน
# ─────────────────────────────────────────

API_ID   = 24778942
API_HASH = "8fb64cfbdca670713487c0795dcae9d5"
PHONE    = "+66808151412"

CHANNEL_USERNAME = "@WorldMobileTeam"
TARGET_USERNAME  = "Mr_Telecoms"

NOTIFY_TOKEN   = "7718053957:AAHSHEXigIC3lc9xkUgXtVlPWIg74eikYd0"
NOTIFY_CHAT_ID = "6193006196"

LOOKBACK_HOURS = 24   # ดึงย้อนหลังกี่ชั่วโมง

SESSION_NAME = "monitor_session"

# ─────────────────────────────────────────

_channel_arg = int(CHANNEL_USERNAME) if CHANNEL_USERNAME.lstrip("-").isdigit() else CHANNEL_USERNAME

client = TelegramClient(SESSION_NAME, API_ID, API_HASH)


async def main():
    await client.start(phone=PHONE)
    me = await client.get_me()
    print(f"[*] Logged in as @{me.username}")

    entity = await client.get_entity(_channel_arg)
    print(f"[*] Channel: {entity.title}")

    since = datetime.now(timezone.utc) - timedelta(hours=LOOKBACK_HOURS)
    target = TARGET_USERNAME.lower().lstrip("@")

    print(f"[*] ดึงข้อความย้อนหลัง {LOOKBACK_HOURS} ชั่วโมง...")

    found = []
    async for msg in client.iter_messages(entity, offset_date=None, reverse=False):
        if msg.date < since:
            break
        if not msg.text:
            continue
        sender = await msg.get_sender()
        if sender is None:
            continue
        if (sender.username or "").lower() != target:
            continue
        found.append((msg.date, msg.text))

    await client.disconnect()

    if not found:
        summary = (
            f"[Daily Report] @{TARGET_USERNAME}\n"
            f"Channel: {entity.title}\n"
            f"ช่วงเวลา: {LOOKBACK_HOURS} ชั่วโมงที่ผ่านมา\n"
            f"──────────────────\n"
            f"ไม่พบข้อความจาก @{TARGET_USERNAME}"
        )
        print(summary)
    else:
        lines = "\n\n".join(
            f"[{ts.astimezone().strftime('%H:%M')}] {text}" for ts, text in reversed(found)
        )
        summary = (
            f"[Daily Report] @{TARGET_USERNAME}\n"
            f"Channel: {entity.title}\n"
            f"ช่วงเวลา: {LOOKBACK_HOURS} ชั่วโมงที่ผ่านมา ({len(found)} ข้อความ)\n"
            f"──────────────────\n"
            f"{lines}"
        )
        print(summary)

    send_telegram_text(summary, NOTIFY_TOKEN, NOTIFY_CHAT_ID)
    print("[+] ส่ง notification เรียบร้อย")


if __name__ == "__main__":
    asyncio.run(main())
