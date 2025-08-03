import streamlit as st
import requests
import json
from datetime import datetime
from pytz import timezone
import time
import threading

class TelegramInteractiveBot:
    def __init__(self):
        self.initialize_session_state()
        self.bot_token, self.chat_id = self.get_telegram_credentials()
        self.last_update_id = 0
    
    def initialize_session_state(self):
        """Initialize bot session state"""
        if 'pending_trades' not in st.session_state:
            st.session_state.pending_trades = {}
        if 'confirmed_trades' not in st.session_state:
            st.session_state.confirmed_trades = []
        if 'bot_active' not in st.session_state:
            st.session_state.bot_active = False
        if 'manual_trades' not in st.session_state:
            st.session_state.manual_trades = []
    
    def get_telegram_credentials(self):
        """Get Telegram credentials from Streamlit secrets"""
        try:
            bot_token = st.secrets["telegram"]["bot_token"]
            chat_id = st.secrets["telegram"]["chat_id"]
            return bot_token, chat_id
        except KeyError:
            st.error("❌ Telegram credentials not found in secrets")
            return None, None
    
    def send_message(self, message, reply_markup=None):
        """Send message to Telegram with optional inline keyboard"""
        if not self.bot_token or not self.chat_id:
            return False
        
        url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
        data = {
            "chat_id": self.chat_id,
            "text": message,
            "parse_mode": "HTML"
        }
        
        if reply_markup:
            data["reply_markup"] = json.dumps(reply_markup)
        
        try:
            response = requests.post(url, data=data, timeout=10)
            return response.status_code == 200
        except:
            return False
    
    def send_trade_confirmation_request(self, trade_data):
        """Send trade signal with confirmation buttons"""
        trade_id = f"trade_{int(time.time())}"
        
        # Store pending trade
        st.session_state.pending_trades[trade_id] = {
            **trade_data,
            'timestamp': datetime.now(timezone("Asia/Kolkata")).isoformat(),
            'status': 'pending'
        }
        
        # Create message
        message = f"""
🚨 <b>TRADE SIGNAL DETECTED</b> 🚨

📍 <b>Type:</b> {trade_data.get('Type', 'N/A')} 
🎯 <b>Strike:</b> {trade_data.get('Strike', 'N/A')}
💰 <b>Entry Price:</b> ₹{trade_data.get('LTP', 'N/A')}
🎯 <b>Target:</b> ₹{trade_data.get('Target', 'N/A')}
🛑 <b>Stop Loss:</b> ₹{trade_data.get('SL', 'N/A')}

⏰ <b>Time:</b> {datetime.now(timezone('Asia/Kolkata')).strftime('%H:%M:%S')}

<b>Do you want to log this trade?</b>
        """
        
        # Create inline keyboard
        keyboard = {
            "inline_keyboard": [
                [
                    {"text": "✅ Confirm & Log", "callback_data": f"confirm_{trade_id}"},
                    {"text": "❌ Skip Trade", "callback_data": f"skip_{trade_id}"}
                ],
                [
                    {"text": "📝 Modify Trade", "callback_data": f"modify_{trade_id}"}
                ]
            ]
        }
        
        success = self.send_message(message, keyboard)
        
        if success:
            st.info(f"📱 Trade confirmation sent to Telegram (ID: {trade_id})")
        else:
            st.warning("⚠️ Failed to send Telegram confirmation")
        
        return trade_id
    
    def get_updates(self):
        """Get updates from Telegram bot"""
        if not self.bot_token:
            return []
        
        url = f"https://api.telegram.org/bot{self.bot_token}/getUpdates"
        params = {
            "offset": self.last_update_id + 1,
            "timeout": 1
        }
        
        try:
            response = requests.get(url, params=params, timeout=5)
            if response.status_code == 200:
                data = response.json()
                return data.get("result", [])
        except:
            pass
        
        return []
    
    def process_callback_query(self, callback_query):
        """Process callback query from inline keyboard"""
        callback_data = callback_query.get("callback_data", "")
        message_id = callback_query.get("message", {}).get("message_id")
        
        if callback_data.startswith("confirm_"):
            trade_id = callback_data.replace("confirm_", "")
            self.confirm_trade(trade_id, message_id)
        
        elif callback_data.startswith("skip_"):
            trade_id = callback_data.replace("skip_", "")
            self.skip_trade(trade_id, message_id)
        
        elif callback_data.startswith("modify_"):
            trade_id = callback_data.replace("modify_", "")
            self.modify_trade(trade_id, message_id)
    
    def confirm_trade(self, trade_id, message_id):
        """Confirm and log the trade"""
        if trade_id in st.session_state.pending_trades:
            trade = st.session_state.pending_trades[trade_id]
            trade['status'] = 'confirmed'
            
            # Add to confirmed trades
            st.session_state.confirmed_trades.append(trade)
            
            # Add to main trade log
            st.session_state.trade_log.append(trade)
            
            # Remove from pending
            del st.session_state.pending_trades[trade_id]
            
            # Send confirmation message
            confirmation_msg = f"""
✅ <b>TRADE CONFIRMED & LOGGED</b>

📝 <b>Trade Details:</b>
🎯 {trade.get('Type')} {trade.get('Strike')} @ ₹{trade.get('LTP')}
📊 Target: ₹{trade.get('Target')} | SL: ₹{trade.get('SL')}

🕐 <b>Logged at:</b> {datetime.now(timezone('Asia/Kolkata')).strftime('%H:%M:%S')}

Good luck with your trade! 🚀
            """
            
            self.send_message(confirmation_msg)
            
            # Edit original message
            self.edit_message(message_id, "✅ Trade Confirmed and Logged")
    
    def skip_trade(self, trade_id, message_id):
        """Skip the trade"""
        if trade_id in st.session_state.pending_trades:
            trade = st.session_state.pending_trades[trade_id]
            trade['status'] = 'skipped'
            
            # Remove from pending
            del st.session_state.pending_trades[trade_id]
            
            # Send skip message
            skip_msg = f"""
❌ <b>TRADE SKIPPED</b>

The trade signal has been ignored as requested.
            """
            
            self.send_message(skip_msg)
            
            # Edit original message
            self.edit_message(message_id, "❌ Trade Skipped")
    
    def modify_trade(self, trade_id, message_id):
        """Handle trade modification request"""
        if trade_id in st.session_state.pending_trades:
            modify_msg = f"""
📝 <b>TRADE MODIFICATION</b>

To modify this trade, please send a message in this format:

<code>/modify {trade_id} [field] [new_value]</code>

Available fields:
• <b>target</b> - Change target price
• <b>sl</b> - Change stop loss
• <b>entry</b> - Change entry price

Example: <code>/modify {trade_id} target