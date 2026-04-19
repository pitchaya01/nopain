import asyncio
import re
import os
import requests
import openai
from collections import defaultdict
from datetime import datetime, timezone, timedelta
from telethon import TelegramClient

# ─────────────────────────────────────────
# CONFIG
# ─────────────────────────────────────────

# Etherscan / MNTx
API_KEY   = "HU6J9N3UF2GNK452D3WT9PCT5S3KJSM5A2"
CONTRACT  = "0x5C697fee285B513711A816018DBb34DC0cFC4875"
CHAIN_ID  = 1
DECIMALS  = 18
MAX_ROWS  = 2000
PAGE_SIZE = 100
HOURS_BACK = 24
UNISWAP_ADDR = "0x61192EB6ca9fe34a3Ccc5f4cd4bf6feFB77a037f".lower()
METHOD_MAP = {
    "0xdcb18521": "Decrease Stake",
    "0xa9059cbb": "Transfer",
    "0x12aa3caf": "Swap",
    "0x35138382": "Increase Stake",
}

# Twitter
TWITTER_HEADERS = {"X-API-Key": "new1_5bdebf52aa95464bad3576b4606ff85e"}
USERNAMES = [
    "siamblockchain", "bitcoinaddictth", "BitcoinMagazine", "IOHK_Charles",
    "TheDePINCat", "wmReclaim", "worldmobileteam", "MrTelecoms", "andrew_s_wm",
    "CloverNodes", "WMTxLady", "hopenothype_io", "wmchain", "SebastienGllmt",
    "MinswapIntern", "ChristianRees",
]

# Telegram Bot
TG_TOKEN  = "7718053957:AAHSHEXigIC3lc9xkUgXtVlPWIg74eikYd0"
TG_CHAT   = "6193006196"

# Telethon (monitor Telegram channel)
TG_API_ID         = 24778942
TG_API_HASH       = "8fb64cfbdca670713487c0795dcae9d5"
TG_PHONE          = "+66808151412"
CHANNEL_USERNAME  = "@WorldMobileTeam"
TARGET_USERNAME   = "watarif"
LOOKBACK_HOURS    = 24
SESSION_NAME      = "monitor_session"

ICT = timezone(timedelta(hours=7))


# ─────────────────────────────────────────
# TELEGRAM BOT
# ─────────────────────────────────────────

def send_telegram(message: str):
    url = f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage"
    try:
        r = requests.post(url, data={"chat_id": TG_CHAT, "text": message}, timeout=10)
        r.raise_for_status()
        if not r.json().get("ok"):
            print(f"[!] Telegram error: {r.json()}")
        else:
            print("[+] ส่ง Telegram สำเร็จ")
    except Exception as e:
        print(f"[!] Telegram ส่งไม่ได้: {e}")


# ─────────────────────────────────────────
# COINGECKO / LTV
# ─────────────────────────────────────────

def get_price_coingecko(ids=("bitcoin", "ethereum"), vs_currencies=("usd",)):
    url = "https://api.coingecko.com/api/v3/simple/price"
    r = requests.get(url, params={"ids": ",".join(ids), "vs_currencies": ",".join(vs_currencies)}, timeout=10)
    r.raise_for_status()
    return r.json()

def check_ltv():
    data = get_price_coingecko(["cardano"], ["usd"])
    ada_price = float(data["cardano"]["usd"])
    ltv_percent = (7097.73435225 / (29121.68587978 * ada_price)) * 100
    if ltv_percent > 60:
        send_telegram(f"⚠️ LTV เกิน 60%: {ltv_percent:.2f}%")


# ─────────────────────────────────────────
# TWITTER
# ─────────────────────────────────────────

if not os.getenv("OPENAI_API_KEY"):
    from dotenv import load_dotenv
    load_dotenv()

openai_client = openai.OpenAI()

def remove_dollar_numbers(text):
    return re.sub(r'\$[\d,]+(?:\.\d+)?', '', text).strip()

def remove_urls(text):
    return re.sub(r'http\S+|www\S+|https\S+', '', text, flags=re.MULTILINE)

def is_token_price_related(text):
    keywords = ["marketcap", "sell", "dip", "price", "ล้าง", "แตก", "hold", "hodl",
                "ath", "buy", "mc", "sold", "ขาย", "ซื้อ", "bear"]
    if any(kw in text.lower() for kw in keywords):
        return True
    prompt = (
        "Please determine if the following text is talking about the price, market value, "
        "or price prediction of a token/cryptocurrency, or marketcap or sentiment such as "
        "price drop or high. Text is from twitter tweet or X.\n\n"
        "If so, respond ONLY with 'RELATED'. If not, respond ONLY with 'NOT_RELATED'.\n\n"
        f"Text: {text}"
    )
    response = openai_client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": prompt}],
        temperature=0,
    )
    return response.choices[0].message.content.strip() == "RELATED"

def run_twitter():
    yesterday_utc = (datetime.now(timezone.utc) - timedelta(days=1)).date()
    for uname in USERNAMES:
        response = requests.get(
            "https://api.twitterapi.io/twitter/user/last_tweets",
            headers=TWITTER_HEADERS,
            params={"userName": uname, "includeReplies": "false"},
        )
        tweets = response.json().get("data", {}).get("tweets", [])
        for tweet in tweets:
            created_at = datetime.strptime(tweet["createdAt"], "%a %b %d %H:%M:%S %z %Y")
            if created_at.date() != yesterday_utc:
                continue
            if is_token_price_related(tweet["text"]):
                continue
            message = (
                "------\n"
                f"User      : {uname}\n"
                f"Text      : {tweet['text']}\n"
                f"CreatedAt : {tweet['createdAt']}\n"
            )
            send_telegram(remove_dollar_numbers(remove_urls(message)))


# ─────────────────────────────────────────
# ETHERSCAN / MNTx
# ─────────────────────────────────────────

def ts_to_str(ts: int) -> str:
    return datetime.fromtimestamp(ts, tz=ICT).strftime("%Y-%m-%d %H:%M:%S ICT")

def fetch_latest() -> list:
    all_txs = []
    page = 1
    cutoff_ts = int((datetime.now(tz=timezone.utc) - timedelta(hours=HOURS_BACK)).timestamp())
    print(f"[*] ดึง tx ย้อนหลัง {HOURS_BACK}h (ตั้งแต่ {ts_to_str(cutoff_ts)})...")
    pages_needed = -(-MAX_ROWS // PAGE_SIZE)
    while page <= pages_needed:
        url = (
            f"https://api.etherscan.io/v2/api?chainid={CHAIN_ID}"
            f"&module=account&action=tokentx&contractaddress={CONTRACT}"
            f"&page={page}&offset={PAGE_SIZE}&sort=desc&apikey={API_KEY}"
        )
        data = requests.get(url, timeout=15).json()
        if data["status"] != "1":
            print(f"  [!] หยุดที่ page {page}: {data['message']}")
            break
        batch = data["result"]
        filtered = [tx for tx in batch if int(tx.get("timeStamp", 0)) >= cutoff_ts]
        all_txs.extend(filtered)
        print(f"  page {page:>2}  total {len(batch)} tx  ใน {HOURS_BACK}h: {len(filtered)} tx  รวม {len(all_txs):,}")
        if int(batch[-1].get("timeStamp", 0)) < cutoff_ts or len(batch) < PAGE_SIZE:
            break
        page += 1
    return all_txs[:MAX_ROWS]

def analyze(txs: list):
    dec = 10 ** DECIMALS
    method_volume, method_count, unknown = defaultdict(float), defaultdict(int), defaultdict(int)
    from_uni_vol = to_uni_vol = 0.0
    from_uni_cnt = to_uni_cnt = 0
    timestamps = []
    for tx in txs:
        volume = int(tx.get("value", 0)) / dec
        from_addr = tx.get("from", "").lower()
        to_addr   = tx.get("to",   "").lower()
        timestamps.append(int(tx.get("timeStamp", 0)))
        name = METHOD_MAP.get(tx.get("methodId", "0x"))
        if name is None:
            unknown[tx.get("methodId", "0x")] += 1
        else:
            method_volume[name] += volume
            method_count[name]  += 1
        if from_addr == UNISWAP_ADDR:
            from_uni_vol += volume; from_uni_cnt += 1
        if to_addr == UNISWAP_ADDR:
            to_uni_vol += volume; to_uni_cnt += 1
    ts_min = min(timestamps) if timestamps else 0
    ts_max = max(timestamps) if timestamps else 0
    return method_volume, method_count, from_uni_vol, from_uni_cnt, to_uni_vol, to_uni_cnt, unknown, ts_min, ts_max

def build_report(txs, method_volume, method_count, from_uni_vol, from_uni_cnt,
                 to_uni_vol, to_uni_cnt, unknown, ts_min, ts_max) -> str:
    total_vol = sum(method_volume.values())
    net = from_uni_vol - to_uni_vol
    lines = [
        f"📊 MNTx — สรุปย้อนหลัง {HOURS_BACK} ชั่วโมง",
        f"🕐 {ts_to_str(ts_min)}",
        f"   ถึง {ts_to_str(ts_max)}",
        f"📋 Total Tx : {len(txs):,} transactions",
        "",
        "── Method Volume ──",
    ]
    for name, vol in sorted(method_volume.items(), key=lambda x: -x[1]):
        pct = vol / total_vol * 100 if total_vol else 0
        lines.append(f"  {name:<16} {method_count[name]:>5} tx  {vol:>14,.2f} MNTx ({pct:.1f}%)")
    lines += [
        "",
        "── Uniswap Flow ──",
        f"  ซื้อ (FROM Uni)  {from_uni_cnt:>5} tx  {from_uni_vol:>14,.2f} MNTx",
        f"  ขาย (TO Uni)    {to_uni_cnt:>5} tx  {to_uni_vol:>14,.2f} MNTx",
        f"  Net Flow        {net:>+21,.2f} MNTx",
        f"  {'NET ซื้อเข้า ↑' if net > 0 else 'NET ขายออก ↓'}",
    ]
    return "\n".join(lines)

def run_mntx():
    txs = fetch_latest()
    print(f"\n[+] ได้ทั้งหมด {len(txs):,} transactions ใน {HOURS_BACK}h\n")
    if not txs:
        send_telegram(f"⚠️ MNTx: ไม่มี transaction ใน {HOURS_BACK} ชั่วโมงที่ผ่านมา")
        return
    method_volume, method_count, from_uni_vol, from_uni_cnt, to_uni_vol, to_uni_cnt, _, ts_min, ts_max = analyze(txs)
    report = build_report(txs, method_volume, method_count, from_uni_vol, from_uni_cnt, to_uni_vol, to_uni_cnt, _, ts_min, ts_max)
    print(report)
    # send_telegram(report)


# ─────────────────────────────────────────
# TELEGRAM CHANNEL MONITOR (Telethon)
# ─────────────────────────────────────────

async def run_telegram_monitor():
    _channel_arg = int(CHANNEL_USERNAME) if CHANNEL_USERNAME.lstrip("-").isdigit() else CHANNEL_USERNAME
    tg_client = TelegramClient(SESSION_NAME, TG_API_ID, TG_API_HASH)

    await tg_client.start(phone=TG_PHONE)
    me = await tg_client.get_me()
    print(f"[*] Telethon: logged in as @{me.username}")

    entity = await tg_client.get_entity(_channel_arg)
    print(f"[*] Channel: {entity.title}")

    since = datetime.now(timezone.utc) - timedelta(hours=LOOKBACK_HOURS)
    target = TARGET_USERNAME.lower().lstrip("@")

    found = []
    async for msg in tg_client.iter_messages(entity):
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

    await tg_client.disconnect()

    if not found:
        summary = (
            f"[Daily Report] @{TARGET_USERNAME}\n"
            f"Channel: {entity.title}\n"
            f"ช่วงเวลา: {LOOKBACK_HOURS} ชั่วโมงที่ผ่านมา\n"
            f"──────────────────\n"
            f"ไม่พบข้อความจาก @{TARGET_USERNAME}"
        )
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
    send_telegram(summary)


# ─────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────

if __name__ == "__main__":
    check_ltv()
    run_twitter()
    run_mntx()
    asyncio.run(run_telegram_monitor())
