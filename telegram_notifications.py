import requests
import streamlit as st

def get_telegram_credentials():
    """Get Telegram credentials from Streamlit secrets"""
    try:
        bot_token = st.secrets["telegram"]["bot_token"]
        chat_id = st.secrets["telegram"]["chat_id"]
        return bot_token, chat_id
    except KeyError as e:
        st.error(f"❌ Telegram credentials not found in secrets: {e}")
        return None, None
    except Exception as e:
        st.error(f"❌ Error accessing Telegram secrets: {e}")
        return None, None

def send_telegram_message(message):
    """Send message to Telegram"""
    bot_token, chat_id = get_telegram_credentials()
    
    if not bot_token or not chat_id:
        st.warning("⚠️ Telegram credentials not configured")
        return False
        
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    data = {"chat_id": chat_id, "text": message}
    
    try:
        response = requests.post(url, data=data, timeout=10)
        if response.status_code == 200:
            return True
        else:
            st.warning(f"⚠️ Telegram message failed. Status: {response.status_code}")
            return False
    except requests.exceptions.Timeout:
        st.warning("⚠️ Telegram message timeout")
        return False
    except requests.exceptions.ConnectionError:
        st.warning("⚠️ Telegram connection error")
        return False
    except Exception as e:
        st.error(f"❌ Telegram error: {e}")
        return False

def send_liquidity_spike_alert(row):
    """Send liquidity spike alert"""
    message = (
        f"⚡ Sudden Liquidity Spike!\n"
        f"Strike: {row['strikePrice']}\n"
        f"CE OI Chg: {row['changeinOpenInterest_CE']} | PE OI Chg: {row['changeinOpenInterest_PE']}\n"
        f"Vol CE: {row['totalTradedVolume_CE']} | PE: {row['totalTradedVolume_PE']}"
    )
    return send_telegram_message(message)

def send_trade_signal(atm_signal, suggested_trade, total_score, market_view, 
                     row, support_str, resistance_str, underlying, now):
    """Send trade signal alert"""
    message = (
        f"📍 Spot: {underlying}\n"
        f"🔹 {atm_signal}\n"
        f"{suggested_trade}\n"
        f"Bias Score (ATM ±2): {total_score} ({market_view})\n"
        f"Level: {row['Level']}\n"
        f"📉 Support Zone: {support_str}\n"
        f"📈 Resistance Zone: {resistance_str}\n"
        f"Biases:\n"
        f"Strike: {row['Strike']}\n"
        f"ChgOI: {row['ChgOI_Bias']}, Volume: {row['Volume_Bias']}, Gamma: {row['Gamma_Bias']},\n"
        f"AskQty: {row['AskQty_Bias']}, BidQty: {row['BidQty_Bias']}, IV: {row['IV_Bias']}, DVP: {row['DVP_Bias']}"
    )
    return send_telegram_message(message)

def send_reversal_alert(atm_reversal_data, atm_strike, underlying, now):
    """Send reversal alert"""
    direction = atm_reversal_data['ReversalDirection']
    emoji = "⬆️" if direction == "UP" else "⬇️"
    
    message = (
        f"🔄 ATM REVERSAL ALERT {emoji}\n"
        f"Strike: {atm_strike} (ATM)\n"
        f"Direction: {direction}\n"
        f"Strength: {atm_reversal_data['ReversalScore']}/3\n"
        f"CE ΔOI: {atm_reversal_data['changeinOpenInterest_CE']} (IV {atm_reversal_data['impliedVolatility_CE']}%)\n"
        f"PE ΔOI: {atm_reversal_data['changeinOpenInterest_PE']} (IV {atm_reversal_data['impliedVolatility_PE']}%)\n"
        f"Spot: {underlying}\n"
        f"Time: {now.strftime('%H:%M:%S')}"
    )
    return send_telegram_message(message)

def send_expiry_day_signal(signal, underlying):
    """Send expiry day signal alert"""
    message = (
        f"📅 EXPIRY DAY SIGNAL\n"
        f"Type: {signal['type']}\n"
        f"Strike: {signal['strike']}\n"
        f"Score: {signal['score']:.1f}\n"
        f"LTP: ₹{signal['ltp']}\n"
        f"Target: ₹{signal['target']}\n"
        f"Reason: {signal['reason']}\n"
        f"Spot: {underlying}"
    )
    return send_telegram_message(message)

def send_error_alert(error_message):
    """Send error alert to Telegram"""
    message = f"❌ Nifty Analyzer Error:\n{error_message}"
    return send_telegram_message(message)

def send_startup_message():
    """Send startup notification"""
    from datetime import datetime
    from pytz import timezone
    
    now = datetime.now(timezone("Asia/Kolkata"))
    message = (
        f"🚀 Nifty Options Analyzer Started\n"
        f"Time: {now.strftime('%Y-%m-%d %H:%M:%S')}\n"
        f"Status: Ready for analysis"
    )
    return send_telegram_message(message)

def test_telegram_connection():
    """Test Telegram connection and credentials"""
    test_message = "🧪 Test message from Nifty Options Analyzer"
    success = send_telegram_message(test_message)
    
    if success:
        st.success("✅ Telegram connection successful!")
    else:
        st.error("❌ Telegram connection failed!")
    
    return success

# Optional: Add this to your sidebar for testing
def add_telegram_test_ui():
    """Add Telegram test UI to sidebar"""
    with st.sidebar:
        st.markdown("---")
        st.subheader("🔧 Telegram Test")
        
        if st.button("Test Telegram Connection"):
            test_telegram_connection()
        
        # Custom message sender for testing
        custom_message = st.text_input("Send Custom Message:")
        if st.button("Send Custom Message") and custom_message:
            success = send_telegram_message(custom_message)
            if success:
                st.success("Message sent!")
            else:
                st.error("Failed to send message!")