import requests

# กำหนดช่วงราคา
lower_bound = 102_000
upper_bound = 110_000

# ดึงราคาปัจจุบัน BTCUSDT จาก Binance API
resp = requests.get(
    "https://api.coingecko.com/api/v3/simple/price?ids=bitcoin&vs_currencies=usd"
)
print(resp.json())
current_price = resp.json()["bitcoin"]["usd"]
  

# ตรวจสอบว่าราคาอยู่ในช่วงหรือไม่
if lower_bound <= current_price <= upper_bound:
    print("Yes")
else:
    print("No")
