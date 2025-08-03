import pandas as pd
import streamlit as st
from datetime import datetime
from pytz import timezone

# Weights for bias calculation
weights = {
    "ChgOI_Bias": 2,
    "Volume_Bias": 1,
    "Gamma_Bias": 1,
    "AskQty_Bias": 1,
    "BidQty_Bias": 1,
    "IV_Bias": 1,
    "DVP_Bias": 1,
}

def final_verdict(score):
    """Convert numerical score to market verdict"""
    if score >= 4:
        return "Strong Bullish"
    elif score >= 2:
        return "Bullish"
    elif score <= -4:
        return "Strong Bearish"
    elif score <= -2:
        return "Bearish"
    else:
        return "Neutral"

def delta_volume_bias(price, volume, chg_oi):
    """Calculate delta volume bias"""
    if price > 0 and volume > 0 and chg_oi > 0:
        return "Bullish"
    elif price < 0 and volume > 0 and chg_oi > 0:
        return "Bearish"
    elif price > 0 and volume > 0 and chg_oi < 0:
        return "Bullish"
    elif price < 0 and volume > 0 and chg_oi < 0:
        return "Bearish"
    else:
        return "Neutral"

def determine_level(row):
    """Determine if strike is support or resistance"""
    if row['openInterest_PE'] > 1.12 * row['openInterest_CE']:
        return "Support"
    elif row['openInterest_CE'] > 1.12 * row['openInterest_PE']:
        return "Resistance"
    else:
        return "Neutral"

def calculate_bias_scores(df, atm_strike, underlying):
    """Calculate bias scores for all strikes"""
    bias_results, total_score = [], 0
    
    for _, row in df.iterrows():
        if abs(row['strikePrice'] - atm_strike) > 100:
            continue

        score = 0
        zone = 'ATM' if row['strikePrice'] == atm_strike else 'ITM' if row['strikePrice'] < underlying else 'OTM'
        
        row_data = {
            "Strike": row['strikePrice'],
            "Zone": zone,
            "Level": determine_level(row),
            "ChgOI_Bias": "Bullish" if row['changeinOpenInterest_CE'] < row['changeinOpenInterest_PE'] else "Bearish",
            "Volume_Bias": "Bullish" if row['totalTradedVolume_CE'] < row['totalTradedVolume_PE'] else "Bearish",
            "Gamma_Bias": "Bullish" if row['Gamma_CE'] < row['Gamma_PE'] else "Bearish",
            "AskQty_Bias": "Bullish" if row['askQty_PE'] > row['askQty_CE'] else "Bearish",
            "BidQty_Bias": "Bearish" if row['bidQty_PE'] > row['bidQty_CE'] else "Bullish",
            "IV_Bias": "Bullish" if row['impliedVolatility_CE'] > row['impliedVolatility_PE'] else "Bearish",
            "DVP_Bias": delta_volume_bias(
                row['lastPrice_CE'] - row['lastPrice_PE'],
                row['totalTradedVolume_CE'] - row['totalTradedVolume_PE'],
                row['changeinOpenInterest_CE'] - row['changeinOpenInterest_PE']
            )
        }

        for k in row_data:
            if "_Bias" in k:
                bias = row_data[k]
                score += weights.get(k, 1) if bias == "Bullish" else -weights.get(k, 1)

        row_data["BiasScore"] = score
        row_data["Verdict"] = final_verdict(score)
        total_score += score
        bias_results.append(row_data)

    return bias_results, total_score

def reversal_score(row):
    """Calculate reversal signals"""
    score = 0
    direction = ""
    
    # Bearish Reversal Signals (Market might go DOWN)
    if (row['changeinOpenInterest_CE'] < 0 and 
        row['changeinOpenInterest_PE'] > 0 and
        row['impliedVolatility_PE'] > row['impliedVolatility_CE']):
        score += 2
        direction = "DOWN"
    
    # Bullish Reversal Signals (Market might go UP)
    elif (row['changeinOpenInterest_CE'] > 0 and 
          row['changeinOpenInterest_PE'] < 0 and
          row['impliedVolatility_CE'] > row['impliedVolatility_PE']):
        score += 2
        direction = "UP"
    
    # Additional confirmation from bid/ask quantities
    if row['bidQty_PE'] > row['bidQty_CE'] and row['askQty_PE'] > row['askQty_CE']:
        score += 1
        if not direction:
            direction = "DOWN"
    elif row['bidQty_CE'] > row['bidQty_PE'] and row['askQty_CE'] > row['askQty_PE']:
        score += 1
        if not direction:
            direction = "UP"
    
    return score, direction

def expiry_bias_score(row):
    """Calculate expiry day bias score"""
    score = 0

    # OI + Price Based Bias Logic
    if row['changeinOpenInterest_CE'] > 0 and row['lastPrice_CE'] > row['previousClose_CE']:
        score += 1  # New CE longs → Bullish
    if row['changeinOpenInterest_PE'] > 0 and row['lastPrice_PE'] > row['previousClose_PE']:
        score -= 1  # New PE longs → Bearish
    if row['changeinOpenInterest_CE'] > 0 and row['lastPrice_CE'] < row['previousClose_CE']:
        score -= 1  # CE writing → Bearish
    if row['changeinOpenInterest_PE'] > 0 and row['lastPrice_PE'] < row['previousClose_PE']:
        score += 1  # PE writing → Bullish

    # Bid Volume Dominance
    if 'bidQty_CE' in row and 'bidQty_PE' in row:
        if row['bidQty_CE'] > row['bidQty_PE'] * 1.5:
            score += 1  # CE Bid dominance → Bullish
        if row['bidQty_PE'] > row['bidQty_CE'] * 1.5:
            score -= 1  # PE Bid dominance → Bearish

    # Volume Churn vs OI
    if row['totalTradedVolume_CE'] > 2 * row['openInterest_CE']:
        score -= 0.5  # CE churn → Possibly noise
    if row['totalTradedVolume_PE'] > 2 * row['openInterest_PE']:
        score += 0.5  # PE churn → Possibly noise

    # Bid-Ask Pressure
    if 'underlyingValue' in row:
        if abs(row['lastPrice_CE'] - row['underlyingValue']) < abs(row['lastPrice_PE'] - row['underlyingValue']):
            score += 0.5  # CE closer to spot → Bullish
        else:
            score -= 0.5  # PE closer to spot → Bearish

    return score

def get_support_resistance_zones(df, spot):
    """Calculate support and resistance zones"""
    df['Level'] = df.apply(determine_level, axis=1)
    support_strikes = df[df['Level'] == "Support"]['strikePrice'].tolist()
    resistance_strikes = df[df['Level'] == "Resistance"]['strikePrice'].tolist()

    nearest_supports = sorted([s for s in support_strikes if s <= spot], reverse=True)[:2]
    nearest_resistances = sorted([r for r in resistance_strikes if r >= spot])[:2]

    support_zone = (min(nearest_supports), max(nearest_supports)) if len(nearest_supports) >= 2 else (nearest_supports[0], nearest_supports[0]) if nearest_supports else (None, None)
    resistance_zone = (min(nearest_resistances), max(nearest_resistances)) if len(nearest_resistances) >= 2 else (nearest_resistances[0], nearest_resistances[0]) if nearest_resistances else (None, None)

    return support_zone, resistance_zone

def is_in_zone(spot, strike, level):
    """Check if spot is in zone"""
    if level == "Support":
        return strike - 20 <= spot <= strike + 20
    elif level == "Resistance":
        return strike - 20 <= spot <= strike + 20
    return False

def expiry_entry_signal(df, support_levels, resistance_levels, score_threshold=1.5):
    """Generate expiry day entry signals"""
    entries = []
    for _, row in df.iterrows():
        strike = row['strikePrice']
        score = expiry_bias_score(row)

        # Entry at support/resistance + Bias Score Condition
        if score >= score_threshold and strike in support_levels:
            support_zone = st.session_state.get('support_zone', (None, None))
            resistance_zone = st.session_state.get('resistance_zone', (None, None))
            
            if resistance_zone[0]:
                target_price = row['lastPrice_CE'] * (1 + (resistance_zone[0] - strike) / strike * 0.5)
            else:
                target_price = row['lastPrice_CE'] * 1.3
                
            entries.append({
                'type': 'BUY CALL',
                'strike': strike,
                'score': score,
                'ltp': row['lastPrice_CE'],
                'target': round(target_price, 2),
                'reason': 'Bullish score + support zone'
            })

        if score <= -score_threshold and strike in resistance_levels:
            support_zone = st.session_state.get('support_zone', (None, None))
            resistance_zone = st.session_state.get('resistance_zone', (None, None))
            
            if support_zone[1]:
                target_price = row['lastPrice_PE'] * (1 + (strike - support_zone[1]) / strike * 0.5)
            else:
                target_price = row['lastPrice_PE'] * 1.3
                
            entries.append({
                'type': 'BUY PUT',
                'strike': strike,
                'score': score,
                'ltp': row['lastPrice_PE'],
                'target': round(target_price, 2),
                'reason': 'Bearish score + resistance zone'
            })

    return entries