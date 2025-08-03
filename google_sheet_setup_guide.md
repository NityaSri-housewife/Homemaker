# 📊 Google Sheets Integration Setup Guide

## 🎯 What This Does

Your Nifty Options Analyzer will now automatically:
- **Log analysis data every 15 minutes** during market hours
- **Log all trades immediately** when signals are generated  
- **Generate daily summary** at market close (6:45 PM)
- **Create organized sheets** for different data types

## 📋 Google Cloud Setup (One-time)

### Step 1: Create Google Cloud Project
1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Click "New Project" 
3. Project name: `nifty-options-analyzer`
4. Click "Create"

### Step 2: Enable Google Sheets API
1. In your project, go to "APIs & Services" > "Library"
2. Search for "Google Sheets API"
3. Click on it and press "Enable"
4. Also enable "Google Drive API" (for file creation)

### Step 3: Create Service Account
1. Go to "APIs & Services" > "Credentials"
2. Click "Create Credentials" > "Service Account"
3. Service account name: `nifty-sheets-logger`
4. Click "Create and Continue"
5. Role: Select "Editor" 
6. Click "Continue" > "Done"

### Step 4: Generate Service Account Key
1. Click on your service account email
2. Go to "Keys" tab
3. Click "Add Key" > "Create New Key"
4. Choose "JSON" format
5. Click "Create" - **Download the JSON file**

## 🔐 Configure Streamlit Secrets

### Update your `.streamlit/secrets.toml`:

```toml
[telegram]
bot_token = "your_bot_token"
chat_id = "your_chat_id"

[google_sheets]
type = "service_account"
project_id = "your-project-id"
private_key_id = "your-private-key-id"
private_key = "-----BEGIN PRIVATE KEY-----\nyour-private-key-here\n-----END PRIVATE KEY-----"
client_email = "nifty-sheets-logger@your-project-id.iam.gserviceaccount.com"
client_id = "your-client-id"
auth_uri = "https://accounts.google.com/o/oauth2/auth"
token_uri = "https://oauth2.googleapis.com/token"
auth_provider_x509_cert_url = "https://www.googleapis.com/oauth2/v1/certs"
client_x509_cert_url = "https://www.googleapis.com/robot/v1/metadata/x509/nifty-sheets-logger%40your-project-id.iam.gserviceaccount.com"

# Optional: Your email to share sheets with
user_email = "your.email@gmail.com"
```

### How to Fill the Values:

Open your downloaded JSON file and copy these values:

```json
{
  "type": "service_account",                    // ← Copy to secrets.toml
  "project_id": "your-project-id",              // ← Copy to secrets.toml  
  "private_key_id": "abc123...",                // ← Copy to secrets.toml
  "private_key": "-----BEGIN PRIVATE KEY...",   // ← Copy to secrets.toml
  "client_email": "service@project.iam...",     // ← Copy to secrets.toml
  "client_id": "123456789",                     // ← Copy to secrets.toml
  "auth_uri": "https://accounts.google.com...", // ← Copy to secrets.toml
  "token_uri": "https://oauth2.googleapis...",  // ← Copy to secrets.toml
  "auth_provider_x509_cert_url": "https://...", // ← Copy to secrets.toml
  "client_x509_cert_url": "https://www.goog..." // ← Copy to secrets.toml
}
```

## 🚀 Streamlit Cloud Configuration

### Add Secrets to Streamlit Cloud:

In your Streamlit Cloud app settings, add to secrets:

```toml
[telegram]
bot_token = "your_bot_token"
chat_id = "your_chat_id"

[google_sheets]
type = "service_account"
project_id = "your-project-id-here"
private_key_id = "your-private-key-id-here"
private_key = "-----BEGIN PRIVATE KEY-----\nYOUR-VERY-LONG-PRIVATE-KEY-HERE\n-----END PRIVATE KEY-----"
client_email = "your-service-account@your-project.iam.gserviceaccount.com"
client_id = "your-client-id-here"
auth_uri = "https://accounts.google.com/o/oauth2/auth"
token_uri = "https://oauth2.googleapis.com/token"
auth_provider_x509_cert_url = "https://www.googleapis.com/oauth2/v1/certs"
client_x509_cert_url = "https://www.googleapis.com/robot/v1/metadata/x509/your-service-account%40your-project.iam.gserviceaccount.com"

user_email = "your.email@gmail.com"
```

## 📊 What Gets Created

### Automatic Spreadsheet Structure:

```
Nifty Options Analysis (Google Sheet)
├── Analysis_Log        # Every 15 min during market hours
├── Trade_Log          # Every trade signal  
├── Daily_Summary_2025-08-03    # Daily summaries
├── Daily_Summary_2025-08-04    # One per day
└── Daily_Summary_2025-08-05    # Auto-created
```

### Analysis_Log Columns:
- Timestamp, Date, Time
- Spot_Price, Market_View, Bias_Score  
- Support/Resistance Zones
- ATM Strike data
- Signal_Generated flag

### Trade_Log Columns:
- Date, Time, Strike, Type (CE/PE)
- Entry_Price, Target_Price, Stop_Loss
- Signal_Type, Market_View, Bias_Score
- Status, Notes

### Daily_Summary Contains:
- Total trades count
- CE vs PE trade distribution  
- Analysis records count
- Signal generation rate
- Performance metrics

## 🧪 Testing

### Test in Your App:
1. Start your app: `streamlit run main_app.py`
2. In sidebar: Click "🧪 Test Google Sheets"
3. Should see: ✅ "Google Sheets connection successful!"

### Manual Controls in Sidebar:
- **📝 Log Now**: Force log current analysis
- **📋 Daily Summary**: Generate summary manually  
- **Status indicators**: Shows logging status

## ⚙️ Automatic Logging Behavior

### Analysis Logging (Every 15 Minutes):
- **When**: Market hours (9 AM - 6:40 PM), every 15 minutes
- **What**: Complete market analysis snapshot
- **Prevents duplicates**: Won't log if already logged in last 14 minutes

### Trade Logging (Immediate):
- **When**: Any trade signal is generated
- **What**: Complete trade details with context
- **Enhanced data**: Market view, bias scores, S/R levels

### Daily Summary (Market Close):
- **When**: 6:45 PM (5 minutes after market close)
- **What**: Day's trading and analysis summary
- **Frequency**: Once per day

## 🔍 Monitoring & Debugging

### Sidebar Status Indicators:
- 🟢 **Active**: Currently logging
- 🔵 **Waiting**: Ready for next interval
- ⚠️ **Warning**: Check connection

### Error Handling:
- App continues working even if Google Sheets fails
- Local logging always works as backup
- Clear error messages in UI

## 📈 Data Analysis Benefits

### Historical Analysis:
- Track signal accuracy over time
- Analyze market condition patterns
- Optimize bias scoring weights

### Performance Tracking:
- Daily/weekly/monthly summaries
- Signal generation frequency
- Market timing analysis

### Export Capabilities:
- Data already in Google Sheets
- Easy to create charts and pivot tables
- Share analysis with others

## 🔒 Security Notes

- Service account has limited permissions
- Only accesses sheets you create
- No personal Google account access
- Credentials encrypted in Streamlit secrets

## 🆘 Troubleshooting

### "Credentials not found":
- Check secrets.toml format
- Ensure all fields copied correctly
- Verify no extra spaces/characters

### "Permission denied":
- Ensure Google Sheets API is enabled
- Check service account has Editor role
- Verify project ID matches

### "Sheet not found":
- App will auto-create sheets
- Check service account email is correct
- Ensure sufficient Google Drive storage

---

## 🎯 Quick Start Checklist

- [ ] Created Google Cloud project
- [ ] Enabled Google Sheets & Drive APIs  
- [ ] Created service account with Editor role
- [ ] Downloaded JSON credentials file
- [ ] Updated `.streamlit/secrets.toml` with all values
- [ ] Added secrets to Streamlit Cloud dashboard
- [ ] Updated `requirements.txt` with new packages
- [ ] Tested connection in app sidebar
- [ ] Verified automatic logging works

Your Nifty Options Analyzer now has enterprise-grade data logging! 🚀