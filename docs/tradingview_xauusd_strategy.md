# TradingView XAUUSD Profitable Strategy Parameters

Berdasarkan riset mendalam dari berbagai strategi *Profitable* di TradingView khusus untuk *Gold* (XAUUSD), pergerakan emas sangat dipengaruhi oleh volatilitas dan faktor makroekonomi (seperti DXY/US Dollar Index). Karena itu, penggunaan indikator standar sering kali memberikan sinyal palsu (whipsaw).

Berikut adalah parameter dan metode yang telah terbukti paling optimal dan direkomendasikan untuk diimplementasikan ke dalam *Decision Engine* dan *Risk Engine* XEDY:

## 1. Metode Utama: Multi-Factor Confluence (Trend + Volatility + Smart Money Concepts)

Strategi terbaik tidak bergantung pada satu indikator tunggal, melainkan konfluensi (pertemuan) dari beberapa faktor pendukung:
- **Trend Direction:** EMA (Exponential Moving Average)
- **Volatility Filter:** ATR (Average True Range)
- **Institutional Zones:** Smart Money Concepts (SMC) - Order Blocks (OB) & Fair Value Gaps (FVG)
- **Macro Correlation:** Inversi DXY (US Dollar Index)

## 2. Parameter Optimal (Timeframe M15 - H1)

### A. Moving Average (Trend Alignment)
- **EMA Crossover:** Menggunakan **EMA 50** dan **EMA 100**.
- **Rules:** 
  - Hanya cari setup BUY jika harga berada di atas EMA 50 dan EMA 100 (Uptrend).
  - Hanya cari setup SELL jika harga berada di bawah EMA 50 dan EMA 100 (Downtrend).

### B. ATR (Average True Range) - Volatility Adjusted Risk
XAUUSD memiliki ekor lilin (wicks) yang panjang. ATR digunakan untuk menentukan dinamis *Stop Loss* (SL) dan *Take Profit* (TP) agar tidak mudah tersentuh oleh volatilitas normal market.
- **ATR Period:** 14
- **Stop Loss Multiplier:** **1.5x hingga 2.0x ATR**.
- **Take Profit Multiplier:** **3.0x ATR** (Mengejar Risk/Reward rasio minimal 1:1.5 atau 1:2).

### C. Momentum Confirmation (RSI / MACD)
- **RSI Period:** 14
- **Overbought/Oversold Filter:** Untuk menghindari "whipsaw", modifikasi batas RSI XAUUSD menjadi **Level 70 (Overbought)** dan **Level 30 (Oversold)**.
- **Rules:** Entry buy ideal saat RSI memantul dari level 30-40 menuju ke atas, sejalan dengan tren EMA.

### D. Smart Money Concepts (SMC)
- **Order Blocks (OB):** Identifikasi candle terakhir sebelum pergerakan impulsif (break of structure). XAUUSD sering melakukan *re-test* ke area OB ini sebelum melanjutkan tren.
- **Fair Value Gaps (FVG):** Gunakan FVG sebagai area target profit atau zona pantulan entry.

### E. DXY Correlation Filter (The Golden Rule)
- Emas memiliki korelasi negatif yang sangat kuat dengan US Dollar.
- **Rules:** Sebelum mengeksekusi order BUY pada XAUUSD, pastikan DXY sedang dalam struktur *Downtrend* atau minimal menunjukkan pelemahan (Bearish). Jika DXY sedang Bullish kuat, *Batal/Ignore* sinyal BUY XAUUSD.

---

## 3. Implementasi ke XEDY (ACTIVE_METHOD)

Berdasarkan parameter di atas, disarankan untuk mengembangkan atau mengoptimalkan metode `ACTIVE_METHOD` pada sistem menjadi pendekatan **SMC + ATR Dynamic Risk**.

**Rekomendasi Update di .env:**
```env
# Gunakan timeframe M15 untuk keseimbangan volatilitas dan sinyal
AVERAGING_TIMEFRAME=M15
# Pertahankan lot tunggal tanpa averaging agar terhindar dari drawdown saat trend panjang
AVERAGING_MAX_POSITIONS=1
# Menggunakan ATR untuk proteksi stop loss
AVERAGING_ATR_MULTIPLIER=1.5
```
