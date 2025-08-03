import streamlit as st
import requests
import pandas as pd
from datetime import datetime, timedelta
from pytz import timezone
import re
import time
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# Sentiment analysis libraries
try:
    from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
    VADER_AVAILABLE = True
except ImportError:
    VADER_AVAILABLE = False
    st.warning("⚠️ VADER Sentiment not available. Install: pip install vaderSentiment")

try:
    from textblob import TextBlob
    TEXTBLOB_AVAILABLE = True
except ImportError:
    TEXTBLOB_AVAILABLE = False
    st.warning("⚠️ TextBlob not available. Install: pip install textblob")

class MarketSentimentAnalyzer:
    def __init__(self):
        self.initialize_session_state()
        if VADER_AVAILABLE:
            self.vader_analyzer = SentimentIntensityAnalyzer()
        
        # News sources and keywords
        self.market_keywords = [
            'NIFTY', 'SENSEX', 'BSE', 'NSE', 'RBI', 'inflation', 'interest rate',
            'GDP', 'FII', 'DII', 'market', 'economy', 'stock', 'rupee', 'dollar',
            'crude oil', 'gold', 'banking', 'IT sector', 'pharma sector'
        ]
        
        self.positive_words = [
            'bullish', 'positive', 'growth', 'rally', 'surge', 'gain', 'rise',
            'boom', 'strong', 'recovery', 'optimistic', 'uptrend', 'breakout'
        ]
        
        self.negative_words = [
            'bearish', 'negative', 'fall', 'decline', 'crash', 'drop', 'weak',
            'recession', 'correction', 'selloff', 'pessimistic', 'downtrend'
        ]
    
    def initialize_session_state(self):
        """Initialize sentiment analysis session state"""
        if 'news_data' not in st.session_state:
            st.session_state.news_data = []
        if 'sentiment_history' not in st.session_state:
            st.session_state.sentiment_history = []
        if 'last_news_fetch' not in st.session_state:
            st.session_state.last_news_fetch = None
        if 'current_sentiment_score' not in st.session_state:
            st.session_state.current_sentiment_score = 0
    
    def fetch_news_data(self, sources=['moneycontrol', 'economic_times']):
        """Fetch news data from various sources"""
        all_news = []
        
        # Try multiple sources
        for source in sources:
            try:
                if source == 'moneycontrol':
                    news = self.fetch_moneycontrol_news()
                elif source == 'economic_times':
                    news = self.fetch_et_news()
                elif source == 'rss_feeds':
                    news = self.fetch_rss_news()
                
                all_news.extend(news)
                
            except Exception as e:
                st.warning(f"⚠️ Failed to fetch {source} news: {str(e)}")
        
        # If no news fetched, use sample data
        if not all_news:
            all_news = self.get_sample_news()
        
        # Filter market-related news
        filtered_news = self.filter_market_news(all_news)
        
        # Update session state
        st.session_state.news_data = filtered_news
        st.session_state.last_news_fetch = datetime.now(timezone("Asia/Kolkata"))
        
        return filtered_news
    
    def fetch_moneycontrol_news(self):
        """Fetch news from MoneyControl (simplified scraping)"""
        # In production, use proper web scraping with BeautifulSoup
        # This is a simplified example
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            
            # Sample request (in real implementation, parse HTML)
            url = "https://www.moneycontrol.com/news/business/markets/"
            response = requests.get(url, headers=headers, timeout=10)
            
            if response.status_code == 200:
                # Extract headlines using regex (simplified)
                headlines = re.findall(r'<h2.*?>(.*?)</h2>', response.text)
                
                news_items = []
                for headline in headlines[:10]:  # Top 10
                    if any(keyword.lower() in headline.lower() for keyword in self.market_keywords):
                        news_items.append({
                            'title': headline.strip(),
                            'source': 'MoneyControl',
                            'timestamp': datetime.now(),
                            'url': url
                        })
                
                return news_items
            
        except Exception as e:
            pass
        
        return []
    
    def fetch_et_news(self):
        """Fetch news from Economic Times"""
        # Similar implementation for ET
        return []
    
    def fetch_rss_news(self):
        """Fetch news from RSS feeds"""
        rss_feeds = [
            'https://economictimes.indiatimes.com/markets/rssfeeds/1977021501.cms',
            'https://www.moneycontrol.com/rss/business.xml'
        ]
        
        news_items = []
        
        for feed_url in rss_feeds:
            try:
                # In production, use feedparser library
                # pip install feedparser
                import feedparser
                
                feed = feedparser.parse(feed_url)
                
                for entry in feed.entries[:5]:  # Top 5 from each feed
                    news_items.append({
                        'title': entry.title,
                        'source': feed.feed.get('title', 'RSS Feed'),
                        'timestamp': datetime.now(),
                        'url': entry.link,
                        'summary': entry.get('summary', '')
                    })
                    
            except ImportError:
                st.warning("⚠️ RSS parsing requires feedparser: pip install feedparser")
            except Exception as e:
                continue
        
        return news_items
    
    def get_sample_news(self):
        """Get sample news data for demo purposes"""
        sample_news = [
            {
                'title': 'Nifty 50 hits fresh record high on strong FII inflows',
                'source': 'Market News',
                'timestamp': datetime.now() - timedelta(minutes=30),
                'sentiment_score': 0.8
            },
            {
                'title': 'RBI maintains repo rate at 6.5% in policy review',
                'source': 'Economic Times',
                'timestamp': datetime.now() - timedelta(hours=1),
                'sentiment_score': 0.2
            },
            {
                'title': 'Banking stocks surge on positive Q3 earnings outlook',
                'source': 'MoneyControl',
                'timestamp': datetime.now() - timedelta(hours=2),
                'sentiment_score': 0.6
            },
            {
                'title': 'Crude oil prices decline amid global economic concerns',
                'source': 'Business Standard',
                'timestamp': datetime.now() - timedelta(hours=3),
                'sentiment_score': -0.4
            },
            {
                'title': 'IT sector faces headwinds from US recession fears',
                'source': 'Financial Express',
                'timestamp': datetime.now() - timedelta(hours=4),
                'sentiment_score': -0.3
            },
            {
                'title': 'Government announces new infrastructure spending package',
                'source': 'Economic Survey',
                'timestamp': datetime.now() - timedelta(hours=5),
                'sentiment_score': 0.5
            }
        ]
        
        return sample_news
    
    def filter_market_news(self, news_items):
        """Filter news items relevant to market"""
        filtered_news = []
        
        for item in news_items:
            title = item.get('title', '').lower()
            summary = item.get('summary', '').lower()
            content = title + ' ' + summary
            
            # Check if news is market-related
            if any(keyword.lower() in content for keyword in self.market_keywords):
                filtered_news.append(item)
        
        return filtered_news[:20]  # Top 20 relevant news
    
    def analyze_sentiment_vader(self, text):
        """Analyze sentiment using VADER"""
        if not VADER_AVAILABLE:
            return 0
        
        scores = self.vader_analyzer.polarity_scores(text)
        return scores['compound']  # Returns score between -1 and 1
    
    def analyze_sentiment_textblob(self, text):
        """Analyze sentiment using TextBlob"""
        if not TEXTBLOB_AVAILABLE:
            return 0
        
        blob = TextBlob(text)
        return blob.sentiment.polarity  # Returns score between -1 and 1
    
    def analyze_sentiment_simple(self, text):
        """Simple rule-based sentiment analysis"""
        text = text.lower()
        
        positive_count = sum(1 for word in self.positive_words if word in text)
        negative_count = sum(1 for word in self.negative_words if word in text)
        
        # Calculate simple sentiment score
        if positive_count + negative_count == 0:
            return 0
        
        sentiment_score = (positive_count - negative_count) / (positive_count + negative_count)
        return sentiment_score
    
    def analyze_news_sentiment(self, news_items):
        """Analyze sentiment for all news items"""
        analyzed_news = []
        
        for item in news_items:
            title = item.get('title', '')
            summary = item.get('summary', '')
            content = title + ' ' + summary
            
            # Try multiple sentiment analysis methods
            sentiments = []
            
            if VADER_AVAILABLE:
                vader_score = self.analyze_sentiment_vader(content)
                sentiments.append(vader_score)
            
            if TEXTBLOB_AVAILABLE:
                textblob_score = self.analyze_sentiment_textblob(content)
                sentiments.append(textblob_score)
            
            # Always include simple analysis as fallback
            simple_score = self.analyze_sentiment_simple(content)
            sentiments.append(simple_score)
            
            # Average the sentiment scores
            avg_sentiment = sum(sentiments) / len(sentiments) if sentiments else 0
            
            # Add sentiment to news item
            item['sentiment_score'] = round(avg_sentiment, 3)
            item['sentiment_label'] = self.get_sentiment_label(avg_sentiment)
            
            analyzed_news.append(item)
        
        return analyzed_news
    
    def get_sentiment_label(self, score):
        """Convert sentiment score to label"""
        if score > 0.3:
            return "🟢 Positive"
        elif score < -0.3:
            return "🔴 Negative"
        else:
            return "🟡 Neutral"
    
    def calculate_overall_sentiment(self, analyzed_news):
        """Calculate overall market sentiment"""
        if not analyzed_news:
            return 0, "🟡 Neutral"
        
        # Weight recent news more heavily
        now = datetime.now(timezone("Asia/Kolkata"))
        weighted_scores = []
        
        for item in analyzed_news:
            timestamp = item.get('timestamp', now)
            if isinstance(timestamp, str):
                timestamp = datetime.fromisoformat(timestamp)
            
            # Calculate time weight (more recent = higher weight)
            hours_ago = (now - timestamp).total_seconds() / 3600
            time_weight = max(0.1, 1 / (1 + hours_ago * 0.1))  # Exponential decay
            
            sentiment_score = item.get('sentiment_score', 0)
            weighted_scores.append(sentiment_score * time_weight)
        
        overall_sentiment = sum(weighted_scores) / len(weighted_scores)
        sentiment_label = self.get_sentiment_label(overall_sentiment)
        
        return round(overall_sentiment, 3), sentiment_label
    
    def update_sentiment_history(self, sentiment_score):
        """Update sentiment history for tracking"""
        now = datetime.now(timezone("Asia/Kolkata"))
        
        # Add current sentiment to history
        st.session_state.sentiment_history.append({
            'timestamp': now,
            'sentiment_score': sentiment_score,
            'time_str': now.strftime("%H:%M")
        })
        
        # Keep only last 24 hours of data
        cutoff_time = now - timedelta(hours=24)
        st.session_state.sentiment_history = [
            item for item in st.session_state.sentiment_history
            if item['timestamp'] > cutoff_time
        ]
    
    def render_sentiment_analysis_ui(self):
        """Render sentiment analysis interface"""
        st.markdown("## 📰 Market Sentiment Analysis")
        
        # Fetch news button and auto-refresh logic
        col1, col2, col3 = st.columns(3)
        
        with col1:
            if st.button("🔄 Refresh News", type="primary"):
                with st.spinner("Fetching latest news..."):
                    self.fetch_and_analyze_news()
        
        with col2:
            auto_refresh = st.checkbox("Auto Refresh", value=True)
        
        with col3:
            if st.session_state.last_news_fetch:
                last_fetch = st.session_state.last_news_fetch.strftime("%H:%M:%S")
                st.caption(f"Last update: {last_fetch}")
        
        # Auto refresh every 15 minutes
        if auto_refresh:
            if (not st.session_state.last_news_fetch or 
                (datetime.now(timezone("Asia/Kolkata")) - st.session_state.last_news_fetch).total_seconds() > 900):
                self.fetch_and_analyze_news()
        
        # Display sentiment dashboard
        self.render_sentiment_dashboard()
        
        # Display news feed
        self.render_news_feed()
        
        # Display sentiment trends
        self.render_sentiment_trends()
    
    def fetch_and_analyze_news(self):
        """Fetch and analyze news sentiment"""
        try:
            # Fetch news
            news_items = self.fetch_news_data()
            
            if news_items:
                # Analyze sentiment
                analyzed_news = self.analyze_news_sentiment(news_items)
                
                # Calculate overall sentiment
                overall_score, overall_label = self.calculate_overall_sentiment(analyzed_news)
                
                # Update session state
                st.session_state.news_data = analyzed_news
                st.session_state.current_sentiment_score = overall_score
                
                # Update history
                self.update_sentiment_history(overall_score)
                
                st.success(f"✅ Analyzed {len(analyzed_news)} news items")
            else:
                st.warning("⚠️ No relevant news found")
                
        except Exception as e:
            st.error(f"❌ Error fetching news: {str(e)}")
    
    def render_sentiment_dashboard(self):
        """Render sentiment dashboard with key metrics"""
        if not st.session_state.news_data:
            st.info("📰 Click 'Refresh News' to fetch latest market sentiment")
            return
        
        # Overall sentiment score
        overall_score = st.session_state.current_sentiment_score
        overall_label = self.get_sentiment_label(overall_score)
        
        # Create metrics dashboard
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            # Sentiment score with color coding
            if overall_score > 0.3:
                st.success(f"📈 Sentiment: {overall_score:+.2f}")
            elif overall_score < -0.3:
                st.error(f"📉 Sentiment: {overall_score:+.2f}")
            else:
                st.info(f"📊 Sentiment: {overall_score:+.2f}")
        
        with col2:
            st.metric("🎯 Market Mood", overall_label.split()[1])
        
        with col3:
            positive_news = len([n for n in st.session_state.news_data if n.get('sentiment_score', 0) > 0.1])
            st.metric("🟢 Positive News", positive_news)
        
        with col4:
            negative_news = len([n for n in st.session_state.news_data if n.get('sentiment_score', 0) < -0.1])
            st.metric("🔴 Negative News", negative_news)
        
        # Sentiment gauge
        self.render_sentiment_gauge(overall_score)
        
        # Top headlines
        self.render_top_headlines()
    
    def render_sentiment_gauge(self, sentiment_score):
        """Render sentiment gauge chart"""
        fig = go.Figure(go.Indicator(
            mode = "gauge+number+delta",
            value = sentiment_score,
            domain = {'x': [0, 1], 'y': [0, 1]},
            title = {'text': "Market Sentiment Score"},
            delta = {'reference': 0},
            gauge = {
                'axis': {'range': [-1, 1]},
                'bar': {'color': "darkblue"},
                'steps': [
                    {'range': [-1, -0.3], 'color': "lightcoral"},
                    {'range': [-0.3, 0.3], 'color': "lightyellow"},
                    {'range': [0.3, 1], 'color': "lightgreen"}
                ],
                'threshold': {
                    'line': {'color': "red", 'width': 4},
                    'thickness': 0.75,
                    'value': 0
                }
            }
        ))
        
        fig.update_layout(
            height=300,
            title="Current Market Sentiment",
            template="plotly_white"
        )
        
        st.plotly_chart(fig, use_container_width=True)
    
    def render_top_headlines(self):
        """Render top 3 headlines with sentiment"""
        st.markdown("### 📋 Top Headlines")
        
        # Sort news by absolute sentiment score (most impactful)
        sorted_news = sorted(
            st.session_state.news_data,
            key=lambda x: abs(x.get('sentiment_score', 0)),
            reverse=True
        )
        
        for i, news in enumerate(sorted_news[:3], 1):
            sentiment_score = news.get('sentiment_score', 0)
            sentiment_label = news.get('sentiment_label', '🟡 Neutral')
            
            # Create expandable headline
            with st.expander(f"#{i} {news.get('title', 'No title')}", expanded=i==1):
                col1, col2 = st.columns([3, 1])
                
                with col1:
                    st.write(f"**Source:** {news.get('source', 'Unknown')}")
                    if 'summary' in news:
                        st.write(f"**Summary:** {news['summary'][:200]}...")
                    
                    timestamp = news.get('timestamp', datetime.now())
                    if isinstance(timestamp, datetime):
                        time_str = timestamp.strftime("%H:%M, %d %b")
                    else:
                        time_str = str(timestamp)
                    st.caption(f"Time: {time_str}")
                
                with col2:
                    st.metric("Sentiment", f"{sentiment_score:+.2f}")
                    st.write(sentiment_label)
                    
                    if 'url' in news:
                        st.link_button("🔗 Read More", news['url'])
    
    def render_news_feed(self):
        """Render complete news feed"""
        if not st.session_state.news_data:
            return
        
        st.markdown("### 📰 Complete News Feed")
        
        # Filter options
        col1, col2 = st.columns(2)
        
        with col1:
            sentiment_filter = st.selectbox(
                "Filter by Sentiment",
                ["All", "Positive", "Negative", "Neutral"]
            )
        
        with col2:
            sort_by = st.selectbox(
                "Sort by",
                ["Sentiment Impact", "Time", "Source"]
            )
        
        # Apply filters
        filtered_news = st.session_state.news_data.copy()
        
        if sentiment_filter != "All":
            if sentiment_filter == "Positive":
                filtered_news = [n for n in filtered_news if n.get('sentiment_score', 0) > 0.1]
            elif sentiment_filter == "Negative":
                filtered_news = [n for n in filtered_news if n.get('sentiment_score', 0) < -0.1]
            elif sentiment_filter == "Neutral":
                filtered_news = [n for n in filtered_news if -0.1 <= n.get('sentiment_score', 0) <= 0.1]
        
        # Apply sorting
        if sort_by == "Sentiment Impact":
            filtered_news.sort(key=lambda x: abs(x.get('sentiment_score', 0)), reverse=True)
        elif sort_by == "Time":
            filtered_news.sort(key=lambda x: x.get('timestamp', datetime.now()), reverse=True)
        elif sort_by == "Source":
            filtered_news.sort(key=lambda x: x.get('source', ''))
        
        # Display filtered news
        if filtered_news:
            # Create DataFrame for better display
            news_df = pd.DataFrame([{
                'Title': item.get('title', 'No title')[:80] + '...' if len(item.get('title', '')) > 80 else item.get('title', 'No title'),
                'Source': item.get('source', 'Unknown'),
                'Sentiment': f"{item.get('sentiment_score', 0):+.2f}",
                'Label': item.get('sentiment_label', '🟡 Neutral'),
                'Time': item.get('timestamp', datetime.now()).strftime('%H:%M') if isinstance(item.get('timestamp'), datetime) else str(item.get('timestamp', ''))
            } for item in filtered_news])
            
            # Style the dataframe
            def highlight_sentiment(row):
                colors = []
                for col in row.index:
                    if col == 'Sentiment':
                        val = float(row[col])
                        if val > 0.3:
                            colors.append('background-color: #d4edda; color: #155724')
                        elif val < -0.3:
                            colors.append('background-color: #f8d7da; color: #721c24')
                        else:
                            colors.append('background-color: #fff3cd; color: #856404')
                    else:
                        colors.append('')
                return colors
            
            styled_df = news_df.style.apply(highlight_sentiment, axis=1)
            st.dataframe(styled_df, use_container_width=True, height=400)
        else:
            st.info("No news items match the selected filters")
    
    def render_sentiment_trends(self):
        """Render sentiment trends over time"""
        if not st.session_state.sentiment_history:
            return
        
        st.markdown("### 📈 Sentiment Trends")
        
        # Create DataFrame from history
        history_df = pd.DataFrame(st.session_state.sentiment_history)
        
        if len(history_df) < 2:
            st.info("Need more data points to show trends")
            return
        
        # Create time series chart
        fig = go.Figure()
        
        # Add sentiment line
        fig.add_trace(go.Scatter(
            x=history_df['timestamp'],
            y=history_df['sentiment_score'],
            mode='lines+markers',
            name='Sentiment Score',
            line=dict(color='blue', width=2),
            marker=dict(size=6)
        ))
        
        # Add sentiment zones
        fig.add_hline(y=0.3, line_dash="dash", line_color="green", 
                     annotation_text="Positive Zone", annotation_position="right")
        fig.add_hline(y=-0.3, line_dash="dash", line_color="red", 
                     annotation_text="Negative Zone", annotation_position="right")
        fig.add_hline(y=0, line_dash="dot", line_color="gray", 
                     annotation_text="Neutral", annotation_position="right")
        
        # Fill sentiment zones
        fig.add_shape(type="rect", xref="paper", yref="y",
                     x0=0, x1=1, y0=0.3, y1=1,
                     fillcolor="rgba(0,255,0,0.1)", line=dict(width=0))
        fig.add_shape(type="rect", xref="paper", yref="y",
                     x0=0, x1=1, y0=-1, y1=-0.3,
                     fillcolor="rgba(255,0,0,0.1)", line=dict(width=0))
        
        fig.update_layout(
            title="Market Sentiment Over Time",
            xaxis_title="Time",
            yaxis_title="Sentiment Score",
            template="plotly_white",
            height=400,
            yaxis=dict(range=[-1, 1])
        )
        
        st.plotly_chart(fig, use_container_width=True)
        
        # Sentiment statistics
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            avg_sentiment = history_df['sentiment_score'].mean()
            st.metric("📊 Avg Sentiment", f"{avg_sentiment:+.2f}")
        
        with col2:
            max_sentiment = history_df['sentiment_score'].max()
            st.metric("📈 Peak Positive", f"{max_sentiment:+.2f}")
        
        with col3:
            min_sentiment = history_df['sentiment_score'].min()
            st.metric("📉 Peak Negative", f"{min_sentiment:+.2f}")
        
        with col4:
            sentiment_volatility = history_df['sentiment_score'].std()
            st.metric("🔀 Volatility", f"{sentiment_volatility:.2f}")
    
    def get_trading_signal_from_sentiment(self):
        """Generate trading signals based on sentiment analysis"""
        if not st.session_state.news_data:
            return None
        
        current_sentiment = st.session_state.current_sentiment_score
        
        # Simple sentiment-based signals
        if current_sentiment > 0.5:
            return {
                'signal': 'BULLISH',
                'confidence': min(abs(current_sentiment) * 100, 95),
                'reason': 'Strong positive market sentiment detected',
                'color': 'success'
            }
        elif current_sentiment < -0.5:
            return {
                'signal': 'BEARISH',
                'confidence': min(abs(current_sentiment) * 100, 95),
                'reason': 'Strong negative market sentiment detected',
                'color': 'error'
            }
        elif abs(current_sentiment) > 0.3:
            direction = 'BULLISH' if current_sentiment > 0 else 'BEARISH'
            return {
                'signal': f'WEAK {direction}',
                'confidence': abs(current_sentiment) * 100,
                'reason': f'Moderate {direction.lower()} sentiment detected',
                'color': 'info'
            }
        else:
            return {
                'signal': 'NEUTRAL',
                'confidence': 50,
                'reason': 'Mixed or neutral market sentiment',
                'color': 'info'
            }

# Main function to render sentiment analysis
def render_sentiment_analysis():
    """Main function to render sentiment analysis"""
    analyzer = MarketSentimentAnalyzer()
    analyzer.render_sentiment_analysis_ui()

# Function to get current sentiment score for main app
def get_current_sentiment_score():
    """Get current sentiment score for use in main analysis"""
    return st.session_state.get('current_sentiment_score', 0)