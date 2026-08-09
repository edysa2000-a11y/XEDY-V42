import re
import sys

def main():
    with open('c:/Antigravity/Project/XEDY Mission Control/backend/scripts/scrape_news.py', 'r', encoding='utf-8') as f:
        content = f.read()

    # 1. Update get_live_multi_asset_prices
    content = content.replace(
        'prices = {"XAUUSD": 0.0, "USOIL": 0.0, "DXY": 0.0, "US10Y": 0.0}',
        'prices = {"XAUUSD": 0.0, "USOIL": 0.0, "DXY": 0.0, "US10Y": 0.0, "SPX": 0.0, "DJI": 0.0, "DAX": 0.0, "NI225": 0.0}'
    )
    content = content.replace(
        '"tickers": ["FX_IDC:XAUUSD", "TVC:USOIL", "TVC:DXY", "TVC:US10Y"],',
        '"tickers": ["FX_IDC:XAUUSD", "TVC:USOIL", "TVC:DXY", "TVC:US10Y", "SP:SPX", "TVC:DJI", "XETR:DAX", "TVC:NI225"],'
    )
    content = content.replace(
        'elif "US10Y" in ticker: prices["US10Y"] = close_price',
        'elif "US10Y" in ticker: prices["US10Y"] = close_price\n                    elif "SPX" in ticker: prices["SPX"] = close_price\n                    elif "DJI" in ticker: prices["DJI"] = close_price\n                    elif "DAX" in ticker: prices["DAX"] = close_price\n                    elif "NI225" in ticker: prices["NI225"] = close_price'
    )

    # 2. Update prices_str and system_prompt
    prices_str_old = """        f"- US Dollar Index (DXY): {prices.get('DXY', 0.0):.2f}\\n"
        f"- US 10Y Treasury Yield: {prices.get('US10Y', 0.0):.2f}%\\n"
    )"""
    prices_str_new = """        f"- US Dollar Index (DXY): {prices.get('DXY', 0.0):.2f}\\n"
        f"- US 10Y Treasury Yield: {prices.get('US10Y', 0.0):.2f}%\\n"
        f"- S&P 500 (SPX): {prices.get('SPX', 0.0):.2f}\\n"
        f"- Dow Jones (DJI): {prices.get('DJI', 0.0):.2f}\\n"
        f"- DAX 40 (DAX): {prices.get('DAX', 0.0):.2f}\\n"
        f"- Nikkei 225 (NI225): {prices.get('NI225', 0.0):.2f}\\n"
    )"""
    content = content.replace(prices_str_old, prices_str_new)

    sys_prompt_old = "study the cross-market prices (Gold vs DXY, Yields, and Oil),"
    sys_prompt_new = "study the cross-market prices (Gold vs DXY, Yields, Oil, and Global Stock Indices like SPX, DJI, DAX, Nikkei),"
    content = content.replace(sys_prompt_old, sys_prompt_new)

    # 3. Dynamic Arrows in tg_msg_p2 and tg_msg_p3
    arrow_logic = """
    bias_clean = str(analysis.get('bias')).split('_')[0]
    
    # Dynamic arrows logic
    dx_arrow = "↓" if dx_icon == "🟢" else "↑" if dx_icon == "🔴" else "↕"
    us_arrow = "↓" if us_icon == "🟢" else "↑" if us_icon == "🔴" else "↕"
    e_arrow = "↑" if e_icon == "🟢" else "↓" if e_icon == "🔴" else "↕"
    risk_arrow = "↓" if m_icon == "🟢" else "↑" if m_icon == "🔴" else "↕"
    t_arrow = "↑" if f_icon == "🔴" else "↓"
"""
    content = content.replace("    bias_clean = str(analysis.get('bias')).split('_')[0]", arrow_logic)

    # 4. Replace hardcoded arrows in text block
    content = content.replace("DXY        ↓  {dx_icon}", "DXY        {dx_arrow}  {dx_icon}")
    content = content.replace("US10Y      ↓  {us_icon}", "US10Y      {us_arrow}  {us_icon}")
    content = content.replace("Real Yield ↓  {us_icon}", "Real Yield {us_arrow}  {us_icon}")
    
    content = content.replace("DXY        ↓  → GOLD {dx_icon}", "DXY        {dx_arrow}  → GOLD {dx_icon}")
    content = content.replace("US10Y      ↓  → GOLD {us_icon}", "US10Y      {us_arrow}  → GOLD {us_icon}")
    content = content.replace("Real Yield ↓  → GOLD {us_icon}", "Real Yield {us_arrow}  → GOLD {us_icon}")
    content = content.replace("Oil        ↑  → Inflation Risk {e_icon}", "Oil        {e_arrow}  → Inflation Risk {e_icon}")
    content = content.replace("Risk Assets→ Defensive Flow {m_icon}", "Risk Assets {risk_arrow} → Defensive Flow {m_icon}")

    with open('c:/Antigravity/Project/XEDY Mission Control/backend/scripts/scrape_news.py', 'w', encoding='utf-8') as f:
        f.write(content)
    print("Patched indices and dynamic arrows successfully")

if __name__ == '__main__':
    main()
