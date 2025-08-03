import streamlit as st
from streamlit_autorefresh import st_autorefresh
import pandas as pd
import numpy as np
from datetime import datetime, time
from pytz import timezone
import traceback
import requests
import math
from scipy.stats import norm
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import io

# ===================================================================
# STREAMLIT CLOUD COMPATIBLE VERSION
# All modules are included in this single file to avoid import issues
# ===================================================================

def initialize_streamlit_config():
    """Initialize Streamlit configuration and session states"""
    st.set_page_config(
        page_title="Nifty Options Analyzer Pro", 
        layout="wide",
        initial_sidebar_state="expanded",
        page_icon="📈"
    )

    # Initialize session states
    session_defaults = {
        'price_data': pd.DataFrame(columns=["Time", "Spot"]),
        'trade_log': [],
        'call_log_book': [],
        'export_data': False,
        'support_zone': (None, None),
        'resistance_zone': (None, None),
        'refresh_interval': 120000,  # Default 2 minutes
        'last_analysis_log': None,
        'last_daily_summary': None,
        'api_call_count': 0,
        'last_update_time': None,
        'data_quality_score': 100,
        'current_page': 'Analysis',
        'news_data': [],
        'sentiment_history': [],
        'current_sentiment_score': 0,
        'bot_active': False,
        'pending_trades': {},
        'confirmed_trades': [],
        'manual_trades': [],
        'simulated_trades': []
    }
    
    for key, default_value in session_defaults.items():
        if key not in st.session_state:
            st.session_state[key] = default_value

# ===================================================================
# TELEGRAM NOTIFICATIONS MODULE
# ===================================================================

def get_telegram_credentials():
    """Get Telegram credentials from Streamlit secrets"""
    try:
        bot_token = st.secrets["telegram"]["bot_token"]
        chat_id = st.secrets["telegram"]["chat_id"]
        return bot_token, chat_id
    except KeyError as e:
        st.error(f"❌ Telegram credentials not found: {e}")
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
        return response.status_code == 200
    except Exception as e:
        st.warning(f"⚠️ Telegram error: {e}")
        return False

# ===================================================================
# DATA PROCESSING MODULE
# ===================================================================

@st.cache_data(ttl=60)
def fetch_option_chain_data():
    """Fetch option chain data from NSE"""
    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        session = requests.Session()
        session.headers.update(headers)
        
        # Initialize NSE session
        session.get("https://www.nseindia.com", timeout=5)
        
        # Fetch option chain data
        url = "https://www.nseindia.com/api/option-chain-indices?symbol=NIFTY"
        response = session.get(url, timeout=10)
        data = response.json()
        
        # Validate data
        if not data or 'records' not in data or 'data' not in data['records']:
            st.error("❌ Invalid data received from NSE")
            return None, None, None
        
        # Get previous close data
        try:
            prev_close_url = "https://www.nseindia.com/api/equity-stockIndices?index=NIFTY%2050"
            prev_close_response = session.get(prev_close_url, timeout=10)
            prev_close_data = prev_close_response.json()
            prev_close = prev_close_data['data'][0]['previousClose']
        except:
            prev_close = 0
            st.warning("⚠️ Could not fetch previous close data")
        
        return data, prev_close, session
        
    except Exception as e:
        st.error(f"❌ Error fetching data: {e}")
        send_telegram_message(f"❌ Data fetch error: {str(e)}")
        return None, None, None

def is_market_open():
    """Check if market is currently open"""
    now = datetime.now(timezone("Asia/Kolkata"))
    current_day = now.weekday()
    current_time = now.time()
    market_start = time(9, 0)
    market_end = time(18, 40)
    
    return current_day < 5 and market_start <= current_time <= market_end

def calculate_greeks(option_type, S, K, T, r, sigma):
    """Calculate option Greeks"""
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
        
    except Exception:
        return 0, 0, 0, 0, 0

# ===================================================================
# ANALYSIS FUNCTIONS MODULE
# ===================================================================

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

def determine_level(row):
    """Determine if strike is support or resistance"""
    if row['openInterest_PE'] > 1.12 * row['openInterest_CE']:
        return "Support"
    elif row['openInterest_CE'] > 1.12 * row['openInterest_PE']:
        return "Resistance"
    else:
        return "Neutral"

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

# ===================================================================
# UI COMPONENTS MODULE
# ===================================================================

def display_enhanced_trade_log():
    """Display enhanced trade log"""
    if not st.session_state.trade_log:
        st.info("📝 No trades logged yet")
        return
        
    st.markdown("### 📜 Trade Log")
    df_trades = pd.DataFrame(st.session_state.trade_log)
    
    # Add simulated P&L
    if 'Current_Price' not in df_trades.columns:
        df_trades['Current_Price'] = df_trades['LTP'] * np.random.uniform(0.8, 1.3, len(df_trades))
        df_trades['Unrealized_PL'] = (df_trades['Current_Price'] - df_trades['LTP']) * 75
        df_trades['Status'] = df_trades['Unrealized_PL'].apply(
            lambda x: '🟢 Profit' if x > 0 else '🔴 Loss' if x < -100 else '🟡 Breakeven'
        )
    
    st.dataframe(df_trades, use_container_width=True)
    
    # Summary metrics
    col1, col2, col3 = st.columns(3)
    total_pl = df_trades['Unrealized_PL'].sum()
    win_rate = len(df_trades[df_trades['Unrealized_PL'] > 0]) / len(df_trades) * 100
    
    with col1:
        st.metric("💰 Total P&L", f"₹{total_pl:,.0f}")
    with col2:
        st.metric("🎯 Win Rate", f"{win_rate:.1f}%")
    with col3:
        st.metric("📊 Total Trades", len(df_trades))

def plot_price_with_sr():
    """Plot price chart with support and resistance"""
    price_df = st.session_state['price_data'].copy()
    
    if price_df.empty or price_df['Spot'].isnull().all():
        st.info("📈 Price chart will appear once data accumulates...")
        return
    
    support_zone = st.session_state.get('support_zone', (None, None))
    resistance_zone = st.session_state.get('resistance_zone', (None, None))
    
    fig = go.Figure()
    
    # Add price line
    fig.add_trace(go.Scatter(
        x=price_df.index, 
        y=price_df['Spot'], 
        mode='lines+markers', 
        name='Spot Price',
        line=dict(color='blue', width=2)
    ))
    
    # Add support/resistance zones
    if all(support_zone):
        fig.add_hline(y=support_zone[0], line_dash="dash", line_color="green", annotation_text="Support")
        fig.add_hline(y=support_zone[1], line_dash="dash", line_color="green")
    
    if all(resistance_zone):
        fig.add_hline(y=resistance_zone[0], line_dash="dash", line_color="red", annotation_text="Resistance")
        fig.add_hline(y=resistance_zone[1], line_dash="dash", line_color="red")
    
    fig.update_layout(
        title="Nifty Spot Price with Support & Resistance",
        xaxis_title="Time",
        yaxis_title="Price",
        template="plotly_white",
        height=400
    )
    
    st.plotly_chart(fig, use_container_width=True)

# ===================================================================
# MAIN APPLICATION LOGIC
# ===================================================================

def render_navigation():
    """Render main navigation"""
    st.sidebar.markdown("# 📈 Nifty Options Pro")
    st.sidebar.markdown("**Version**: 3.0.0 | **Streamlit Cloud**")
    st.sidebar.markdown("---")
    
    pages = {
        "📊 Live Analysis": "Analysis",
        "🚀 Trade Simulator": "Simulator", 
        "🤖 Telegram Bot": "Bot",
        "📰 Market Sentiment": "Sentiment"
    }
    
    selected_page = st.sidebar.radio(
        "🧭 Navigation",
        list(pages.keys()),
        index=list(pages.values()).index(st.session_state.current_page)
    )
    
    st.session_state.current_page = pages[selected_page]
    return st.session_state.current_page

def setup_sidebar_controls():
    """Setup sidebar controls"""
    with st.sidebar:
        st.markdown("---")
        st.header("⚙️ Settings")
        
        refresh_interval = st.number_input(
            "Refresh interval (seconds)", 
            min_value=30, 
            value=int(st.session_state.refresh_interval/1000), 
            step=30
        )
        
        if st.button("Apply Refresh Settings"):
            st.session_state.refresh_interval = refresh_interval * 1000
            st.success(f"✅ Refresh set to {refresh_interval} seconds")

    # Apply auto-refresh only on Analysis page
    if st.session_state.current_page == "Analysis":
        st_autorefresh(
            interval=st.session_state.refresh_interval, 
            key="data_refresh", 
            limit=100
        )

def process_basic_analysis(data, underlying):
    """Process basic option chain analysis"""
    try:
        records = data['records']['data']
        calls, puts = [], []

        for item in records:
            if 'CE' in item:
                calls.append(item['CE'])
            if 'PE' in item:
                puts.append(item['PE'])

        if not calls or not puts:
            return None, None, None, "No Data"

        df_ce = pd.DataFrame(calls)
        df_pe = pd.DataFrame(puts)
        df = pd.merge(df_ce, df_pe, on='strikePrice', suffixes=('_CE', '_PE')).sort_values('strikePrice')

        # Get ATM strike
        atm_strike = min(df['strikePrice'], key=lambda x: abs(x - underlying))
        df_filtered = df[df['strikePrice'].between(atm_strike - 200, atm_strike + 200)]

        # Simple bias calculation
        total_score = 0
        bias_results = []
        
        for _, row in df_filtered.iterrows():
            if abs(row['strikePrice'] - atm_strike) > 100:
                continue
                
            # Simple bias scoring
            score = 0
            if row['changeinOpenInterest_CE'] < row['changeinOpenInterest_PE']:
                score += 1
            if row['totalTradedVolume_CE'] < row['totalTradedVolume_PE']:
                score += 1
            if row['askQty_PE'] > row['askQty_CE']:
                score += 1
            
            zone = 'ATM' if row['strikePrice'] == atm_strike else 'OTM' if row['strikePrice'] > underlying else 'ITM'
            
            bias_results.append({
                "Strike": row['strikePrice'],
                "Zone": zone,
                "Level": determine_level(row),
                "BiasScore": score,
                "Verdict": "Bullish" if score >= 2 else "Bearish" if score <= 0 else "Neutral"
            })
            
            total_score += score

        market_view = final_verdict(total_score)
        df_summary = pd.DataFrame(bias_results)
        
        return df_filtered, df_summary, total_score, market_view

    except Exception as e:
        st.error(f"Analysis error: {e}")
        return None, None, None, "Error"

def render_analysis_page():
    """Render the main analysis page"""
    if not is_market_open():
        st.warning("📴 Market is closed. Take rest and recharge! 🎯")
        st.info("Market hours: 9:00 AM - 6:40 PM IST, Monday-Friday")
        return

    try:
        st.session_state.api_call_count += 1
        
        data, prev_close, session = fetch_option_chain_data()
        if not data:
            st.error("❌ Unable to fetch option chain data")
            return

        st.session_state.last_update_time = datetime.now(timezone("Asia/Kolkata")).strftime("%H:%M:%S")
        
        underlying = data['records']['underlyingValue']
        
        # Process analysis
        df, df_summary, total_score, market_view = process_basic_analysis(data, underlying)
        
        if df is None:
            st.error("❌ Unable to process data")
            return
            
        # Get support/resistance zones
        support_zone, resistance_zone = get_support_resistance_zones(df, underlying)
        st.session_state.support_zone = support_zone
        st.session_state.resistance_zone = resistance_zone
        
        # Display header
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("🎯 Spot", f"{underlying:.2f}")
        with col2:
            st.metric("🧠 View", market_view)
        with col3:
            st.metric("⚖️ Score", f"{total_score:+.0f}")
        with col4:
            st.metric("🕐 Update", st.session_state.last_update_time)
        
        st.markdown("---")
        
        # Support/Resistance
        col1, col2 = st.columns(2)
        with col1:
            support_str = f"{support_zone[1]} to {support_zone[0]}" if all(support_zone) else "N/A"
            st.success(f"🛡️ **Support**: `{support_str}`")
        with col2:
            resistance_str = f"{resistance_zone[0]} to {resistance_zone[1]}" if all(resistance_zone) else "N/A"
            st.error(f"🚧 **Resistance**: `{resistance_str}`")
        
        # Store price data
        current_time_str = datetime.now(timezone("Asia/Kolkata")).strftime("%H:%M:%S")
        new_row = pd.DataFrame([[current_time_str, underlying]], columns=["Time", "Spot"])
        st.session_state['price_data'] = pd.concat([st.session_state['price_data'], new_row], ignore_index=True)
        
        # Display chart
        plot_price_with_sr()
        
        # Display summary
        with st.expander("📊 Analysis Summary"):
            if not df_summary.empty:
                st.dataframe(df_summary, use_container_width=True)
        
        # Display trade log
        display_enhanced_trade_log()

    except Exception as e:
        st.error(f"❌ Analysis error: {e}")
        send_telegram_message(f"❌ Analysis error: {str(e)}")

def render_simulator_page():
    """Render basic simulator page"""
    st.markdown("## 🚀 Trade Simulator")
    st.info("📝 Basic simulator - Full version requires separate modules")
    
    col1, col2 = st.columns(2)
    
    with col1:
        option_type = st.selectbox("Type", ["CE", "PE"])
        strike = st.number_input("Strike", value=24000, step=50)
        entry_price = st.number_input("Entry Price", value=100.0, step=0.5)
    
    with col2:
        target = st.number_input("Target", value=150.0, step=0.5)
        stop_loss = st.number_input("Stop Loss", value=70.0, step=0.5)
        quantity = st.number_input("Quantity", value=75, step=25)
    
    if st.button("🎯 Add to Simulation"):
        trade = {
            "Type": option_type,
            "Strike": strike,
            "Entry": entry_price,
            "Target": target,
            "SL": stop_loss,
            "Qty": quantity,
            "Time": datetime.now().strftime("%H:%M:%S")
        }
        st.session_state.simulated_trades.append(trade)
        st.success("✅ Trade added to simulation!")
    
    if st.session_state.simulated_trades:
        st.markdown("### 📊 Simulated Trades")
        st.dataframe(pd.DataFrame(st.session_state.simulated_trades))

def render_bot_page():
    """Render basic bot page"""
    st.markdown("## 🤖 Telegram Bot")
    st.info("📱 Basic bot controls - Full interactive features require separate modules")
    
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("🚀 Test Connection", use_container_width=True):
            success = send_telegram_message("🧪 Test message from Nifty Analyzer")
            if success:
                st.success("✅ Telegram connected!")
            else:
                st.error("❌ Connection failed!")
    
    with col2:
        bot_status = "🟢 Active" if st.session_state.bot_active else "🔴 Inactive"
        st.metric("Bot Status", bot_status)
    
    # Manual message sender
    custom_message = st.text_input("Send Custom Message:")
    if st.button("📤 Send Message") and custom_message:
        success = send_telegram_message(custom_message)
        if success:
            st.success("Message sent!")
        else:
            st.error("Failed to send!")

def render_sentiment_page():
    """Render basic sentiment page"""
    st.markdown("## 📰 Market Sentiment")
    st.info("📊 Basic sentiment display - Full analysis requires separate modules")
    
    # Sample sentiment data
    sample_news = [
        {"title": "Nifty hits fresh highs on strong FII flows", "sentiment": 0.8, "source": "Market News"},
        {"title": "RBI maintains repo rate in policy review", "sentiment": 0.1, "source": "Economic Times"},
        {"title": "Banking stocks surge on earnings optimism", "sentiment": 0.6, "source": "MoneyControl"},
        {"title": "IT sector faces headwinds from US concerns", "sentiment": -0.3, "source": "Financial Express"}
    ]
    
    avg_sentiment = sum(item["sentiment"] for item in sample_news) / len(sample_news)
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("📊 Sentiment Score", f"{avg_sentiment:+.2f}")
    with col2:
        positive_news = len([n for n in sample_news if n["sentiment"] > 0.1])
        st.metric("🟢 Positive News", positive_news)
    with col3:
        negative_news = len([n for n in sample_news if n["sentiment"] < -0.1])
        st.metric("🔴 Negative News", negative_news)
    
    st.markdown("### 📰 Sample Headlines")
    for news in sample_news:
        sentiment_color = "🟢" if news["sentiment"] > 0.1 else "🔴" if news["sentiment"] < -0.1 else "🟡"
        st.write(f"{sentiment_color} **{news['title']}** ({news['sentiment']:+.1f}) - *{news['source']}*")

def main():
    """Main application entry point"""
    try:
        initialize_streamlit_config()
        
        # Navigation
        current_page = render_navigation()
        
        # Sidebar
        setup_sidebar_controls()
        
        # System status
        with st.sidebar:
            st.markdown("---")
            st.header("🔧 Status")
            if is_market_open():
                st.success("🟢 Market: Open")
            else:
                st.info("🔴 Market: Closed")
            
            st.metric("API Calls", st.session_state.api_call_count)
            
            if st.session_state.last_update_time:
                st.caption(f"Last update: {st.session_state.last_update_time}")
        
        # Render pages
        if current_page == "Analysis":
            st.title("📊 Live Options Analysis")
            render_analysis_page()
        elif current_page == "Simulator":
            st.title("🚀 Trade Simulator")
            render_simulator_page()
        elif current_page == "Bot":
            st.title("🤖 Telegram Bot")
            render_bot_page()
        elif current_page == "Sentiment":
            st.title("📰 Market Sentiment")
            render_sentiment_page()
        
    except Exception as e:
        st.error("❌ Application error occurred")
        with st.expander("🔍 Error Details"):
            st.code(traceback.format_exc())

if __name__ == "__main__":
    main()