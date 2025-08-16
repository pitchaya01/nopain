import requests
from datetime import datetime, timedelta
import re
import openai
import os
usernames = ["siamblockchain","BitcoinMagazine","IOHK_Charles", "MrTelecoms","CloverNodes","WMTxLady","hopenothype_io","wmchain","SebastienGllmt","MinswapIntern","ChristianRees","SebastienGllmt","worldmobileteam"]
headers = {"X-API-Key": "e9636d13f522474b8bcfe3cad9c44d03"}
token = '7718053957:AAHSHEXigIC3lc9xkUgXtVlPWIg74eikYd0'
chat_id = '6193006196'
url = f"https://api.telegram.org/bot{token}/sendMessage"
all_tweets = []
if not os.getenv("OPENAI_API_KEY"):
    from dotenv import load_dotenv
    load_dotenv()  # จะโหลดค่า key จาก .env ถ้ามี

client = openai.OpenAI()
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
 
for uname in usernames:
    url = "https://api.twitterapi.io/twitter/user/last_tweets"
    params = {"userName": uname,"includeReplies":"true"}
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
 
