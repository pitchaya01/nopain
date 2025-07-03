import requests

# กำหนดช่วงราคา
lower_bound = 102_000
upper_bound = 110_000

# ดึงราคาปัจจุบัน BTCUSDT จาก Binance API
response = requests.get("https://api.binance.com/api/v3/ticker/price", params={"symbol": "BTCUSDT"})
data = response.json()
print(data)
current_price = float(data["price"])

# ตรวจสอบว่าราคาอยู่ในช่วงหรือไม่
if lower_bound <= current_price <= upper_bound:
    print("Yes")
else:
    print("No")
