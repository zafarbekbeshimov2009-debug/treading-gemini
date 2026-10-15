def analyze_market():
    url = f"https://api.binance.com/api/v3/klines?symbol={SYMBOL}&interval={INTERVAL}&limit=50"
    response = requests.get(url, timeout=10)
    data = response.json()
    
    # Ma'lumot kelganini tekshirish
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
    
    # NaN qiymatlarni tekshirish
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
