import requests
from datetime import datetime, timedelta
import re
import openai
import os
from collections import defaultdict
from datetime import datetime, timezone, timedelta
# ─────────────────────────────────────────
# CONFIG
# ─────────────────────────────────────────
API_KEY  = "HU6J9N3UF2GNK452D3WT9PCT5S3KJSM5A2"
CONTRACT = "0x5C697fee285B513711A816018DBb34DC0cFC4875"
CHAIN_ID = 1
DECIMALS = 18
MAX_ROWS  = 2000
PAGE_SIZE = 100
HOURS_BACK = 24   # ← เปลี่ยนตรงนี้เพื่อดูย้อนหลังกี่ชั่วโมง
 
UNISWAP_ADDR = "0x61192EB6ca9fe34a3Ccc5f4cd4bf6feFB77a037f".lower()
 
METHOD_MAP = {
    "0xdcb18521": "Decrease Stake",
    "0xa9059cbb": "Transfer",
    "0x12aa3caf": "Swap",
    "0x35138382": "Increase Stake",
}
 
# Telegram
TG_TOKEN  = "7718053957:AAHSHEXigIC3lc9xkUgXtVlPWIg74eikYd0"
TG_CHAT   = "6193006196"
 
ICT = timezone(timedelta(hours=7))
 
def ts_to_str(ts: int) -> str:
    return datetime.fromtimestamp(ts, tz=ICT).strftime("%Y-%m-%d %H:%M:%S ICT")
 
 
# ─────────────────────────────────────────
# TELEGRAM
# ─────────────────────────────────────────
def send_telegram(message: str):
    url = f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage"
    payload = {"chat_id": TG_CHAT, "text": message}
    try:
        r = requests.post(url, data=payload, timeout=10)
        r.raise_for_status()
        resp = r.json()
        if not resp.get("ok"):
            print(f"[!] Telegram error: {resp}")
        else:
            print("[+] ส่ง Telegram สำเร็จ")
    except Exception as e:
        print(f"[!] Telegram ส่งไม่ได้: {e}")
 
 
# ─────────────────────────────────────────
# FETCH
# ─────────────────────────────────────────
def fetch_latest() -> list:
    all_txs = []
    page = 1
    pages_needed = -(-MAX_ROWS // PAGE_SIZE)
 
    cutoff_ts = int((datetime.now(tz=timezone.utc) - timedelta(hours=HOURS_BACK)).timestamp())
    print(f"[*] ดึง tx ย้อนหลัง {HOURS_BACK}h (ตั้งแต่ {ts_to_str(cutoff_ts)})...")
 
    while page <= pages_needed:
        url = (
            f"https://api.etherscan.io/v2/api"
            f"?chainid={CHAIN_ID}"
            f"&module=account"
            f"&action=tokentx"
            f"&contractaddress={CONTRACT}"
            f"&page={page}"
            f"&offset={PAGE_SIZE}"
            f"&sort=desc"
            f"&apikey={API_KEY}"
        )
        resp = requests.get(url, timeout=15)
        data = resp.json()
 
        if data["status"] != "1":
            print(f"  [!] หยุดที่ page {page}: {data['message']} — {data['result']}")
            break
 
        batch = data["result"]
        filtered = [tx for tx in batch if int(tx.get("timeStamp", 0)) >= cutoff_ts]
        all_txs.extend(filtered)
        print(f"  page {page:>2}  total {len(batch)} tx  ใน {HOURS_BACK}h: {len(filtered)} tx  รวม {len(all_txs):,}")
 
        oldest_ts = int(batch[-1].get("timeStamp", 0)) if batch else 0
        if oldest_ts < cutoff_ts:
            print(f"  [i] ถึงช่วงเวลาที่ต้องการแล้ว หยุดดึง")
            break
 
        if len(batch) < PAGE_SIZE:
            print(f"  [i] ข้อมูลหมดแล้ว")
            break
 
        page += 1
 
    return all_txs[:MAX_ROWS]
 
 
# ─────────────────────────────────────────
# ANALYZE
# ─────────────────────────────────────────
def analyze(txs: list):
    dec = 10 ** DECIMALS
 
    method_volume = defaultdict(float)
    method_count  = defaultdict(int)
    unknown       = defaultdict(int)
 
    from_uni_vol = to_uni_vol = 0.0
    from_uni_cnt = to_uni_cnt = 0
    timestamps = []
 
    for tx in txs:
        volume    = int(tx.get("value", 0)) / dec
        from_addr = tx.get("from", "").lower()
        to_addr   = tx.get("to",   "").lower()
        ts        = int(tx.get("timeStamp", 0))
        timestamps.append(ts)
 
        mid  = tx.get("methodId", "0x")
        name = METHOD_MAP.get(mid)
 
        if name is None:
            unknown[mid] += 1
        else:
            method_volume[name] += volume
            method_count[name]  += 1
 
        if from_addr == UNISWAP_ADDR:
            from_uni_vol += volume
            from_uni_cnt += 1
        if to_addr == UNISWAP_ADDR:
            to_uni_vol += volume
            to_uni_cnt += 1
 
    ts_min = min(timestamps) if timestamps else 0
    ts_max = max(timestamps) if timestamps else 0
 
    return (method_volume, method_count,
            from_uni_vol, from_uni_cnt,
            to_uni_vol,   to_uni_cnt,
            unknown, ts_min, ts_max)
 
 
# ─────────────────────────────────────────
# BUILD REPORT STRING
# ─────────────────────────────────────────
def build_report(txs, method_volume, method_count,
                 from_uni_vol, from_uni_cnt,
                 to_uni_vol,   to_uni_cnt,
                 unknown, ts_min, ts_max) -> str:
 
    total_txs = len(txs)
    total_vol = sum(method_volume.values())
    net       = from_uni_vol - to_uni_vol
    direction = "NET ซื้อเข้า ↑" if net > 0 else "NET ขายออก ↓"
 
    lines = []
    lines.append(f"📊 MNTx — สรุปย้อนหลัง {HOURS_BACK} ชั่วโมง")
    lines.append(f"🕐 {ts_to_str(ts_min)}")
    lines.append(f"   ถึง {ts_to_str(ts_max)}")
    lines.append(f"📋 Total Tx : {total_txs:,} transactions")
    lines.append("")
 
    lines.append("── Method Volume ──")
    for name, vol in sorted(method_volume.items(), key=lambda x: -x[1]):
        cnt = method_count[name]
        pct = vol / total_vol * 100 if total_vol else 0
        lines.append(f"  {name:<16} {cnt:>5} tx  {vol:>14,.2f} MNTx ({pct:.1f}%)")
 
    lines.append("")
    lines.append("── Uniswap Flow ──")
    lines.append(f"  ซื้อ (FROM Uni)  {from_uni_cnt:>5} tx  {from_uni_vol:>14,.2f} MNTx")
    lines.append(f"  ขาย (TO Uni)    {to_uni_cnt:>5} tx  {to_uni_vol:>14,.2f} MNTx")
    lines.append(f"  Net Flow        {net:>+21,.2f} MNTx")
    lines.append(f"  {direction}")
 
    return "\n".join(lines)
 
 
# ─────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────
###===================================================
#usernames = ["club_wmtx"]
usernames = ["siamblockchain","bitcoinaddictth","BitcoinMagazine","IOHK_Charles","TheDePINCat","wmReclaim","worldmobileteam", "MrTelecoms","andrew_s_wm","CloverNodes","WMTxLady","hopenothype_io","wmchain","SebastienGllmt","MinswapIntern","ChristianRees"]
headers = {"X-API-Key": "new1_5bdebf52aa95464bad3576b4606ff85e"}
token = '7718053957:AAHSHEXigIC3lc9xkUgXtVlPWIg74eikYd0'
chat_id = '6193006196'
url = f"https://api.telegram.org/bot{token}/sendMessage"
all_tweets = []
if not os.getenv("OPENAI_API_KEY"):
    from dotenv import load_dotenv
    load_dotenv()  # จะโหลดค่า key จาก .env ถ้ามี

client = openai.OpenAI()
def send_telegram_text(message: str, token: str, chat_id: str) -> dict:
    """
    ส่งข้อความธรรมดาไป Telegram โดยรับเฉพาะข้อความที่เตรียมมาแล้ว
    :param message: ข้อความที่ต้องการส่ง
    :param token: Telegram Bot Token
    :param chat_id: chat id หรือ @channelusername
    :param parse_mode: "Markdown", "MarkdownV2", "HTML" หรือ None
    """
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": message,
    }


    try:
        r = requests.post(url, data=payload, timeout=10)
        r.raise_for_status()
        resp = r.json()
        if not resp.get("ok", False):
            raise TelegramAPIError(f"Telegram API returned error: {resp}")
        return resp
    except requests.RequestException as e:
        raise TelegramAPIError(f"HTTP error calling Telegram API: {e}") from e
def get_price_coingecko(ids=("bitcoin", "ethereum"), vs_currencies=("usd",)):
    """
    ดึงราคาจาก CoinGecko โดยระบุ coin ids และสกุลเงินอ้างอิง
    :param ids: tuple/list ของ coin id ตาม CoinGecko เช่น "bitcoin","ethereum"
    :param vs_currencies: tuple/list ของ fiat/crypto เปรียบเทียบ เช่น "usd","thb"
    :return: dict {"bitcoin": {"usd": 12345.67}, ...}
    """
    url = "https://api.coingecko.com/api/v3/simple/price"
    params = {
        "ids": ",".join(ids),
        "vs_currencies": ",".join(vs_currencies),
    }
    r = requests.get(url, params=params, timeout=10)
    r.raise_for_status()
    return r.json()
def normalized_abs_diff(pa, pb):
    # d in [0,1]
    m = max(pa, pb)
    return 0.0 if m == 0 else abs(pa - pb) / m
def remove_dollar_numbers(text):
    # Regular expression ที่หา $ และตัวเลขที่ตามมา ไม่จำเป็นต้องอยู่ต้นบรรทัด
    pattern = r'\$[\d,]+(?:\.\d+)?'
    # ลบข้อความ pattern ออกจาก string
    new_text = re.sub(pattern, '', text).strip()
    return new_text
def remove_urls(text):
    # ลบ pattern ของลิงก์ทั้งหมด (http, https, www. และ ลิงก์แบบไม่ใส่ www)
    return re.sub(r'http\S+|www\S+|https\S+', '', text, flags=re.MULTILINE)
def is_token_price_related(text):

    keywords = ["marketcap","sell","dip","price","ล้าง","แตก","hold","hodl","ath","buy","mc","sold","ขาย","ซื้อ","bear"] 
    lowered = text.lower()

    for kw in keywords:
        if kw.lower() in lowered:
            return True
    lowered = text.lower()
    """
    ใช้ OpenAI ช่วยแยกว่าเป็นข้อความเกี่ยวกับ 'ราคาโทเคน' หรือไม่
    คืนค่า True ถ้าเกี่ยวกับราคาหรือท่าทีตลาด, False ถ้าไม่เกี่ยว
    """
    prompt = (
        f"Please determine if the following text is talking about the price, market value, or price prediction of a token/cryptocurrency. or metketcap or sentiment such as price drop or high "
        f"Text is from twitter tweet or X .\n\n"
        f"If so, respond ONLY with 'RELATED'. If not, respond ONLY with 'NOT_RELATED'.\n\n"
        f"Text: {text}"
    )
    response = client.chat.completions.create(
        model="gpt-4o",
        messages = [{"role": "user", "content": prompt}],
        temperature=0
    )
    answer = response.choices[0].message.content.strip()
    return answer == "RELATED"

def translate_to_thai(text):
    """
    ใช้ OpenAI ช่วยแปลข้อความเป็นภาษาไทย
    """
    prompt = (
        "Please translate the following text into Thai language.\n\n"
        f"Text: {text}"
    )
    response = client.chat.completions.create(
        model="gpt-4o",
        messages = [{"role": "user", "content": prompt}],
        temperature=0.2
    )
    return response.choices[0].message.content.strip()
# วันเมื่อวาน (UTC)
# result=(is_token_price_related('บิตคอย ร่วงกว่า5000 usd ใน 24ชั่วโมง'))
# print(result)
# payload = {
#             'chat_id': chat_id,
#             'text': "test"
#         }
# r = requests.post(url, data=payload)
# print(r)
yesterday_utc = (datetime.utcnow() - timedelta(days=1)).date()
data_a=get_price_coingecko(["cardano"],["usd"])
ada_price=float(data_a['cardano']['usd'])
ltv_percent = (7097.73435225 / (29121.68587978 * ada_price)) * 100

#data_b=get_price_coingecko(["world-mobile-token"],["usd"])
#price_a=float(data_a['bitcoin']['usd'])
#price_b=float(data_b['world-mobile-token']['usd'])
is_helthy="no"
if ltv_percent > 60:
    is_helthy = "no"
    #send_telegram_text(str(ltv_percent),'7718053957:AAHSHEXigIC3lc9xkUgXtVlPWIg74eikYd0','6193006196')

#abs_p=round(normalized_abs_diff(price_a,price_b)*100,2)

#send_telegram_text(is_helthy,'7718053957:AAHSHEXigIC3lc9xkUgXtVlPWIg74eikYd0','6193006196')
for uname in usernames:
    url = "https://api.twitterapi.io/twitter/user/last_tweets"
    params = {"userName": uname,"includeReplies":"false"}
    response = requests.get(url, headers=headers, params=params)
    data = response.json()
 
    tweets = data['data']['tweets']
    
    for tweet in tweets:
        created_at_str = tweet.get("createdAt")
        created_at_dt = datetime.strptime(created_at_str, "%a %b %d %H:%M:%S %z %Y")
        # ใช้ .date() เปรียบเทียบเฉพาะปี-เดือน-วัน
        if created_at_dt.date() == yesterday_utc:
            tweet_info = {
                "user": uname,
                "text": tweet.get("text"),
                "url": tweet.get("url"),
                "isReply": tweet.get("isReply"),
                "createdAt": tweet.get("createdAt"),
            }
            all_tweets.append(tweet_info)

# แสดงผล tweet ของเมื่อวานนี้
        
for t in all_tweets:
    result=(is_token_price_related(t["text"]))
    if(result==False):
        message = (
            "------\n"
            f"User      : {t['user']}\n"
            f"Text      : {t['text']}\n"
            # f"Thai      : {translate_to_thai(t['text'])}"
            f"CreatedAt : {t['createdAt']}\n"
        )
        payload = {
            'chat_id': chat_id,
            'text': remove_dollar_numbers(remove_urls(message))
        }
        token = '7718053957:AAHSHEXigIC3lc9xkUgXtVlPWIg74eikYd0'
        chat_id = '6193006196'
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        r = requests.post(url, data=payload)
        print(r.json())


#=======================================================================================
txs = fetch_latest()
print(f"\n[+] ได้ทั้งหมด {len(txs):,} transactions ใน {HOURS_BACK}h\n")
 
if not txs:
    msg = f"⚠️ MNTx: ไม่มี transaction ใน {HOURS_BACK} ชั่วโมงที่ผ่านมา"
    print(msg)
    send_telegram(msg)
    exit(0)
(method_volume, method_count,
     from_uni_vol, from_uni_cnt,
     to_uni_vol,   to_uni_cnt,
     unknown, ts_min, ts_max) = analyze(txs)
 
report = build_report(txs, method_volume, method_count,
                          from_uni_vol, from_uni_cnt,
                          to_uni_vol,   to_uni_cnt,
                          unknown, ts_min, ts_max)
 
    # แสดงใน terminal
 print(report)
 
    # ส่ง Telegram
send_telegram(report)
