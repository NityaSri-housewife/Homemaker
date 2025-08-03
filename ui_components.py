import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import io
from datetime import datetime
from pytz import timezone

def display_enhanced_trade_log():
    """Display enhanced trade log with improved styling and live P&L"""
    if not st.session_state.trade_log:
        st.info("📝 No trades logged yet. Signals will appear here when generated.")
        return
        
    st.markdown("### 📜 Live Trade Log")
    df_trades = pd.DataFrame(st.session_state.trade_log)
    
    # Add live P&L simulation (in real implementation, use live prices)
    if 'Current_Price' not in df_trades.columns:
        # Simulate current prices with some randomness
        np.random.seed(42)  # For consistent demo
        price_multipliers = np.random.uniform(0.8, 1.4, len(df_trades))
        df_trades['Current_Price'] = df_trades['LTP'] * price_multipliers
        
        # Calculate P&L (assuming 1 lot = 75 quantity)
        df_trades['Qty'] = 75
        df_trades['Unrealized_PL'] = (df_trades['Current_Price'] - df_trades['LTP']) * df_trades['Qty']
        
        # Add status based on P&L
        df_trades['Status'] = df_trades['Unrealized_PL'].apply(
            lambda x: '🟢 Profit' if x > 100 else '🔴 Loss' if x < -100 else '🟡 Breakeven'
        )
        
        # Add percentage returns
        df_trades['Return_%'] = ((df_trades['Current_Price'] - df_trades['LTP']) / df_trades['LTP'] * 100).round(2)
    
    # Style the dataframe with color coding
    def style_pnl_row(row):
        colors = []
        for col in row.index:
            if col == 'Unrealized_PL':
                if row[col] > 100:
                    colors.append('background-color: #d4edda; color: #155724; font-weight: bold')
                elif row[col] < -100:
                    colors.append('background-color: #f8d7da; color: #721c24; font-weight: bold')
                else:
                    colors.append('background-color: #fff3cd; color: #856404')
            elif col == 'Return_%':
                if row[col] > 5:
                    colors.append('color: #28a745; font-weight: bold')
                elif row[col] < -5:
                    colors.append('color: #dc3545; font-weight: bold')
                else:
                    colors.append('color: #ffc107')
            else:
                colors.append('')
        return colors
    
    # Display styled dataframe
    styled_trades = df_trades.style.apply(style_pnl_row, axis=1)
    st.dataframe(styled_trades, use_container_width=True)
    
    # Summary statistics in columns
    col1, col2, col3, col4 = st.columns(4)
    
    total_pl = df_trades['Unrealized_PL'].sum()
    winning_trades = len(df_trades[df_trades['Unrealized_PL'] > 0])
    total_trades = len(df_trades)
    win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0
    avg_return = df_trades['Return_%'].mean()
    
    with col1:
        st.metric("💰 Total P&L", f"₹{total_pl:,.0f}", 
                 delta=f"{total_pl:+,.0f}" if total_pl != 0 else None)
    
    with col2:
        st.metric("🎯 Win Rate", f"{win_rate:.1f}%", 
                 delta=f"{winning_trades}/{total_trades}")
    
    with col3:
        st.metric("📊 Avg Return", f"{avg_return:+.1f}%",
                 delta="Good" if avg_return > 0 else "Review")
    
    with col4:
        st.metric("📈 Total Trades", total_trades)

def plot_price_with_sr():
    """Enhanced price chart with support/resistance and volume"""
    price_df = st.session_state['price_data'].copy()
    
    if price_df.empty or price_df['Spot'].isnull().all():
        st.info("📈 Price chart will appear once data accumulates...")
        return
        
    # Ensure proper datetime conversion
    price_df['Time'] = pd.to_datetime(price_df['Time'], format='%H:%M:%S', errors='coerce')
    price_df = price_df.dropna(subset=['Time', 'Spot'])
    
    if price_df.empty:
        return
    
    # Get zones
    support_zone = st.session_state.get('support_zone', (None, None))
    resistance_zone = st.session_state.get('resistance_zone', (None, None))
    
    # Create subplot with secondary y-axis
    fig = make_subplots(
        rows=2, cols=1,
        row_heights=[0.8, 0.2],
        subplot_titles=('Nifty Spot Price with Support & Resistance', 'Volume Profile'),
        vertical_spacing=0.05
    )
    
    # Main price line
    fig.add_trace(
        go.Scatter(
            x=price_df['Time'], 
            y=price_df['Spot'], 
            mode='lines+markers', 
            name='Spot Price',
            line=dict(color='#1f77b4', width=3),
            hovertemplate='<b>%{y:.2f}</b><br>%{x}<extra></extra>'
        ),
        row=1, col=1
    )
    
    # Add support zone
    if all(support_zone) and None not in support_zone:
        # Support zone fill
        fig.add_shape(
            type="rect",
            xref="x", yref="y",
            x0=price_df['Time'].min(), x1=price_df['Time'].max(),
            y0=support_zone[0], y1=support_zone[1],
            fillcolor="rgba(40, 167, 69, 0.15)", 
            line=dict(width=0),
            layer="below",
            row=1, col=1
        )
        
        # Support lines
        for i, level in enumerate(support_zone):
            fig.add_hline(
                y=level,
                line=dict(color='#28a745', dash='dash' if i == 0 else 'dot', width=2),
                annotation_text=f"Support {level}",
                annotation_position="right",
                row=1, col=1
            )
    
    # Add resistance zone
    if all(resistance_zone) and None not in resistance_zone:
        # Resistance zone fill
        fig.add_shape(
            type="rect",
            xref="x", yref="y",
            x0=price_df['Time'].min(), x1=price_df['Time'].max(),
            y0=resistance_zone[0], y1=resistance_zone[1],
            fillcolor="rgba(220, 53, 69, 0.15)", 
            line=dict(width=0),
            layer="below",
            row=1, col=1
        )
        
        # Resistance lines
        for i, level in enumerate(resistance_zone):
            fig.add_hline(
                y=level,
                line=dict(color='#dc3545', dash='dash' if i == 0 else 'dot', width=2),
                annotation_text=f"Resistance {level}",
                annotation_position="right",
                row=1, col=1
            )
    
    # Add volume bars (simulated for demo)
    if len(price_df) > 1:
        volume_data = np.random.randint(1000, 10000, len(price_df))
        fig.add_trace(
            go.Bar(
                x=price_df['Time'],
                y=volume_data,
                name='Volume',
                marker_color='rgba(158, 158, 158, 0.6)',
                showlegend=False
            ),
            row=2, col=1
        )
    
    # Update layout with modern styling
    fig.update_layout(
        title={
            'text': "📈 Live Price Action Analysis",
            'x': 0.5,
            'xanchor': 'center',
            'font': {'size': 20, 'color': '#2c3e50'}
        },
        template="plotly_white",
        hovermode='x unified',
        showlegend=True,
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1
        ),
        margin=dict(l=50, r=50, t=100, b=50)
    )
    
    # Update axes
    fig.update_xaxes(title_text="Time", row=2, col=1)
    fig.update_yaxes(title_text="Price", row=1, col=1)
    fig.update_yaxes(title_text="Volume", row=2, col=1)
    
    st.plotly_chart(fig, use_container_width=True)

def display_call_log_book():
    """Enhanced call log book display"""
    st.markdown("### 📚 Expert Call Log")
    
    if not st.session_state.call_log_book:
        st.info("📞 Expert calls will be tracked here when generated.")
        
        # Add sample call entry form
        with st.expander("➕ Add Manual Call", expanded=False):
            col1, col2 = st.columns(2)
            
            with col1:
                call_type = st.selectbox("Type", ["CE", "PE"])
                strike = st.number_input("Strike", min_value=15000, max_value=30000, step=50)
                entry_price = st.number_input("Entry Price", min_value=1.0, step=0.5)
            
            with col2:
                target1 = st.number_input("Target 1", min_value=1.0, step=0.5)
                target2 = st.number_input("Target 2", min_value=1.0, step=0.5)
                stop_loss = st.number_input("Stop Loss", min_value=0.5, step=0.5)
            
            notes = st.text_area("Notes", placeholder="Reason for the call...")
            
            if st.button("📝 Add Call"):
                new_call = {
                    "Time": datetime.now(timezone("Asia/Kolkata")).strftime("%Y-%m-%d %H:%M:%S"),
                    "Type": call_type,
                    "Strike": strike,
                    "Entry": entry_price,
                    "Targets": {"T1": target1, "T2": target2},
                    "Stoploss": stop_loss,
                    "Status": "Active",
                    "Notes": notes
                }
                st.session_state.call_log_book.append(new_call)
                st.success("✅ Call added to log book!")
                st.experimental_rerun()
        
        return
    
    # Display existing calls
    df_log = pd.DataFrame(st.session_state.call_log_book)
    
    # Style the call log
    def style_call_status(row):
        colors = []
        for col in row.index:
            if col == 'Status':
                if row[col] == 'Hit Target':
                    colors.append('background-color: #d4edda; color: #155724; font-weight: bold')
                elif row[col] == 'Hit Stoploss':
                    colors.append('background-color: #f8d7da; color: #721c24; font-weight: bold')
                elif row[col] == 'Active':
                    colors.append('background-color: #d1ecf1; color: #0c5460; font-weight: bold')
                else:
                    colors.append('')
            else:
                colors.append('')
        return colors
    
    styled_log = df_log.style.apply(style_call_status, axis=1)
    st.dataframe(styled_log, use_container_width=True)
    
    # Call log statistics
    col1, col2, col3 = st.columns(3)
    
    active_calls = len(df_log[df_log['Status'] == 'Active'])
    hit_targets = len(df_log[df_log['Status'] == 'Hit Target'])
    hit_sl = len(df_log[df_log['Status'] == 'Hit Stoploss'])
    
    with col1:
        st.metric("🟢 Active Calls", active_calls)
    with col2:
        st.metric("🎯 Targets Hit", hit_targets)
    with col3:
        st.metric("🛑 Stop Loss Hit", hit_sl)
    
    # Download options
    col1, col2 = st.columns(2)
    with col1:
        if st.button("📥 Download CSV", use_container_width=True):
            csv_data = df_log.to_csv(index=False)
            st.download_button(
                label="💾 Download Call Log",
                data=csv_data,
                file_name=f"call_log_{datetime.now().strftime('%Y%m%d')}.csv",
                mime="text/csv"
            )
    
    with col2:
        if st.button("🔄 Refresh Status", use_container_width=True):
            st.info("Call status will auto-update based on current prices")

def create_export_data(df_summary, trade_log, spot_price):
    """Enhanced export data creation with multiple sheets"""
    output = io.BytesIO()
    
    try:
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            # Option chain summary
            df_summary.to_excel(writer, sheet_name='Option_Chain_Summary', index=False)
            
            # Trade log
            if trade_log:
                pd.DataFrame(trade_log).to_excel(writer, sheet_name='Trade_Log', index=False)
            
            # Price data
            if not st.session_state.price_data.empty:
                st.session_state.price_data.to_excel(writer, sheet_name='Price_Data', index=False)
            
            # Call log book
            if st.session_state.call_log_book:
                pd.DataFrame(st.session_state.call_log_book).to_excel(writer, sheet_name='Call_Log', index=False)
            
            # Summary statistics
            summary_stats = {
                'Metric': ['Spot Price', 'Total Trades', 'Active Calls', 'Export Time'],
                'Value': [
                    spot_price,
                    len(trade_log) if trade_log else 0,
                    len(st.session_state.call_log_book),
                    datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                ]
            }
            pd.DataFrame(summary_stats).to_excel(writer, sheet_name='Summary', index=False)
    
    except ImportError:
        st.error("❌ Excel export requires openpyxl. Please install: `pip install openpyxl`")
        return None, None
    except Exception as e:
        st.error(f"❌ Export failed: {str(e)}")
        return None, None
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"nifty_analysis_{timestamp}.xlsx"
    
    return output.getvalue(), filename

def handle_export_data(df_summary, spot_price):
    """Enhanced export data handling with progress indicator"""
    if st.session_state.get('export_data', False):
        try:
            with st.spinner("📊 Preparing comprehensive Excel report..."):
                excel_data, filename = create_export_data(
                    df_summary, 
                    st.session_state.trade_log, 
                    spot_price
                )
                
                if excel_data:
                    st.download_button(
                        label="📥 Download Complete Analysis Report",
                        data=excel_data,
                        file_name=filename,
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        use_container_width=True
                    )
                    st.success("✅ Excel report ready! Click download button above.")
                    
                    # Show what's included
                    with st.expander("📋 Report Contents", expanded=False):
                        st.markdown("""
                        **Your Excel report includes:**
                        - 📊 Option Chain Summary
                        - 📜 Trade Log with P&L
                        - 📈 Price Action Data  
                        - 📚 Call Log Book
                        - 📋 Summary Statistics
                        """)
                
                st.session_state.export_data = False
                
        except Exception as e:
            st.error(f"❌ Export failed: {str(e)}")
            st.session_state.export_data = False

def auto_update_call_log(current_price):
    """Auto update call log with enhanced logic"""
    if not st.session_state.call_log_book:
        return
    
    updated_count = 0
    
    for call in st.session_state.call_log_book:
        if call.get("Status") != "Active":
            continue
            
        strike = call.get("Strike", 0)
        call_type = call.get("Type", "")
        targets = call.get("Targets", {})
        stop_loss = call.get("Stoploss", 0)
        
        # Simple logic for demo (in reality, use option prices)
        price_diff = abs(current_price - strike)
        
        if call_type == "CE":
            if current_price >= strike + 50:  # Simplified target logic
                call["Status"] = "Hit Target"
                call["Exit_Time"] = datetime.now(timezone("Asia/Kolkata")).strftime("%Y-%m-%d %H:%M:%S")
                call["Exit_Price"] = current_price
                updated_count += 1
            elif current_price <= strike - 100:  # Simplified SL logic
                call["Status"] = "Hit Stoploss"
                call["Exit_Time"] = datetime.now(timezone("Asia/Kolkata")).strftime("%Y-%m-%d %H:%M:%S")
                call["Exit_Price"] = current_price
                updated_count += 1
                
        elif call_type == "PE":
            if current_price <= strike - 50:  # Simplified target logic
                call["Status"] = "Hit Target"
                call["Exit_Time"] = datetime.now(timezone("Asia/Kolkata")).strftime("%Y-%m-%d %H:%M:%S")
                call["Exit_Price"] = current_price
                updated_count += 1
            elif current_price >= strike + 100:  # Simplified SL logic
                call["Status"] = "Hit Stoploss"
                call["Exit_Time"] = datetime.now(timezone("Asia/Kolkata")).strftime("%Y-%m-%d %H:%M:%S")
                call["Exit_Price"] = current_price
                updated_count += 1
    
    if updated_count > 0:
        st.info(f"🔄 Updated {updated_count} call(s) status based on current price")