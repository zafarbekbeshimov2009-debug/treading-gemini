import os
import time
import requests
import pandas as pd
import numpy as np
from telegram import Bot
import asyncio
import logging
from threading import Thread
from flask import Flask

# Flask server (Render uxlatib qo'ymasligi uchun)
app_web = Flask('')

@app_web.route('/')
def home():
    return "Bot is running 24/7!"

def run_web():
    app_web.run(host='0.0.0.0', port=int(os.environ.get("PORT", 8080)))

def keep_alive():
    t = Thread(target=run_web)
    t.start()

# O'z-o'ziga ping yuborish (UptimeRobot shart emasligi uchun)
def self_ping():
    app_url = os.environ.get("RENDER_EXTERNAL_URL")
    if app_url:
        while True:
            try:
                requests.get(app_url, timeout=10)
                logging.info("Self-ping yuborildi (Render uxlab qolmasligi uchun).")
            except Exception as e:
                logging.error(f"Self-ping xatosi: {e}")
            # Har 7 daqiqada bir marta o'ziga so'rov yuboradi
            time.sleep(420)

def run_ping_thread():
    t = Thread(target=self_ping)
    t.start()

# Logging
logging.basicConfig(
    format='%(asctime)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.environ.get("CHAT_ID")
SYMBOL = "BTCUSDT"
INTERVAL = "15m"

bot = Bot(token=TELEGRAM_BOT_TOKEN)

def calculate_rsi(data, window=14):
    delta = data.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=window).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=window).mean()
    rs = gain / loss
    return 100 - (100 / (1.0 + rs))

def analyze_market():
    url = f"https://api.binance.com/api/v3/klines?symbol={SYMBOL}&interval={INTERVAL}&limit=50"
    response = requests.get(url, timeout=10)
    data = response.json()
    
    if not isinstance(data, list) or len(data) < 30:
        return None
        
    df = pd.DataFrame(data, columns=[
        'open_time', 'open', 'high', 'low', 'close', 'volume',
        'close_time', 'quote_asset_volume', 'number_of_trades',
        'taker_buy_base_asset_volume', 'taker_buy_quote_asset_volume', 'ignore'
    ])
    
    df['close'] = df['close'].astype(float)
    df['volume'] = df['volume'].astype(float)
    
    df['rsi'] = calculate_rsi(df['close'], window=14)
    df['avg_volume'] = df['volume'].rolling(window=20).mean()
    
    df = df.dropna()
    if df.empty:
        return None
        
    latest = df.iloc[-1]
    prev_avg_vol = latest['avg_volume']
    current_vol = latest['volume']
    current_rsi = latest['rsi']
    current_price = latest['close']
    
    is_volume_spike = current_vol > (prev_avg_vol * 2.5)
    is_rsi_bullish = 45 < current_rsi < 75
    
    if is_volume_spike and is_rsi_bullish:
        multiplier = current_vol / prev_avg_vol
        message = (
            f"🚨 **KESKIN KO'TARILISH (PUMP) SIGNALI!**\n\n"
            f"🪙 **Juftlik:** {SYMBOL}\n"
            f"💰 **Joriy narx:** ${current_price:,.2f}\n"
            f"📊 **RSI (14):** {current_rsi:.2f}\n"
            f"📈 **Hajm sakrashi:** O'rtachadan **{multiplier:.1f}x** baland!\n\n"
            f"⚡ *Strategiya:* Volume Spike + RSI tasdiqlandi."
        )
        return message
    return None

async def main():
    logging.info("Bot Render'da ishga tushdi va bozorni kuzatmoqda...")
    while True:
        try:
            signal = analyze_market()
            if signal:
                await bot.send_message(chat_id=CHAT_ID, text=signal, parse_mode="Markdown")
                logging.info("Signal yuborildi!")
                await asyncio.sleep(900) 
            else:
                await asyncio.sleep(60)
        except Exception as e:
            logging.error(f"Xatolik yuz berdi: {e}. 30 soniyadan so'ng qayta uriniladi...")
            await asyncio.sleep(30)

if __name__ == "__main__":
    # Veb serverni yoqamiz
    keep_alive()
    # O'z-o'ziga ping yuborishni boshlaymiz (UptimeRobot o'rniga)
    run_ping_thread()
    # Asosiy bot siklini ishga tushiramiz
    asyncio.run(main())
