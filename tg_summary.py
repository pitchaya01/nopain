import sys
import os
import asyncio
import requests
import anthropic
from datetime import datetime, timezone, timedelta
from dotenv import load_dotenv
from telethon import TelegramClient

sys.stdout.reconfigure(encoding="utf-8")
sys.stderr.reconfigure(encoding="utf-8")

load_dotenv()

anthropic_client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

# ─────────────────────────────────────────
# CONFIG
# ─────────────────────────────────────────

API_ID   = int(os.environ["TELEGRAM_API_ID"])
API_HASH = os.environ["TELEGRAM_API_HASH"]
PHONE    = os.environ["TELEGRAM_PHONE"]

NOTIFY_TOKEN   = os.environ["NOTIFY_TOKEN"]
NOTIFY_CHAT_ID = os.environ["NOTIFY_CHAT_ID"]

# Channels/Groups ที่ต้องการสรุป
CHANNELS = [
    "@unitynodesannouncements",
    "@WorldMobileTeam",
    "-1003692765127", #unitynode
    "@WorldMobileAnnouncements",
    "@mntannouncements"
]

# Users ที่ต้องการติดตาม (จะแจ้งเตือนทุกข้อความที่พวกเขาโพสต์)
TRACKED_USERS = [
    "Mr_Telecoms",
    "@unityassistant ",
    "andrew_s_wm",
    "@Jk4milli"
]

LOOKBACK_HOURS = 24
SESSION_NAME   = "monitor_session"

ICT = timezone(timedelta(hours=7))

# ─────────────────────────────────────────


def send_telegram_text(message: str) -> None:
    url = f"https://api.telegram.org/bot{NOTIFY_TOKEN}/sendMessage"
    for i in range(0, len(message), 4096):
        chunk = message[i:i + 4096]
        r = requests.post(url, data={"chat_id": NOTIFY_CHAT_ID, "text": chunk}, timeout=10)
        r.raise_for_status()


def summarize_with_claude(channel_title: str, messages: list[tuple]) -> str:
    lines = "\n".join(
        f"[{ts.astimezone(ICT).strftime('%Y-%m-%d %H:%M')}] {sender}: {text}"
        for ts, sender, text in messages
    )
    prompt = (
        f"ต่อไปนี้คือข้อความทั้งหมดจาก Telegram group/channel ชื่อ '{channel_title}' "
        f"ในช่วง {LOOKBACK_HOURS} ชั่วโมงที่ผ่านมา\n\n"
        f"{lines}\n\n"
        "กรุณาสรุปเป็นภาษาไทยว่า:\n"
        "1. หัวข้อหลักที่พูดถึงในช่วงเวลานี้มีอะไรบ้าง\n"
        "2. ประเด็นสำคัญหรือน่าสนใจมีอะไร\n"
        "3. ภาพรวมบรรยากาศใน group เป็นอย่างไร (เชิงบวก/เชิงลบ/เป็นกลาง)\n"
        "สรุปให้กระชับและครอบคลุม"
    )
    with anthropic_client.messages.stream(
        model="claude-sonnet-4-6",
        max_tokens=64000,
        messages=[{"role": "user", "content": prompt}],
    ) as stream:
        response = stream.get_final_message()
    return response.content[0].text.strip()


def get_sender_name(sender) -> str:
    if sender is None:
        return ""
    if hasattr(sender, "username") and sender.username:
        return sender.username
    if hasattr(sender, "first_name"):
        return sender.first_name or ""
    return ""


async def process_channel(client, channel_input: str, since: datetime):
    channel_arg = int(channel_input) if channel_input.lstrip("-").isdigit() else channel_input

    entity = await client.get_entity(channel_arg)
    print(f"[*] Channel/Group: {entity.title}")
    print(f"[*] ดึงข้อความย้อนหลัง {LOOKBACK_HOURS} ชั่วโมง...")

    tracked = {u.lower().lstrip("@") for u in TRACKED_USERS}
    all_messages = []
    tracked_messages = []

    async for msg in client.iter_messages(entity, reverse=False):
        if msg.date < since:
            break
        if not msg.text:
            continue
        sender = await msg.get_sender()
        sender_name = get_sender_name(sender)
        all_messages.append((msg.date, sender_name, msg.text))

        if sender_name.lower() in tracked:
            tracked_messages.append((msg.date, sender_name, msg.text))

    print(f"[*] พบข้อความทั้งหมด {len(all_messages)} ข้อความ")
    print(f"[*] พบข้อความจาก tracked users {len(tracked_messages)} ข้อความ")

    # ── แจ้งเตือนข้อความจาก tracked users ──
    if tracked_messages:
        lines = "\n\n".join(
            f"[{ts.astimezone(ICT).strftime('%Y-%m-%d %H:%M')}] @{sender}:\n{text}"
            for ts, sender, text in reversed(tracked_messages)
        )
        alert = (
            f"🔔 Tracked Users — {entity.title}\n"
            f"ช่วงเวลา: {LOOKBACK_HOURS} ชั่วโมงที่ผ่านมา ({len(tracked_messages)} ข้อความ)\n"
            f"──────────────────\n"
            f"{lines}"
        )
        send_telegram_text(alert)
        print("[+] ส่งแจ้งเตือน tracked users เรียบร้อย")
    else:
        send_telegram_text(
            f"📭 ไม่พบข้อความจาก tracked users ใน {entity.title}\n"
            f"ติดตาม: {', '.join('@' + u for u in TRACKED_USERS)}"
        )

    # ── สรุปภาพรวม channel ด้วย Claude ──
    if not all_messages:
        send_telegram_text(
            f"📭 ไม่พบข้อความใน {entity.title}\n"
            f"ช่วงเวลา: {LOOKBACK_HOURS} ชั่วโมงที่ผ่านมา"
        )
        return

    print("[*] กำลังให้ Claude สรุป...")
    ai_summary = summarize_with_claude(entity.title, all_messages)
    since_ict = since.astimezone(ICT).strftime("%Y-%m-%d %H:%M")
    now_ict   = datetime.now(ICT).strftime("%Y-%m-%d %H:%M")
    summary = (
        f"📋 สรุป {entity.title}\n"
        f"ช่วงเวลา: {since_ict} – {now_ict} (ICT)\n"
        f"จำนวนข้อความ: {len(all_messages)} ข้อความ\n"
        f"──────────────────\n"
        f"{ai_summary}"
    )
    print(summary)
    send_telegram_text(summary)
    print("[+] ส่งสรุปเรียบร้อย")


async def main():
    client = TelegramClient(SESSION_NAME, API_ID, API_HASH)
    await client.start(phone=PHONE)
    me = await client.get_me()
    print(f"[*] Logged in as @{me.username}")

    since = datetime.now(timezone.utc) - timedelta(hours=LOOKBACK_HOURS)

    for channel in CHANNELS:
        print(f"\n{'='*40}")
        print(f"[*] กำลังประมวลผล: {channel}")
        await process_channel(client, channel, since)

    await client.disconnect()


if __name__ == "__main__":
    asyncio.run(main())
