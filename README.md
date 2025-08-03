# 📈 Nifty Options Analyzer

A comprehensive real-time Nifty options trading analyzer with automated signals, Greek calculations, and Telegram notifications.

## 🚀 Features

- **Real-time NSE Data**: Live option chain analysis from NSE
- **Greek Calculations**: Delta, Gamma, Vega, Theta, Rho for all strikes
- **Multi-factor Analysis**: Bias scoring with 7+ parameters
- **Support/Resistance**: Dynamic S/R zone identification
- **Reversal Signals**: ATM reversal pattern detection
- **Expiry Day Logic**: Specialized analysis for expiry days
- **Telegram Alerts**: Real-time notifications for all signals
- **Interactive UI**: Charts, tables, and live data visualization
- **Trade Log**: Enhanced P&L tracking with Excel export
- **Auto-refresh**: Configurable refresh intervals

## 📊 Analysis Methods

### Bias Scoring System
- **Change in OI Bias** (Weight: 2)
- **Volume Bias** (Weight: 1)
- **Gamma Bias** (Weight: 1)
- **Ask/Bid Quantity Bias** (Weight: 1 each)
- **IV Bias** (Weight: 1)
- **Delta-Volume-Price Bias** (Weight: 1)

### Signal Types
- **Trade Signals**: Call/Put entries at S/R levels
- **Reversal Alerts**: ATM reversal pattern detection
- **Liquidity Spikes**: Sudden volume/OI increases
- **Expiry Signals**: Specialized expiry day analysis

## 🛠️ Quick Start

### 1. Installation
```bash
git clone https://github.com/yourusername/nifty-options-analyzer.git
cd nifty-options-analyzer
pip install -r requirements.txt
```

### 2. Configuration
Create your secrets file:
```bash
cp .streamlit/secrets.toml.example .streamlit/secrets.toml
```

Edit `.streamlit/secrets.toml` with your credentials:
```toml
[telegram]
bot_token = "your_bot_token_here"
chat_id = "your_chat_id_here"
```

### 3. Run Application
```bash
streamlit run main_app.py
```

## 🤖 Telegram Bot Setup

1. **Create Bot**: Message @BotFather on Telegram
2. **Get Token**: Save the bot token from BotFather
3. **Get Chat ID**: Message @userinfobot to get your chat ID
4. **Add to Secrets**: Update `.streamlit/secrets.toml`

## 🌐 Streamlit Cloud Deployment

1. **Push to GitHub**: Ensure all files are committed
2. **Connect Repository**: Link your repo to Streamlit Cloud
3. **Set Main File**: Specify `main_app.py` as entry point
4. **Add Secrets**: Copy your secrets to Streamlit Cloud dashboard

## 📁 Project Structure

```
nifty-options-analyzer/
├── main_app.py                 # Main application entry point
├── data_processing.py          # NSE data fetching and processing
├── analysis_functions.py       # Analysis logic and calculations
├── telegram_notifications.py   # Telegram alert system
├── ui_components.py           # UI components and charts
├── expiry_analysis.py         # Expiry day specific analysis
├── regular_analysis.py        # Regular trading day analysis
├── requirements.txt           # Python dependencies
├── .gitignore                # Git ignore rules
├── README.md                 # This file
├── SETUP.md                  # Detailed setup guide
└── .streamlit/
    └── secrets.toml.example  # Template for credentials
```

## ⚙️ Configuration Options

### Refresh Settings
- **Default**: 2 minutes (120 seconds)
- **Minimum**: 30 seconds
- **Configurable**: Via sidebar settings

### Market Hours
- **Active**: Monday-Friday, 9:00 AM - 6:40 PM IST
- **Auto-detection**: Shows rest message outside hours

## 📈 Usage

### Signal Interpretation
- **Strong Bullish**: Score ≥ 4
- **Bullish**: Score ≥ 2
- **Neutral**: -2 < Score < 2
- **Bearish**: Score ≤ -2
- **Strong Bearish**: Score ≤ -4

### Trade Entries
- **Call Entry**: Bullish bias at support levels
- **Put Entry**: Bearish bias at resistance levels
- **Targets**: Based on S/R distance or IV
- **Stop Loss**: 20% of entry price

## 🔒 Security

- **No hardcoded credentials**: All secrets in config files
- **Gitignore protection**: Secrets never committed to repo
- **Environment isolation**: Local and cloud secrets separate

## 🤝 Contributing

1. Fork the repository
2. Create feature branch: `git checkout -b feature-name`
3. Commit changes: `git commit -am 'Add feature'`
4. Push to branch: `git push origin feature-name`
5. Submit pull request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## ⚠️ Disclaimer

This tool is for educational and analysis purposes only. Trading involves risk, and past performance doesn't guarantee future results. Always do your own research before making trading decisions.

## 📞 Support

- **Issues**: Open a GitHub issue
- **Documentation**: See SETUP.md for detailed instructions
- **Updates**: Watch the repository for updates

---

Made with ❤️ for the trading community