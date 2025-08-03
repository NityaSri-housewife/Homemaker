import streamlit as st
from streamlit_autorefresh import st_autorefresh
import pandas as pd
from datetime import datetime
from pytz import timezone
import traceback
import sys
import os

# Add current directory to Python path to find local modules
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

# Now import local modules (these should work if files are in same directory)
try:
    from data_processing import fetch_option_chain_data, is_market_open
    from expiry_analysis import is_expiry_day, handle_expiry_day_analysis, display_expiry_signals, display_expiry_option_chain
    from regular_analysis import handle_regular_trading_analysis, handle_reversal_analysis, handle_liquidity_zones
    from ui_components import display_enhanced_trade_log, handle_export_data, display_call_log_book, auto_update_call_log
    from telegram_notifications import send_telegram_message
    from google_sheets_integration import (
        log_analysis_data, log_trade_data, generate_daily_summary, 
        should_log_analysis, should_generate_daily_summary, test_google_sheets_connection
    )
    
    # Import new feature modules
    from trade_simulator import render_trade_simulator
    from telegram_interactive_bot import render_telegram_interactive_bot, send_trade_for_confirmation
    from sentiment_analysis import render_sentiment_analysis, get_current_sentiment_score
    
    IMPORTS_SUCCESS = True
    
except ImportError as e:
    st.error(f"❌ Import Error: {str(e)}")
    st.error("🔍 Please ensure all required files are in the same directory as main_app.py")
    st.info("""
    **Required files in same directory:**
    - data_processing.py
    - analysis_functions.py  
    - expiry_analysis.py
    - regular_analysis.py
    - ui_components.py
    - telegram_notifications.py
    - google_sheets_integration.py
    - trade_simulator.py
    - telegram_interactive_bot.py
    - sentiment_analysis.py
    """)
    IMPORTS_SUCCESS = False

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
        'current_page': 'Analysis'  # New: page navigation
    }
    
    for key, default_value in session_defaults.items():
        if key not in st.session_state:
            st.session_state[key] = default_value

def render_navigation():
    """Render main navigation"""
    st.sidebar.markdown("# 📈 Nifty Options Pro")
    st.sidebar.markdown("**Version**: 3.0.0 | **Updated**: Aug 2025")
    st.sidebar.markdown("---")
    
    # Main navigation
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

def render_sticky_header_with_sentiment(underlying=None, market_view=None, total_score=None):
    """Enhanced sticky header with sentiment integration"""
    if underlying and market_view and total_score is not None:
        # Get current sentiment score
        sentiment_score = get_current_sentiment_score()
        
        # Create enhanced header
        col1, col2, col3, col4, col5 = st.columns(5)
        
        with col1:
            st.metric("🎯 Nifty Spot", f"{underlying:.2f}")
        
        with col2:
            # Color-code market view
            if "Bullish" in market_view:
                st.metric("🧠 Market View", market_view, delta="Bullish", delta_color="normal")
            elif "Bearish" in market_view:
                st.metric("🧠 Market View", market_view, delta="Bearish", delta_color="inverse")
            else:
                st.metric("🧠 Market View", market_view)
        
        with col3:
            # Color-code bias score
            delta_color = "normal" if total_score > 0 else "inverse" if total_score < 0 else "off"
            st.metric("⚖️ Bias Score", f"{total_score:+.1f}", delta=f"{abs(total_score):.1f}", delta_color=delta_color)
        
        with col4:
            # Add sentiment score
            if sentiment_score > 0.3:
                st.metric("📰 Sentiment", f"{sentiment_score:+.2f}", delta="Positive", delta_color="normal")
            elif sentiment_score < -0.3:
                st.metric("📰 Sentiment", f"{sentiment_score:+.2f}", delta="Negative", delta_color="inverse")
            else:
                st.metric("📰 Sentiment", f"{sentiment_score:+.2f}", delta="Neutral", delta_color="off")
        
        with col5:
            now = datetime.now(timezone("Asia/Kolkata"))
            st.metric("🕐 Last Update", now.strftime("%H:%M:%S"))
        
        st.markdown("---")

def setup_sidebar_controls():
    """Setup comprehensive sidebar controls"""
    with st.sidebar:
        st.markdown("---")
        st.header("⚙️ Settings")
        
        # Refresh Settings
        refresh_interval = st.number_input(
            "Refresh interval (seconds)", 
            min_value=30, 
            value=int(st.session_state.refresh_interval/1000), 
            step=30,
            help="How often to refresh data (minimum 30 seconds)"
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

def setup_system_status_sidebar():
    """Setup system status monitoring in sidebar"""
    with st.sidebar:
        st.markdown("---")
        st.header("🔧 System Status")
        
        # Market Status
        if IMPORTS_SUCCESS and is_market_open():
            st.success("🟢 Market: Open")
        else:
            st.info("🔴 Market: Closed")
        
        # Performance Metrics
        col1, col2 = st.columns(2)
        with col1:
            st.metric("API Calls", st.session_state.get('api_call_count', 0))
        with col2:
            st.metric("Data Quality", f"{st.session_state.get('data_quality_score', 100)}%")
        
        # Feature Status
        st.markdown("**📱 Features:**")
        
        # Import Status
        if IMPORTS_SUCCESS:
            st.caption("🟢 All modules loaded")
        else:
            st.caption("🔴 Module import errors")
        
        # Telegram Bot Status
        bot_active = st.session_state.get('bot_active', False)
        bot_status = "🟢 Active" if bot_active else "🔴 Inactive"
        st.caption(f"Telegram Bot: {bot_status}")
        
        # Sentiment Analysis Status
        has_sentiment_data = bool(st.session_state.get('news_data', []))
        sentiment_status = "🟢 Updated" if has_sentiment_data else "🟡 No Data"
        st.caption(f"Sentiment: {sentiment_status}")
        
        # Last Update
        if st.session_state.last_update_time:
            st.caption(f"Last update: {st.session_state.last_update_time}")

def setup_google_sheets_controls():
    """Setup Google Sheets controls in sidebar"""
    if not IMPORTS_SUCCESS:
        return
        
    with st.sidebar:
        st.markdown("---")
        st.header("📊 Google Sheets")
        
        # Show logging status with better indicators
        if should_log_analysis():
            st.success("🟢 Analysis: Logging active")
        else:
            next_log = "Next log in ~15 min"
            st.info(f"🔵 Analysis: {next_log}")
        
        if should_generate_daily_summary():
            st.success("🟢 Summary: Ready")
        else:
            st.info("🔵 Summary: At market close")
        
        # Manual controls in columns for better UX
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button("📝 Log", help="Force log current analysis"):
                handle_manual_log()
        
        with col2:
            if st.button("📋 Summary", help="Generate daily summary"):
                handle_manual_summary()
        
        # Test connection
        if st.button("🧪 Test Sheets", help="Test Google Sheets connection"):
            test_google_sheets_connection()

def handle_manual_log():
    """Handle manual logging trigger"""
    if 'last_analysis_data' in st.session_state:
        data = st.session_state.last_analysis_data
        success = log_analysis_data(
            data['df_summary'], data['underlying'], data['market_view'],
            data['total_score'], data['support_zone'], data['resistance_zone'],
            data.get('signal_generated', 'Manual')
        )
        if success:
            st.success("✅ Logged to sheets!")
        else:
            st.error("❌ Logging failed!")
    else:
        st.warning("⚠️ No data to log yet")

def handle_manual_summary():
    """Handle manual summary generation"""
    success = generate_daily_summary()
    if success:
        st.success("✅ Summary generated!")
        st.session_state.last_daily_summary = datetime.now(timezone("Asia/Kolkata")).isoformat()
    else:
        st.error("❌ Summary generation failed!")

def render_analysis_page():
    """Render the main analysis page"""
    if not IMPORTS_SUCCESS:
        st.error("❌ Cannot run analysis - missing required modules")
        st.info("Please ensure all Python files are in the same directory")
        return
        
    if not is_market_open():
        st.warning("📴 Market is closed. Take rest and recharge! 🎯")
        st.info("Market hours: 9:00 AM - 6:40 PM IST, Monday-Friday")
        
        # Show other features even when market is closed
        st.markdown("### 🎯 Available Features During Market Closure:")
        col1, col2, col3 = st.columns(3)
        
        with col1:
            if st.button("🚀 Trade Simulator", use_container_width=True):
                st.session_state.current_page = "Simulator"
                st.experimental_rerun()
        
        with col2:
            if st.button("🤖 Telegram Bot", use_container_width=True):
                st.session_state.current_page = "Bot"
                st.experimental_rerun()
        
        with col3:
            if st.button("📰 Market Sentiment", use_container_width=True):
                st.session_state.current_page = "Sentiment"
                st.experimental_rerun()
        
        return

    try:
        # Update API call counter
        st.session_state.api_call_count += 1
        
        # Fetch data with resilience
        data, prev_close, session = fetch_option_chain_data()
        if not data:
            st.error("❌ Unable to fetch option chain data. Please try again.")
            st.session_state.data_quality_score = max(0, st.session_state.data_quality_score - 10)
            return

        # Update data quality score
        st.session_state.data_quality_score = min(100, st.session_state.data_quality_score + 1)
        st.session_state.last_update_time = datetime.now(timezone("Asia/Kolkata")).strftime("%H:%M:%S")

        # Extract and validate basic info
        records = data['records']['data']
        expiry = data['records']['expiryDates'][0]
        underlying = data['records']['underlyingValue']
        
        # Time calculations
        now = datetime.now(timezone("Asia/Kolkata"))
        expiry_date = timezone("Asia/Kolkata").localize(datetime.strptime(expiry, "%d-%b-%Y"))
        T = max((expiry_date - now).days, 1) / 365
        r = 0.06

        signal_generated = "No"

        # Handle expiry day vs regular day
        if is_expiry_day(now, expiry_date):
            signal_generated = handle_expiry_day_logic(data, expiry, underlying, prev_close, now)
        else:
            signal_generated = handle_regular_day_logic(data, expiry, underlying, T, r, now)

    except Exception as e:
        error_msg = f"❌ Critical Error in Analysis: {str(e)}"
        st.error(error_msg)
        
        # Send detailed traceback to Telegram for debugging
        try:
            detailed_error = f"❌ Main Analysis Error:\n{traceback.format_exc()}"
            send_telegram_message(detailed_error)
        except:
            pass  # Don't let Telegram errors break the flow

def handle_expiry_day_logic(data, expiry, underlying, prev_close, now):
    """Handle expiry day analysis logic"""
    df, expiry_signals = handle_expiry_day_analysis(data, expiry, underlying, prev_close, now)
    
    # Display results with sentiment
    render_sticky_header_with_sentiment(underlying, "Expiry Day", 0)
    display_expiry_signals(expiry_signals, underlying, now)
    display_expiry_option_chain(df)
    
    return "Expiry Day Analysis Complete"

def handle_regular_day_logic(data, expiry, underlying, T, r, now):
    """Handle regular trading day analysis logic"""
    # Main analysis
    df, bias_results, total_score, market_view, suggested_trade, signal_sent = handle_regular_trading_analysis(
        data, expiry, underlying, T, r, now
    )
    
    if df.empty or not bias_results:
        st.error("❌ Unable to process option chain data")
        return "Error"
    
    # Get zones
    support_zone = st.session_state.get('support_zone', (None, None))
    resistance_zone = st.session_state.get('resistance_zone', (None, None))
    
    # Render results with enhanced header
    render_sticky_header_with_sentiment(underlying, market_view, total_score)
    
    # Support/Resistance display
    col1, col2 = st.columns(2)
    
    with col1:
        support_str = f"{support_zone[1]} to {support_zone[0]}" if all(support_zone) else "N/A"
        st.success(f"🛡️ **Support Zone**: `{support_str}`")
    
    with col2:
        resistance_str = f"{resistance_zone[0]} to {resistance_zone[1]}" if all(resistance_zone) else "N/A"
        st.error(f"🚧 **Resistance Zone**: `{resistance_str}`")
    
    # Trade suggestion
    if suggested_trade:
        sentiment_score = get_current_sentiment_score()
        sentiment_context = ""
        
        if sentiment_score > 0.3:
            sentiment_context = "📰 **Sentiment**: Positive market news supports this signal"
        elif sentiment_score < -0.3:
            sentiment_context = "📰 **Sentiment**: Negative news - trade with caution"
        else:
            sentiment_context = "📰 **Sentiment**: Neutral news environment"
        
        st.info(f"🎯 **Trading Signal**\n\n{suggested_trade}\n\n{sentiment_context}")
    
    return "Regular Analysis Complete"

def main():
    """Main application entry point"""
    try:
        # Initialize configuration
        initialize_streamlit_config()
        
        # Check if imports were successful
        if not IMPORTS_SUCCESS:
            st.title("❌ Nifty Options Analyzer - Import Error")
            st.error("The application cannot start due to missing modules.")
            st.info("Please ensure all required Python files are in the same directory as main_app.py")
            return
        
        # Render navigation and get current page
        current_page = render_navigation()
        
        # Setup sidebar controls
        setup_sidebar_controls()
        setup_system_status_sidebar()
        
        # Only show Google Sheets controls on Analysis page
        if current_page == "Analysis":
            setup_google_sheets_controls()
        
        # Render different pages based on navigation
        if current_page == "Analysis":
            st.title("📊 Live Options Analysis")
            render_analysis_page()
            
        elif current_page == "Simulator":
            st.title("🚀 Trade Simulator")
            if IMPORTS_SUCCESS:
                render_trade_simulator()
            else:
                st.error("❌ Trade Simulator unavailable - missing modules")
            
        elif current_page == "Bot":
            st.title("🤖 Telegram Interactive Bot")
            if IMPORTS_SUCCESS:
                render_telegram_interactive_bot()
            else:
                st.error("❌ Telegram Bot unavailable - missing modules")
            
        elif current_page == "Sentiment":
            st.title("📰 Market Sentiment Analysis")
            if IMPORTS_SUCCESS:
                render_sentiment_analysis()
            else:
                st.error("❌ Sentiment Analysis unavailable - missing modules")
        
    except Exception as e:
        st.error("❌ Critical application error occurred")
        
        # Show error details in expander for debugging
        with st.expander("🔍 Error Details", expanded=False):
            st.code(traceback.format_exc())
        
        # Provide recovery options
        st.info("🔄 Try refreshing the page or check your internet connection")

if __name__ == "__main__":
    main()