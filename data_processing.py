import streamlit as st
import requests
import pandas as pd
import numpy as np
from datetime import datetime
import math
from scipy.stats import norm
from pytz import timezone

def fetch_option_chain_data():
    """Fetch option chain data from NSE"""
    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        session = requests.Session()
        session.headers.update(headers)
        session.get("https://www.nseindia.com", timeout=5)
        url = "https://www.nseindia.com/api/option-chain-indices?symbol=NIFTY"
        response = session.get(url, timeout=10)
        data = response.json()
        
        # Get previous close data
        prev_close_url = "https://www.nseindia.com/api/equity-stockIndices?index=NIFTY%2050"
        prev_close_data = session.get(prev_close_url, timeout=10).json()
        prev_close = prev_close_data['data'][0]['previousClose']
        
        return data, prev_close, session
    except Exception as e:
        st.error(f"Error fetching data: {e}")
        return None, None, None

def process_option_data(data, prev_close, underlying, expiry, T, r):
    """Process raw option data into structured format"""
    records = data['records']['data']
    calls, puts = [], []

    for item in records:
        if 'CE' in item and item['CE']['expiryDate'] == expiry:
            ce = item['CE']
            ce['previousClose_CE'] = prev_close
            ce['underlyingValue'] = underlying
            if ce['impliedVolatility'] > 0:
                greeks = calculate_greeks('CE', underlying, ce['strikePrice'], T, r, ce['impliedVolatility'] / 100)
                ce.update(dict(zip(['Delta', 'Gamma', 'Vega', 'Theta', 'Rho'], greeks)))
            calls.append(ce)

        if 'PE' in item and item['PE']['expiryDate'] == expiry:
            pe = item['PE']
            pe['previousClose_PE'] = prev_close
            pe['underlyingValue'] = underlying
            if pe['impliedVolatility'] > 0:
                greeks = calculate_greeks('PE', underlying, pe['strikePrice'], T, r, pe['impliedVolatility'] / 100)
                pe.update(dict(zip(['Delta', 'Gamma', 'Vega', 'Theta', 'Rho'], greeks)))
            puts.append(pe)

    df_ce = pd.DataFrame(calls)
    df_pe = pd.DataFrame(puts)
    df = pd.merge(df_ce, df_pe, on='strikePrice', suffixes=('_CE', '_PE')).sort_values('strikePrice')
    
    return df

def calculate_greeks(option_type, S, K, T, r, sigma):
    """Calculate option Greeks"""
    d1 = (math.log(S / K) + (r + 0.5 * sigma**2) * T) / (sigma * math.sqrt(T))
    d2 = d1 - sigma * math.sqrt(T)
    delta = norm.cdf(d1) if option_type == 'CE' else -norm.cdf(-d1)
    gamma = norm.pdf(d1) / (S * sigma * math.sqrt(T))
    vega = S * norm.pdf(d1) * math.sqrt(T) / 100
    theta = (- (S * norm.pdf(d1) * sigma) / (2 * math.sqrt(T)) - r * K * math.exp(-r * T) * norm.cdf(d2)) / 365 if option_type == 'CE' else (- (S * norm.pdf(d1) * sigma) / (2 * math.sqrt(T)) + r * K * math.exp(-r * T) * norm.cdf(-d2)) / 365
    rho = (K * T * math.exp(-r * T) * norm.cdf(d2)) / 100 if option_type == 'CE' else (-K * T * math.exp(-r * T) * norm.cdf(-d2)) / 100
    return round(delta, 4), round(gamma, 4), round(vega, 4), round(theta, 4), round(rho, 4)

def detect_liquidity_zones(df, spot_price, price_history):
    """Detect liquidity zones based on price action and volume"""
    zones = []
    unique_strikes = df['strikePrice'].unique()
    
    for strike in unique_strikes:
        revisit_count = sum((abs(spot - strike) <= 10) for spot in price_history)
        strike_data = df[df['strikePrice'] == strike]
        
        avg_volume = (strike_data['totalTradedVolume_CE'].mean() + 
                     strike_data['totalTradedVolume_PE'].mean())
        avg_oi_change = (strike_data['changeinOpenInterest_CE'].mean() + 
                        strike_data['changeinOpenInterest_PE'].mean())
        
        if revisit_count >= 3 and avg_volume > 5000 and avg_oi_change > 0:
            zones.append({
                'strike': strike,
                'revisits': revisit_count,
                'volume': round(avg_volume),
                'oi_change': round(avg_oi_change)
            })
    return pd.DataFrame(zones)

def sudden_liquidity_spike(row):
    """Detect sudden liquidity spikes"""
    ce_spike = row['changeinOpenInterest_CE'] > 1.5 * row['openInterest_CE'] and row['totalTradedVolume_CE'] > 1500
    pe_spike = row['changeinOpenInterest_PE'] > 1.5 * row['openInterest_PE'] and row['totalTradedVolume_PE'] > 1500
    return ce_spike or pe_spike
