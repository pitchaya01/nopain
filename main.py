import requests

# กำหนดช่วงราคา
lower_bound = 110_000
upper_bound = 120_000

# ดึงราคาปัจจุบัน BTCUSDT จาก Binance API
resp = requests.get(
    "https://api.coingecko.com/api/v3/simple/price?ids=bitcoin&vs_currencies=usd"
)

current_price = resp.json()["bitcoin"]["usd"]
  
result=''
# ตรวจสอบว่าราคาอยู่ในช่วงหรือไม่
if lower_bound <= current_price <= upper_bound:
    result="Yes"
else:
     result="No"
token = '7718053957:AAHSHEXigIC3lc9xkUgXtVlPWIg74eikYd0'
chat_id = '6193006196'
message = str(lower_bound)+'to'+str(upper_bound)+result

url = f"https://api.telegram.org/bot{token}/sendMessage"
payload = {
    'chat_id': chat_id,
    'text': message
}

r = requests.post(url, data=payload)
print(r.json())
