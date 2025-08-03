# 🛠️ Nifty Options Analyzer - Detailed Setup Guide

## 📋 Prerequisites

- Python 3.8 or higher
- Git installed
- Telegram account
- Internet connection for NSE data

## 🔧 Local Development Setup

### Step 1: Clone Repository
```bash
git clone https://github.com/yourusername/nifty-options-analyzer.git
cd nifty-options-analyzer
```

### Step 2: Create Virtual Environment
```bash
# Windows
python -m venv venv
venv\Scripts\activate

# macOS/Linux
python3 -m venv venv
source venv/bin/activate
```

### Step 3: Install Dependencies
```bash
pip install --upgrade pip
pip install -r requirements.txt
```

### Step 4: Setup Telegram Bot

#### Create Telegram Bot:
1. Open Telegram and search for @BotFather
2. Send `/newbot` command
3. Follow instructions to create your bot
4. **Save the bot token** (format: `123456789:ABCdefGHIjklMNOpqrsTUVwxyz`)

#### Get Your Chat ID:
1. Message @userinfobot on Telegram
2. Send any message to get your chat ID
3. **Save the chat ID** (format: `123456789`)

### Step 5: Configure Secrets
```bash
# Create streamlit directory
mkdir .streamlit

# Copy example file
cp .streamlit/secrets.toml.example .streamlit/secrets.toml
```

Edit `.streamlit/secrets.toml`:
```toml
[telegram]
bot_token = "123456789:ABCdefGHIjklMNOpqrsTUVwxyz"
chat_id = "123456789"
```

### Step 6: Test Installation
```bash
streamlit run main_app.py
```

Your app should open at `http://localhost:8501`

### Step 7: Test Telegram Connection
1. In the app sidebar, find "Telegram Test"
2. Click "Test Telegram Connection"
3. You should see ✅ success and receive a test message

## 🌐 Streamlit Cloud Deployment

### Step 1: Prepare Repository
```bash
# Ensure all files are committed
git add .
git commit -m "Add Nifty Options Analyzer"
git push origin main
```

### Step 2: Deploy to Streamlit Cloud

1. **Go to**: https://share.streamlit.io/
2. **Sign in**: With your GitHub account
3. **New app**: Click "New app"
4. **Repository**: Select your repository
5. **Branch**: `main`
6. **Main file path**: `main_app.py`
7. **Click**: "Deploy!"

### Step 3: Configure Secrets in Cloud

1. **App Settings**: Click on your app settings
2. **Secrets Tab**: Find the "Secrets" section
3. **Add Secrets**: Copy and paste:

```toml
[telegram]
bot_token = "123456789:ABCdefGHIjklMNOpqrsTUVwxyz"
chat_id = "123456789"
```

4. **Save**: Click "Save"
5. **Reboot**: Your app will restart automatically

## 🧪 Testing & Verification

### Local Testing Checklist
- [ ] Virtual environment activated
- [ ] All packages installed successfully
- [ ] `.streamlit/secrets.toml` file created
- [ ] Telegram bot token and chat ID configured
- [ ] App starts without errors
- [ ] Telegram test connection works
- [ ] Market data loads (during market hours)

### Cloud Testing Checklist
- [ ] App deploys successfully
- [ ] No import errors in logs
- [ ] Secrets configured in cloud dashboard
- [ ] Telegram notifications work
- [ ] All features functional

## 🔍 Troubleshooting

### Common Issues

#### "Module not found" errors
```bash
# Ensure virtual environment is active
source venv/bin/activate  # macOS/Linux
venv\Scripts\activate     # Windows

# Reinstall requirements
pip install -r requirements.txt
```

#### "Telegram credentials not found"
- Check `.streamlit/secrets.toml` exists
- Verify file format (TOML syntax)
- Ensure proper indentation
- Check for extra quotes or spaces

#### "Connection failed" to Telegram
- Test bot token with @BotFather
- Verify chat ID is correct (numbers only)
- Check internet connection
- Try sending `/start` to your bot first

#### NSE data fetch errors
- Market hours: 9:00 AM - 6:40 PM IST, Monday-Friday
- Check internet connection
- NSE API may be temporarily down

### Debug Mode
Add this to your `main_app.py` for debugging:
```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

## 🔄 Updates & Maintenance

### Updating the Application
```bash
git pull origin main
pip install -r requirements.txt --upgrade
streamlit run main_app.py
```

### Adding New Features
1. Create feature branch: `git checkout -b feature-name`
2. Make changes and test locally
3. Commit and push: `git push origin feature-name`
4. Create pull request
5. Merge and deploy

## 📊 Performance Optimization

### Refresh Rate Settings
- **High frequency**: 30-60 seconds (more data, higher load)
- **Balanced**: 2-3 minutes (recommended)
- **Conservative**: 5+ minutes (light load)

### Memory Management
- App automatically manages session state
- Clear browser cache if performance issues
- Restart app if memory usage high

## 🔒 Security Best Practices

### Local Development
- Never commit `.streamlit/secrets.toml`
- Use different tokens for dev/production
- Regularly rotate API keys

### Production
- Monitor telegram bot usage
- Set up logging for debugging
- Regular security updates

## 🆘 Getting Help

### Self-Help Resources
1. Check this SETUP.md file
2. Review error messages in terminal
3. Test individual components
4. Check Streamlit Cloud logs

### Community Support
- **GitHub Issues**: Report bugs and feature requests
- **Streamlit Forums**: General Streamlit questions
- **Telegram**: For bot-related issues

### Error Reporting
When reporting issues, include:
- Error message (full text)
- Steps to reproduce
- Operating system
- Python version
- Screenshot if applicable

---

## 🎯 Quick Reference

### Essential Commands
```bash
# Activate environment
source venv/bin/activate  # macOS/Linux
venv\Scripts\activate     # Windows

# Run app
streamlit run main_app.py

# Update packages
pip install -r requirements.txt --upgrade

# Check logs
streamlit run main_app.py --logger.level=debug
```

### File Structure
- **main_app.py**: Start here for app entry point
- **requirements.txt**: Python packages only
- **.streamlit/secrets.toml**: Your credentials (not in git)
- **README.md**: Overview and quick start
- **SETUP.md**: This detailed guide

Happy Trading! 📈