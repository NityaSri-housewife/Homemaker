import streamlit as st
import requests
import pandas as pd
import numpy as np
from datetime import datetime, time
import math
from scipy.stats import norm
from pytz import timezone
import traceback
import time as time_module

@st.cache_data(ttl=60)  # Cache for 1 minute to improve performance
def fetch_option_chain_data():
    """Fetch option chain data from NSE with enhanced resilience"""
    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        session = requests.Session()
        session.headers.update(headers)
        
        # Initialize NSE session with retry
        session_response = fetch_with_retry(session, "https://www.nseindia.com", max_retries=3)
        if not session_response:
            return None, None, None
        
        # Fetch option chain data with retry
        url = "https://www.nseindia.com/api/option-chain-indices?symbol=NIFTY"
        response = fetch_with_retry(session, url, max_retries=3)
        if not response:
            return None, None, None
            
        data = response.json()
        
        # Enhanced data validation
        if not data or 'records' not in data:
            st.error("❌ Malformed API response - missing records")
            return None, None, None
            
        if 'data' not in data['records']:
            st.error("❌ Malformed API response - missing data in records")
            return None, None, None
            
        if not data['records']['data']:
            st.error("❌ Empty option chain data received")
            return None, None, None
        
        # Get previous close data with retry
        prev_close_url = "https://www.nseindia.com/api/equity-stockIndices?index=NIFTY%2050"
        prev_close_response = fetch_with_retry(session, prev_close_url, max_retries=3)
        
        if prev_close_response:
            prev_close_data = prev_close_response.json()
            if prev_close_data and 'data' in prev_close_data and prev_close_data['data']:
                prev_close = prev_close_data['data'][0].get('previousClose', 0)
            else:
                prev_close = 0
                st.warning("⚠️ Could not fetch previous close data")
        else:
            prev_close = 0
            st.warning("⚠️ Previous close data unavailable")
        
        return data, prev_close, session
        
    except Exception as e:
        error_msg = f"Error fetching data: {str(e)}"
        st.error(f"❌ {error_msg}")
        
        # Send detailed error to Telegram for debugging
        detailed_error = f"❌ Data Fetch Error:\n{traceback.format_exc()}"
        try:
            from telegram_notifications import send_telegram_message
            send_telegram_message(detailed_error)
        except:
            pass  # Don't let Telegram errors break the main flow
            
        return None, None, None

def fetch_with_retry(session, url, max_retries=3, timeout=10):
    """Fetch URL with exponential backoff retry"""
    for attempt in range(max_retries):
        try:
            response = session.get(url, timeout=timeout)
            if response.status_code == 200:
                return response
            else:
                st.warning(f"⚠️ API returned status {response.status_code}, attempt {attempt + 1}")
                
        except requests.exceptions.Timeout:
            st.warning(f"⚠️ Request timeout, attempt {attempt + 1}")
        except requests.exceptions.ConnectionError:
            st.warning(f"⚠️ Connection error, attempt {attempt + 1}")
        except Exception as e:
            st.warning(f"⚠️ Request failed: {str(e)}, attempt {attempt + 1}")
        
        if attempt < max_retries - 1:
            wait_time = 2 ** attempt  # Exponential backoff: 1s, 2s, 4s
            time_module.sleep(wait_time)
    
    st.error(f"❌ Failed to fetch data after {max_retries} attempts")
    return None

def process_option_data(data, prev_close, underlying, expiry, T, r):
    """Process raw option data into structured format with validation"""
    try:
        records = data['records']['data']
        calls, puts = [], []

        for item in records:
            # Validate item structure
            if not isinstance(item, dict):
                continue
                
            # Process CE data
            if 'CE' in item and isinstance(item['CE'], dict):
                ce = item['CE'].copy()
                
                # Validate required fields
                required_fields = ['strikePrice', 'expiryDate', 'impliedVolatility', 'lastPrice']
                if all(field in ce for field in required_fields):
                    ce['previousClose_CE'] = prev_close
                    ce['underlyingValue'] = underlying
                    
                    if ce['impliedVolatility'] > 0 and ce['strikePrice'] > 0:
                        try:
                            greeks = calculate_greeks('CE', underlying, ce['strikePrice'], T, r, ce['impliedVolatility'] / 100)
                            ce.update(dict(zip(['Delta', 'Gamma', 'Vega', 'Theta', 'Rho'], greeks)))
                        except:
                            # Set default values if Greek calculation fails
                            ce.update({'Delta': 0, 'Gamma': 0, 'Vega': 0, 'Theta': 0, 'Rho': 0})
                    
                    calls.append(ce)

            # Process PE data
            if 'PE' in item and isinstance(item['PE'], dict):
                pe = item['PE'].copy()
                
                # Validate required fields
                if all(field in pe for field in required_fields):
                    pe['previousClose_PE'] = prev_close
                    pe['underlyingValue'] = underlying
                    
                    if pe['impliedVolatility'] > 0 and pe['strikePrice'] > 0:
                        try:
                            greeks = calculate_greeks('PE', underlying, pe['strikePrice'], T, r, pe['impliedVolatility'] / 100)
                            pe.update(dict(zip(['Delta', 'Gamma', 'Vega', 'Theta', 'Rho'], greeks)))
                        except:
                            # Set default values if Greek calculation fails
                            pe.update({'Delta': 0, 'Gamma': 0, 'Vega': 0, 'Theta': 0, 'Rho': 0})
                    
                    puts.append(pe)

        if not calls or not puts:
            st.error("❌ No valid option data found")
            return pd.DataFrame()

        df_ce = pd.DataFrame(calls)
        df_pe = pd.DataFrame(puts)
        
        # Validate DataFrames
        if df_ce.empty or df_pe.empty:
            st.error("❌ Empty option chain after processing")
            return pd.DataFrame()
        
        # Merge on strikePrice with validation
        df = pd.merge(df_ce, df_pe, on='strikePrice', suffixes=('_CE', '_PE'), how='inner')
        
        if df.empty:
            st.error("❌ No matching strikes found between CE and PE")
            return pd.DataFrame()
        
        df = df.sort_values('strikePrice')
        return df
        
    except Exception as e:
        error_msg = f"Error processing option data: {str(e)}"
        st.error(f"❌ {error_msg}")
        
        # Send detailed error for debugging
        try:
            from telegram_notifications import send_telegram_message
            send_telegram_message(f"❌ Data Processing Error:\n{traceback.format_exc()}")
        except:
            pass
            
        return pd.DataFrame()

def calculate_greeks(option_type, S, K, T, r, sigma):
    """Calculate option Greeks with error handling"""
    try:
        if sigma <= 0 or T <= 0 or S <= 0 or K <= 0:
            return 0, 0, 0, 0, 0
            
        d1 = (math.log(S / K) + (r + 0.5 * sigma**2) * T) / (sigma * math.sqrt(T))
        d2 = d1 - sigma * math.sqrt(T)
        
        delta = norm.cdf(d1) if option_type == 'CE' else -norm.cdf(-d1)
        gamma = norm.pdf(d1) / (S * sigma * math.sqrt(T))
        vega = S * norm.pdf(d1) * math.sqrt(T) / 100
        
        if option_type == 'CE':
            theta = (- (S * norm.pdf(d1) * sigma) / (2 * math.sqrt(T)) - r * K * math.exp(-r * T) * norm.cdf(d2)) / 365
            rho = (K * T * math.exp(-r * T) * norm.cdf(d2)) / 100
        else:
            theta = (- (S * norm.pdf(d1) * sigma) / (2 * math.sqrt(T)) + r * K * math.exp(-r * T) * norm.cdf(-d2)) / 365
            rho = (-K * T * math.exp(-r * T) * norm.cdf(-d2)) / 100
        
        return round(delta, 4), round(gamma, 4), round(vega, 4), round(theta, 4), round(rho, 4)
        
    except (ValueError, ZeroDivisionError, OverflowError) as e:
        # Return neutral Greeks if calculation fails
        return 0, 0, 0, 0, 0

def detect_liquidity_zones(df, spot_price, price_history):
    """Detect liquidity zones based on price action and volume with validation"""
    try:
        if df.empty or not price_history:
            return pd.DataFrame()
            
        zones = []
        unique_strikes = df['strikePrice'].unique()
        
        for strike in unique_strikes:
            if not isinstance(strike, (int, float)) or strike <= 0:
                continue
                
            revisit_count = sum((abs(spot - strike) <= 10) for spot in price_history if isinstance(spot, (int, float)))
            strike_data = df[df['strikePrice'] == strike]
            
            if strike_data.empty:
                continue
            
            # Safely calculate averages with fallback values
            try:
                avg_volume = (
                    strike_data['totalTradedVolume_CE'].fillna(0).mean() + 
                    strike_data['totalTradedVolume_PE'].fillna(0).mean()
                )
                avg_oi_change = (
                    strike_data['changeinOpenInterest_CE'].fillna(0).mean() + 
                    strike_data['changeinOpenInterest_PE'].fillna(0).mean()
                )
            except:
                continue
            
            if revisit_count >= 3 and avg_volume > 5000 and avg_oi_change > 0:
                zones.append({
                    'strike': strike,
                    'revisits': revisit_count,
                    'volume': round(avg_volume),
                    'oi_change': round(avg_oi_change)
                })
                
        return pd.DataFrame(zones)
        
    except Exception as e:
        st.warning(f"⚠️ Error detecting liquidity zones: {str(e)}")
        return pd.DataFrame()

def sudden_liquidity_spike(row):
    """Detect sudden liquidity spikes with validation"""
    try:
        # Validate required fields exist and are numeric
        required_fields = ['changeinOpenInterest_CE', 'openInterest_CE', 'totalTradedVolume_CE',
                          'changeinOpenInterest_PE', 'openInterest_PE', 'totalTradedVolume_PE']
        
        for field in required_fields:
            if field not in row or not isinstance(row[field], (int, float)):
                return False
        
        ce_spike = (row['changeinOpenInterest_CE'] > 1.5 * row['openInterest_CE'] and 
                   row['totalTradedVolume_CE'] > 1500)
        pe_spike = (row['changeinOpenInterest_PE'] > 1.5 * row['openInterest_PE'] and 
                   row['totalTradedVolume_PE'] > 1500)
        
        return ce_spike or pe_spike
        
    except Exception as e:
        return False

def get_market_hours():
    """Get market hours as time objects - cleaner approach"""
    return time(9, 0), time(18, 40)

def is_market_open():
    """Check if market is currently open"""
    now = datetime.now(timezone("Asia/Kolkata"))
    current_day = now.weekday()
    current_time = now.time()
    market_start, market_end = get_market_hours()
    
    # Monday = 0, Sunday = 6
    if current_day >= 5:  # Saturday or Sunday
        return False
        
    return market_start <= current_time <= market_end