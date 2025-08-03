import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime, timedelta
from pytz import timezone
import json
import time

def get_google_credentials():
    """Get Google Sheets credentials from Streamlit secrets"""
    try:
        # Get credentials from Streamlit secrets
        creds_dict = st.secrets["google_sheets"]
        
        # Convert to proper format
        credentials_info = {
            "type": creds_dict["type"],
            "project_id": creds_dict["project_id"],
            "private_key_id": creds_dict["private_key_id"],
            "private_key": creds_dict["private_key"].replace('\\n', '\n'),
            "client_email": creds_dict["client_email"],
            "client_id": creds_dict["client_id"],
            "auth_uri": creds_dict["auth_uri"],
            "token_uri": creds_dict["token_uri"],
            "auth_provider_x509_cert_url": creds_dict["auth_provider_x509_cert_url"],
            "client_x509_cert_url": creds_dict["client_x509_cert_url"]
        }
        
        # Define the scope
        scope = [
            "https://spreadsheets.google.com/feeds",
            "https://www.googleapis.com/auth/drive"
        ]
        
        # Create credentials
        credentials = Credentials.from_service_account_info(credentials_info, scopes=scope)
        return credentials
        
    except KeyError as e:
        st.error(f"❌ Google Sheets credentials not found: {e}")
        return None
    except Exception as e:
        st.error(f"❌ Error accessing Google credentials: {e}")
        return None

def get_google_client():
    """Get authenticated Google Sheets client"""
    try:
        credentials = get_google_credentials()
        if not credentials:
            return None
        
        client = gspread.authorize(credentials)
        return client
    except Exception as e:
        st.error(f"❌ Failed to authenticate with Google Sheets: {e}")
        return None

def get_or_create_spreadsheet(client, spreadsheet_name="Nifty Options Analysis"):
    """Get existing spreadsheet or create new one"""
    try:
        # Try to open existing spreadsheet
        spreadsheet = client.open(spreadsheet_name)
        return spreadsheet
    except gspread.SpreadsheetNotFound:
        # Create new spreadsheet if not found
        try:
            spreadsheet = client.create(spreadsheet_name)
            # Share with your email (optional)
            spreadsheet.share(st.secrets.get("user_email", ""), perm_type='user', role='writer')
            return spreadsheet
        except Exception as e:
            st.error(f"❌ Failed to create spreadsheet: {e}")
            return None
    except Exception as e:
        st.error(f"❌ Error accessing spreadsheet: {e}")
        return None

def create_analysis_log_sheet(spreadsheet):
    """Create or get analysis log worksheet"""
    try:
        # Try to get existing worksheet
        try:
            worksheet = spreadsheet.worksheet("Analysis_Log")
        except gspread.WorksheetNotFound:
            # Create new worksheet
            worksheet = spreadsheet.add_worksheet(title="Analysis_Log", rows="1000", cols="20")
            
            # Add headers
            headers = [
                "Timestamp", "Date", "Time", "Spot_Price", "Market_View", "Bias_Score",
                "Support_Zone_Low", "Support_Zone_High", "Resistance_Zone_Low", "Resistance_Zone_High",
                "ATM_Strike", "ATM_CE_Price", "ATM_PE_Price", "ATM_CE_IV", "ATM_PE_IV",
                "ATM_CE_OI", "ATM_PE_OI", "ATM_CE_Volume", "ATM_PE_Volume", "Signal_Generated"
            ]
            worksheet.append_row(headers)
        
        return worksheet
    except Exception as e:
        st.error(f"❌ Error creating analysis log sheet: {e}")
        return None

def create_trade_log_sheet(spreadsheet):
    """Create or get trade log worksheet"""
    try:
        # Try to get existing worksheet
        try:
            worksheet = spreadsheet.worksheet("Trade_Log")
        except gspread.WorksheetNotFound:
            # Create new worksheet
            worksheet = spreadsheet.add_worksheet(title="Trade_Log", rows="1000", cols="15")
            
            # Add headers
            headers = [
                "Date", "Time", "Timestamp", "Strike", "Type", "Entry_Price", "Target_Price",
                "Stop_Loss", "Signal_Type", "Market_View", "Bias_Score", "Support_Zone",
                "Resistance_Zone", "Status", "Notes"
            ]
            worksheet.append_row(headers)
        
        return worksheet
    except Exception as e:
        st.error(f"❌ Error creating trade log sheet: {e}")
        return None

def log_analysis_data(df_summary, underlying, market_view, total_score, support_zone, resistance_zone, signal_generated="No"):
    """Log analysis data to Google Sheets every 15 minutes"""
    try:
        client = get_google_client()
        if not client:
            return False
        
        spreadsheet = get_or_create_spreadsheet(client)
        if not spreadsheet:
            return False
        
        worksheet = create_analysis_log_sheet(spreadsheet)
        if not worksheet:
            return False
        
        # Get current time
        now = datetime.now(timezone("Asia/Kolkata"))
        
        # Get ATM data
        if not df_summary.empty:
            atm_data = df_summary[df_summary["Zone"] == "ATM"].iloc[0] if not df_summary[df_summary["Zone"] == "ATM"].empty else None
        else:
            atm_data = None
        
        # Prepare row data
        row_data = [
            now.strftime("%Y-%m-%d %H:%M:%S"),  # Timestamp
            now.strftime("%Y-%m-%d"),           # Date
            now.strftime("%H:%M:%S"),           # Time
            underlying,                          # Spot Price
            market_view,                        # Market View
            total_score,                        # Bias Score
            support_zone[0] if support_zone[0] else "",     # Support Zone Low
            support_zone[1] if support_zone[1] else "",     # Support Zone High
            resistance_zone[0] if resistance_zone[0] else "", # Resistance Zone Low
            resistance_zone[1] if resistance_zone[1] else "", # Resistance Zone High
            atm_data["Strike"] if atm_data is not None else "",  # ATM Strike
            "",  # ATM CE Price (to be filled from option data)
            "",  # ATM PE Price
            "",  # ATM CE IV
            "",  # ATM PE IV
            "",  # ATM CE OI
            "",  # ATM PE OI
            "",  # ATM CE Volume
            "",  # ATM PE Volume
            signal_generated  # Signal Generated
        ]
        
        # Append row to sheet
        worksheet.append_row(row_data)
        return True
        
    except Exception as e:
        st.error(f"❌ Failed to log analysis data: {e}")
        return False

def log_trade_data(trade_entry):
    """Log individual trade to Google Sheets"""
    try:
        client = get_google_client()
        if not client:
            return False
        
        spreadsheet = get_or_create_spreadsheet(client)
        if not spreadsheet:
            return False
        
        worksheet = create_trade_log_sheet(spreadsheet)
        if not worksheet:
            return False
        
        # Get current time
        now = datetime.now(timezone("Asia/Kolkata"))
        
        # Prepare row data
        row_data = [
            now.strftime("%Y-%m-%d"),           # Date
            trade_entry.get("Time", now.strftime("%H:%M:%S")),  # Time
            now.strftime("%Y-%m-%d %H:%M:%S"),  # Timestamp
            trade_entry.get("Strike", ""),      # Strike
            trade_entry.get("Type", ""),        # Type (CE/PE)
            trade_entry.get("LTP", ""),         # Entry Price
            trade_entry.get("Target", ""),      # Target Price
            trade_entry.get("SL", ""),          # Stop Loss
            trade_entry.get("Signal_Type", "Regular"),  # Signal Type
            trade_entry.get("Market_View", ""), # Market View
            trade_entry.get("Bias_Score", ""),  # Bias Score
            trade_entry.get("Support_Zone", ""), # Support Zone
            trade_entry.get("Resistance_Zone", ""), # Resistance Zone
            "Active",                           # Status
            trade_entry.get("Notes", "")        # Notes
        ]
        
        # Append row to sheet
        worksheet.append_row(row_data)
        return True
        
    except Exception as e:
        st.error(f"❌ Failed to log trade data: {e}")
        return False

def create_daily_summary_sheet(spreadsheet, date_str):
    """Create daily summary sheet"""
    try:
        sheet_name = f"Daily_Summary_{date_str}"
        
        # Check if sheet already exists
        try:
            worksheet = spreadsheet.worksheet(sheet_name)
            return worksheet
        except gspread.WorksheetNotFound:
            pass
        
        # Create new daily summary sheet
        worksheet = spreadsheet.add_worksheet(title=sheet_name, rows="100", cols="10")
        
        # Add summary headers
        headers = [
            "Metric", "Value", "Notes"
        ]
        worksheet.append_row(headers)
        
        return worksheet
        
    except Exception as e:
        st.error(f"❌ Error creating daily summary sheet: {e}")
        return None

def generate_daily_summary():
    """Generate daily summary of all trades and analysis"""
    try:
        client = get_google_client()
        if not client:
            return False
        
        spreadsheet = get_or_create_spreadsheet(client)
        if not spreadsheet:
            return False
        
        # Get today's date
        today = datetime.now(timezone("Asia/Kolkata")).strftime("%Y-%m-%d")
        
        # Create daily summary sheet
        summary_sheet = create_daily_summary_sheet(spreadsheet, today)
        if not summary_sheet:
            return False
        
        # Get trade log data for today
        trade_log_sheet = spreadsheet.worksheet("Trade_Log")
        all_trades = trade_log_sheet.get_all_records()
        
        # Filter today's trades
        today_trades = [trade for trade in all_trades if trade.get("Date") == today]
        
        # Calculate summary metrics
        total_trades = len(today_trades)
        ce_trades = len([t for t in today_trades if t.get("Type") == "CE"])
        pe_trades = len([t for t in today_trades if t.get("Type") == "PE"])
        
        # Get analysis log data for today
        analysis_sheet = spreadsheet.worksheet("Analysis_Log")
        all_analysis = analysis_sheet.get_all_records()
        today_analysis = [a for a in all_analysis if a.get("Date") == today]
        
        analysis_count = len(today_analysis)
        signals_generated = len([a for a in today_analysis if a.get("Signal_Generated") != "No"])
        
        # Prepare summary data
        summary_data = [
            ["Date", today, ""],
            ["Total Trades", total_trades, ""],
            ["CE Trades", ce_trades, ""],
            ["PE Trades", pe_trades, ""],
            ["Analysis Records", analysis_count, ""],
            ["Signals Generated", signals_generated, ""],
            ["Signal Rate", f"{(signals_generated/analysis_count*100):.1f}%" if analysis_count > 0 else "0%", ""],
            ["Last Updated", datetime.now(timezone("Asia/Kolkata")).strftime("%H:%M:%S"), ""]
        ]
        
        # Clear existing data and add summary
        summary_sheet.clear()
        summary_sheet.append_row(["Metric", "Value", "Notes"])
        
        for row in summary_data:
            summary_sheet.append_row(row)
        
        return True
        
    except Exception as e:
        st.error(f"❌ Failed to generate daily summary: {e}")
        return False

def test_google_sheets_connection():
    """Test Google Sheets connection"""
    try:
        client = get_google_client()
        if not client:
            return False
        
        # Try to create/access test spreadsheet
        spreadsheet = get_or_create_spreadsheet(client, "Test_Nifty_Options")
        if not spreadsheet:
            return False
        
        # Test write operation
        test_sheet = spreadsheet.sheet1
        test_sheet.update('A1', 'Test Connection')
        test_sheet.update('B1', datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        
        st.success("✅ Google Sheets connection successful!")
        return True
        
    except Exception as e:
        st.error(f"❌ Google Sheets connection failed: {e}")
        return False

# Scheduler functions
def should_log_analysis():
    """Check if it's time to log analysis (every 15 minutes)"""
    now = datetime.now(timezone("Asia/Kolkata"))
    
    # Check if we're in market hours
    current_day = now.weekday()
    current_time = now.time()
    market_start = datetime.strptime("09:00", "%H:%M").time()
    market_end = datetime.strptime("18:40", "%H:%M").time()
    
    if current_day >= 5 or not (market_start <= current_time <= market_end):
        return False
    
    # Check if it's a 15-minute interval
    return now.minute % 15 == 0

def should_generate_daily_summary():
    """Check if it's time to generate daily summary (end of day)"""
    now = datetime.now(timezone("Asia/Kolkata"))
    
    # Generate summary at market close (18:45)
    target_time = datetime.strptime("18:45", "%H:%M").time()
    current_time = now.time()
    
    # Check if it's within 5 minutes of target time
    return abs((datetime.combine(datetime.today(), current_time) - 
               datetime.combine(datetime.today(), target_time)).total_seconds()) < 300