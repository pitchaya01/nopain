import requests
from datetime import datetime, timedelta
import re
import openai
import os
#usernames = ["club_wmtx"]
usernames = ["siamblockchain","BitcoinMagazine","IOHK_Charles","TheDePINCat","wmReclaim","worldmobileteam", "MrTelecoms","andrew_s_wm","CloverNodes","WMTxLady","hopenothype_io","wmchain","SebastienGllmt","MinswapIntern","ChristianRees"]
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
    send_telegram_text(str(ltv_percent),'7718053957:AAHSHEXigIC3lc9xkUgXtVlPWIg74eikYd0','6193006196')

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
 
