import streamlit as st
import pandas as pd
from datetime import datetime
from pytz import timezone
from analysis_functions import expiry_bias_score, expiry_entry_signal, determine_level, get_support_resistance_zones
from telegram_notifications import send_telegram_message, send_expiry_day_signal

def is_expiry_day(today, expiry_date):
    """Check if today is expiry day"""
    return today.date() == expiry_date.date()

def process_expiry_day_data(records, expiry, underlying, prev_close):
    """Process data specifically for expiry day"""
    calls, puts = [], []
    
    for item in records:
        if 'CE' in item and item['CE']['expiryDate'] == expiry:
            ce = item['CE']
            ce['previousClose_CE'] = prev_close
            ce['underlyingValue'] = underlying
            calls.append(ce)
        if 'PE' in item and item['PE']['expiryDate'] == expiry:
            pe = item['PE']
            pe['previousClose_PE'] = prev_close
            pe['underlyingValue'] = underlying
            puts.append(pe)
    
    df_ce = pd.DataFrame(calls)
    df_pe = pd.DataFrame(puts)
    df = pd.merge(df_ce, df_pe, on='strikePrice', suffixes=('_CE', '_PE')).sort_values('strikePrice')
    
    return df

def filter_atm_strikes(df, underlying):
    """Filter for ATM ±2 strikes for expiry day analysis"""
    atm_strike = min(df['strikePrice'], key=lambda x: abs(x - underlying))
    return df[df['strikePrice'].between(atm_strike - 100, atm_strike + 100)]

def handle_expiry_day_analysis(data, expiry, underlying, prev_close, now):
    """Handle complete expiry day analysis"""
    st.info("""
📅 **EXPIRY DAY DETECTED**
- Using specialized expiry day analysis
- IV Collapse, OI Unwind, Volume Spike expected
- Modified signals will be generated
""")
    send_telegram_message("⚠️ Expiry Day Detected. Using special expiry analysis.")
    
    # Store spot history for expiry day
    current_time_str = now.strftime("%H:%M:%S")
    new_row = pd.DataFrame([[current_time_str, underlying]], columns=["Time", "Spot"])
    st.session_state['price_data'] = pd.concat([st.session_state['price_data'], new_row], ignore_index=True)
    
    st.markdown(f"### 📍 Spot Price: {underlying}")
    
    # Process records with expiry day logic
    records = data['records']['data']
    df = process_expiry_day_data(records, expiry, underlying, prev_close)
    
    # Get ATM strike and filter for ATM ±2 strikes
    df = filter_atm_strikes(df, underlying)
    
    # Get support/resistance levels
    df['Level'] = df.apply(determine_level, axis=1)
    support_strikes = df[df['Level'] == "Support"]['strikePrice'].unique()
    resistance_strikes = df[df['Level'] == "Resistance"]['strikePrice'].unique()
    
    # Get support/resistance zones for target calculation
    support_zone, resistance_zone = get_support_resistance_zones(df, underlying)
    st.session_state.support_zone = support_zone
    st.session_state.resistance_zone = resistance_zone
    
    # Generate expiry day signals with S/R based targets
    expiry_signals = expiry_entry_signal(df, support_strikes, resistance_strikes)
    
    return df, expiry_signals

def display_expiry_signals(expiry_signals, underlying, now):
    """Display expiry day signals"""
    st.markdown("### 🎯 Expiry Day Signals")
    
    if expiry_signals:
        for signal in expiry_signals:
            st.success(f"""
            {signal['type']} at {signal['strike']} 
            (Score: {signal['score']:.1f}, LTP: ₹{signal['ltp']}, Target: ₹{signal['target']})
            Reason: {signal['reason']}
            """)
            
            # Add to trade log with S/R based targets
            st.session_state.trade_log.append({
                "Time": now.strftime("%H:%M:%S"),
                "Strike": signal['strike'],
                "Type": 'CE' if 'CALL' in signal['type'] else 'PE',
                "LTP": signal['ltp'],
                "Target": signal['target'],
                "SL": round(signal['ltp'] * 0.8, 2)
            })
            
            # Send Telegram alert
            send_expiry_day_signal(signal, underlying)
    else:
        st.warning("No strong expiry day signals detected")

def display_expiry_option_chain(df):
    """Display expiry day specific option chain"""
    with st.expander("📊 Expiry Day Option Chain (ATM ±2 Strikes)"):
        df['ExpiryBiasScore'] = df.apply(expiry_bias_score, axis=1)
        st.dataframe(df[['strikePrice', 'ExpiryBiasScore', 'lastPrice_CE', 'lastPrice_PE', 
                       'changeinOpenInterest_CE', 'changeinOpenInterest_PE',
                       'bidQty_CE', 'bidQty_PE']])