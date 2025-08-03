import streamlit as st
import pandas as pd
from datetime import datetime
from pytz import timezone
from data_processing import process_option_data, sudden_liquidity_spike, detect_liquidity_zones
from analysis_functions import calculate_bias_scores, reversal_score, get_support_resistance_zones, is_in_zone
from telegram_notifications import send_liquidity_spike_alert, send_trade_signal, send_reversal_alert
from ui_components import display_market_summary, plot_price_with_sr

def handle_regular_trading_analysis(data, expiry, underlying, T, r, now):
    """Handle regular trading day analysis"""
    # Process option data with Greeks
    df = process_option_data(data, None, underlying, expiry, T, r)
    
    # Filter for relevant strikes
    atm_strike = min(df['strikePrice'], key=lambda x: abs(x - underlying))
    df = df[df['strikePrice'].between(atm_strike - 200, atm_strike + 200)]
    
    # Calculate bias scores
    bias_results, total_score = calculate_bias_scores(df, atm_strike, underlying)
    
    # Check for liquidity spikes
    check_liquidity_spikes(df)
    
    # Get support/resistance zones
    support_zone, resistance_zone = get_support_resistance_zones(df, underlying)
    st.session_state.support_zone = support_zone
    st.session_state.resistance_zone = resistance_zone
    
    # Update price data
    update_price_data(underlying, now)
    
    # Generate trade signals
    market_view = get_market_view(bias_results)
    suggested_trade, signal_sent = generate_trade_signals(
        bias_results, total_score, market_view, df, underlying, 
        support_zone, resistance_zone, now
    )
    
    return df, bias_results, total_score, market_view, suggested_trade, signal_sent

def check_liquidity_spikes(df):
    """Check for sudden liquidity spikes"""
    for _, row in df.iterrows():
        if sudden_liquidity_spike(row):
            send_liquidity_spike_alert(row)

def update_price_data(underlying, now):
    """Update price data in session state"""
    current_time_str = now.strftime("%H:%M:%S")
    new_row = pd.DataFrame([[current_time_str, underlying]], columns=["Time", "Spot"])
    st.session_state['price_data'] = pd.concat([st.session_state['price_data'], new_row], ignore_index=True)

def get_market_view(bias_results):
    """Get market view from ATM strike"""
    atm_row = next((row for row in bias_results if row["Zone"] == "ATM"), None)
    return atm_row['Verdict'] if atm_row else "Neutral"

def generate_trade_signals(bias_results, total_score, market_view, df, underlying, 
                         support_zone, resistance_zone, now):
    """Generate trade signals based on analysis"""
    suggested_trade = ""
    signal_sent = False
    
    support_str = f"{support_zone[1]} to {support_zone[0]}" if all(support_zone) else "N/A"
    resistance_str = f"{resistance_zone[0]} to {resistance_zone[1]}" if all(resistance_zone) else "N/A"
    
    for row in bias_results:
        if not is_in_zone(underlying, row['Strike'], row['Level']):
            continue

        if row['Level'] == "Support" and total_score >= 4 and "Bullish" in market_view:
            option_type = 'CE'
        elif row['Level'] == "Resistance" and total_score <= -4 and "Bearish" in market_view:
            option_type = 'PE'
        else:
            continue

        ltp = df.loc[df['strikePrice'] == row['Strike'], f'lastPrice_{option_type}'].values[0]
        iv = df.loc[df['strikePrice'] == row['Strike'], f'impliedVolatility_{option_type}'].values[0]
        
        # Calculate target based on S/R zones
        target = calculate_target(option_type, row['Strike'], ltp, iv, support_zone, resistance_zone)
        stop_loss = round(ltp * 0.8, 2)

        atm_signal = f"{'CALL' if option_type == 'CE' else 'PUT'} Entry (Bias Based at {row['Level']})"
        suggested_trade = f"Strike: {row['Strike']} {option_type} @ ₹{ltp} | 🎯 Target: ₹{target} | 🛑 SL: ₹{stop_loss}"

        # Send alerts
        send_trade_signal(atm_signal, suggested_trade, total_score, market_view, 
                         row, support_str, resistance_str, underlying, now)

        # Add to trade log
        st.session_state.trade_log.append({
            "Time": now.strftime("%H:%M:%S"),
            "Strike": row['Strike'],
            "Type": option_type,
            "LTP": ltp,
            "Target": target,
            "SL": stop_loss
        })

        signal_sent = True
        break
    
    return suggested_trade, signal_sent

def calculate_target(option_type, strike, ltp, iv, support_zone, resistance_zone):
    """Calculate target price based on S/R zones"""
    if option_type == 'CE' and resistance_zone[0]:
        # For Call, target based on distance to resistance
        target = round(ltp * (1 + (resistance_zone[0] - strike) / strike * 0.5), 2)
    elif option_type == 'PE' and support_zone[1]:
        # For Put, target based on distance to support
        target = round(ltp * (1 + (strike - support_zone[1]) / strike * 0.5), 2)
    else:
        # Fallback to IV based target if S/R not available
        target = round(ltp * (1 + iv / 100), 2)
    
    return target

def display_regular_analysis_results(underlying, market_view, total_score, support_zone, 
                                   resistance_zone, suggested_trade, df_summary, df, atm_strike):
    """Display regular analysis results"""
    support_str = f"{support_zone[1]} to {support_zone[0]}" if all(support_zone) else "N/A"
    resistance_str = f"{resistance_zone[0]} to {resistance_zone[1]}" if all(resistance_zone) else "N/A"
    
    # Display main summary
    display_market_summary(underlying, market_view, total_score, support_str, resistance_str)
    
    # Display price chart
    plot_price_with_sr()
    
    # Display trade suggestion
    if suggested_trade:
        atm_signal = "CALL Entry" if "CE" in suggested_trade else "PUT Entry"
        st.info(f"🔹 {atm_signal}\n{suggested_trade}")
    
    # Display option chain summary
    with st.expander("📊 Option Chain Summary"):
        st.dataframe(df_summary)
    
    # Display trade log
    if st.session_state.trade_log:
        st.markdown("### 📜 Trade Log")
        st.dataframe(pd.DataFrame(st.session_state.trade_log))

def handle_reversal_analysis(df, atm_strike, underlying, now):
    """Handle reversal signal analysis"""
    st.markdown("---")
    st.markdown("## 🔄 Reversal Signals (ATM ±2 Strikes)")
    
    # Calculate reversal scores
    df['ReversalScore'], df['ReversalDirection'] = zip(*df.apply(reversal_score, axis=1))
    
    # Filter for ATM ±2 strikes for display
    display_strikes = df[
        (df['strikePrice'] >= atm_strike - 100) & 
        (df['strikePrice'] <= atm_strike + 100)
    ].sort_values('strikePrice')
    
    # Show reversal table
    st.dataframe(
        display_strikes[['strikePrice', 'ReversalScore', 'ReversalDirection',
                        'changeinOpenInterest_CE', 'changeinOpenInterest_PE',
                        'impliedVolatility_CE', 'impliedVolatility_PE']]
        .sort_values("ReversalScore", ascending=False)
        .style.apply(lambda x: ['color: green' if v == "UP" else 'color: red' if v == "DOWN" else '' 
                              for v in x], subset=['ReversalDirection'])
    )
    
    # Check ATM strike for alerts
    atm_reversal_data = df[df['strikePrice'] == atm_strike].iloc[0] if not df[df['strikePrice'] == atm_strike].empty else None
    
    if atm_reversal_data is not None and atm_reversal_data['ReversalScore'] >= 2:
        send_reversal_alert(atm_reversal_data, atm_strike, underlying, now)

def handle_liquidity_zones(df, underlying):
    """Handle liquidity zones analysis"""
    st.markdown("## 💧 Liquidity Zones")
    spot_history = st.session_state.price_data['Spot'].tolist()
    liquidity_zones = detect_liquidity_zones(df, underlying, spot_history)
    
    if not liquidity_zones.empty:
        st.dataframe(liquidity_zones)
    else:
        st.warning("No significant liquidity zones detected")