import streamlit as st
from streamlit_autorefresh import st_autorefresh
import pandas as pd
from datetime import datetime
from pytz import timezone

# Import all function modules
from data_processing import fetch_option_chain_data
from expiry_analysis import is_expiry_day, handle_expiry_day_analysis, display_expiry_signals, display_expiry_option_chain
from regular_analysis import handle_regular_trading_analysis, display_regular_analysis_results, handle_reversal_analysis, handle_liquidity_zones
from ui_components import display_enhanced_trade_log, handle_export_data, display_call_log_book, auto_update_call_log
from telegram_notifications import send_telegram_message

def initialize_streamlit_config():
    """Initialize Streamlit configuration and session states"""
    st.set_page_config(page_title="Nifty Options Analyzer", layout="wide")

    # Initialize session states
    if 'price_data' not in st.session_state:
        st.session_state.price_data = pd.DataFrame(columns=["Time", "Spot"])
    if 'trade_log' not in st.session_state:
        st.session_state.trade_log = []
    if 'call_log_book' not in st.session_state:
        st.session_state.call_log_book = []
    if 'export_data' not in st.session_state:
        st.session_state.export_data = False
    if 'support_zone' not in st.session_state:
        st.session_state.support_zone = (None, None)
    if 'resistance_zone' not in st.session_state:
        st.session_state.resistance_zone = (None, None)
    if 'refresh_interval' not in st.session_state:
        st.session_state.refresh_interval = 120000  # Default 2 minutes

def setup_sidebar_controls():
    """Setup sidebar controls for refresh settings"""
    with st.sidebar:
        st.header("Refresh Settings")
        refresh_interval = st.number_input("Refresh interval (seconds)", 
                                         min_value=30, 
                                         value=int(st.session_state.refresh_interval/1000), 
                                         step=30)
        if st.button("Apply Refresh Settings"):
            st.session_state.refresh_interval = refresh_interval * 1000
            st.success(f"Refresh set to {refresh_interval} seconds")

    # Apply auto-refresh
    st_autorefresh(interval=st.session_state.refresh_interval, 
                  key="data_refresh", 
                  limit=100)

def check_market_hours():
    """Check if market is open"""
    now = datetime.now(timezone("Asia/Kolkata"))
    current_day = now.weekday()
    current_time = now.time()
    market_start = datetime.strptime("09:00", "%H:%M").time()
    market_end = datetime.strptime("18:40", "%H:%M").time()

    if current_day >= 5 or not (market_start <= current_time <= market_end):
        st.warning("📴 Take Rest Bro, Have Fun, Recharge — We Will Play Tomorrow! 🎯 ")
        return False
    return True

def main_analysis():
    """Main analysis function"""
    if not check_market_hours():
        return

    try:
        # Fetch data
        data, prev_close, session = fetch_option_chain_data()
        if not data:
            return

        # Extract basic info
        records = data['records']['data']
        expiry = data['records']['expiryDates'][0]
        underlying = data['records']['underlyingValue']
        
        # Time calculations
        now = datetime.now(timezone("Asia/Kolkata"))
        expiry_date = timezone("Asia/Kolkata").localize(datetime.strptime(expiry, "%d-%b-%Y"))
        T = max((expiry_date - now).days, 1) / 365
        r = 0.06

        # Check if it's expiry day
        if is_expiry_day(now, expiry_date):
            # Handle expiry day analysis
            df, expiry_signals = handle_expiry_day_analysis(data, expiry, underlying, prev_close, now)
            display_expiry_signals(expiry_signals, underlying, now)
            display_expiry_option_chain(df)
            return

        # Handle regular trading day analysis
        df, bias_results, total_score, market_view, suggested_trade, signal_sent = handle_regular_trading_analysis(
            data, expiry, underlying, T, r, now
        )
        
        # Create summary dataframe
        df_summary = pd.DataFrame(bias_results)
        
        # Get ATM strike for further analysis
        atm_strike = min(df['strikePrice'], key=lambda x: abs(x - underlying))
        
        # Display main results
        support_zone = st.session_state.get('support_zone', (None, None))
        resistance_zone = st.session_state.get('resistance_zone', (None, None))
        
        display_regular_analysis_results(
            underlying, market_view, total_score, support_zone, 
            resistance_zone, suggested_trade, df_summary, df, atm_strike
        )
        
        # Handle reversal analysis
        handle_reversal_analysis(df, atm_strike, underlying, now)
        
        # Handle liquidity zones
        handle_liquidity_zones(df, underlying)
        
        # Enhanced features
        display_enhanced_features(df_summary, underlying)

    except Exception as e:
        st.error(f"❌ Error: {e}")
        send_telegram_message(f"❌ Error: {str(e)}")

def display_enhanced_features(df_summary, underlying):
    """Display enhanced features section"""
    st.markdown("---")
    st.markdown("## 📈 Enhanced Features")
    
    # Enhanced Trade Log
    display_enhanced_trade_log()
    
    # Export functionality
    st.markdown("---")
    st.markdown("### 📥 Data Export")
    if st.button("Prepare Excel Export"):
        st.session_state.export_data = True
    handle_export_data(df_summary, underlying)
    
    # Call Log Book
    st.markdown("---")
    display_call_log_book()
    
    # Auto update call log with current price
    auto_update_call_log(underlying)

def main():
    """Main application entry point"""
    # Initialize configuration
    initialize_streamlit_config()
    
    # Setup sidebar controls
    setup_sidebar_controls()
    
    # Run main analysis
    main_analysis()

if __name__ == "__main__":
    main()