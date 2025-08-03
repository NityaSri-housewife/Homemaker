import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime, timedelta
from pytz import timezone
import math

class TradeSimulator:
    def __init__(self):
        self.initialize_session_state()
    
    def initialize_session_state(self):
        """Initialize simulator session state"""
        if 'simulated_trades' not in st.session_state:
            st.session_state.simulated_trades = []
        if 'simulation_results' not in st.session_state:
            st.session_state.simulation_results = {}
    
    def calculate_option_price_movement(self, spot_move, strike, option_type, days_to_expiry, iv=20):
        """Simulate option price based on spot movement (simplified Black-Scholes)"""
        try:
            # Simplified option pricing for simulation
            S = 24000 + spot_move  # New spot price
            K = strike
            T = max(days_to_expiry / 365, 0.001)  # Time to expiry
            r = 0.06  # Risk-free rate
            sigma = iv / 100  # Implied volatility
            
            # Calculate d1 and d2
            d1 = (math.log(S / K) + (r + 0.5 * sigma**2) * T) / (sigma * math.sqrt(T))
            d2 = d1 - sigma * math.sqrt(T)
            
            # Black-Scholes formula
            if option_type == 'CE':
                from scipy.stats import norm
                option_price = S * norm.cdf(d1) - K * math.exp(-r * T) * norm.cdf(d2)
            else:  # PE
                from scipy.stats import norm
                option_price = K * math.exp(-r * T) * norm.cdf(-d2) - S * norm.cdf(-d1)
            
            return max(option_price, 0.05)  # Minimum price of 0.05
            
        except:
            # Fallback to simple linear approximation
            if option_type == 'CE':
                return max(spot_move * 0.5, 0.05) if spot_move > 0 else max(-spot_move * 0.3, 0.05)
            else:
                return max(-spot_move * 0.5, 0.05) if spot_move < 0 else max(spot_move * 0.3, 0.05)
    
    def simulate_trade_outcome(self, trade_data, spot_movements):
        """Simulate trade outcome for different spot movements"""
        results = []
        
        entry_price = trade_data['entry_price']
        target = trade_data['target']
        stop_loss = trade_data['stop_loss']
        strike = trade_data['strike']
        option_type = trade_data['option_type']
        quantity = trade_data['quantity']
        days_to_expiry = trade_data.get('days_to_expiry', 7)
        
        for spot_move in spot_movements:
            # Calculate new option price
            new_price = self.calculate_option_price_movement(
                spot_move, strike, option_type, days_to_expiry
            )
            
            # Determine trade outcome
            if new_price >= target:
                exit_price = target
                outcome = "Target Hit"
                pnl = (exit_price - entry_price) * quantity
            elif new_price <= stop_loss:
                exit_price = stop_loss
                outcome = "Stop Loss Hit"
                pnl = (exit_price - entry_price) * quantity
            else:
                exit_price = new_price
                outcome = "Open"
                pnl = (exit_price - entry_price) * quantity
            
            results.append({
                'spot_move': spot_move,
                'new_spot': 24000 + spot_move,  # Assuming current spot is 24000
                'exit_price': exit_price,
                'pnl': pnl,
                'pnl_percent': (pnl / (entry_price * quantity)) * 100,
                'outcome': outcome
            })
        
        return results
    
    def render_trade_simulator_ui(self):
        """Render the main trade simulator interface"""
        st.markdown("## 🚀 Trade Simulator")
        st.markdown("Simulate trade outcomes and visualize P&L scenarios")
        
        # Create tabs for different simulator features
        tab1, tab2, tab3 = st.tabs(["🎯 Single Trade Simulator", "📊 Portfolio Simulator", "📈 Historical Analysis"])
        
        with tab1:
            self.render_single_trade_simulator()
        
        with tab2:
            self.render_portfolio_simulator()
        
        with tab3:
            self.render_historical_analysis()
    
    def render_single_trade_simulator(self):
        """Render single trade simulator"""
        st.markdown("### 🎯 Single Trade Outcome Simulator")
        
        # Input form
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("**📝 Trade Details**")
            option_type = st.selectbox(
                "Option Type", 
                ["CE", "PE"],
                help="Call or Put option"
            )
            strike = st.number_input(
                "Strike Price", 
                min_value=15000, 
                max_value=30000, 
                value=24000, 
                step=50
            )
            entry_price = st.number_input(
                "Entry Price (₹)", 
                min_value=1.0, 
                value=100.0, 
                step=0.5
            )
            quantity = st.number_input(
                "Quantity", 
                min_value=1, 
                value=75, 
                step=25,
                help="Number of contracts (default: 1 lot = 75)"
            )
        
        with col2:
            st.markdown("**🎯 Risk Management**")
            target = st.number_input(
                "Target Price (₹)", 
                min_value=entry_price * 1.1, 
                value=entry_price * 1.5, 
                step=0.5
            )
            stop_loss = st.number_input(
                "Stop Loss (₹)", 
                min_value=1.0, 
                max_value=entry_price * 0.9, 
                value=entry_price * 0.7, 
                step=0.5
            )
            days_to_expiry = st.number_input(
                "Days to Expiry", 
                min_value=1, 
                max_value=30, 
                value=7
            )
            current_spot = st.number_input(
                "Current Spot", 
                min_value=15000, 
                max_value=30000, 
                value=24000, 
                step=10
            )
        
        # Simulation parameters
        st.markdown("**📊 Simulation Parameters**")
        col1, col2 = st.columns(2)
        
        with col1:
            spot_range = st.slider(
                "Spot Movement Range (±points)", 
                min_value=100, 
                max_value=1000, 
                value=500, 
                step=50
            )
        
        with col2:
            simulation_points = st.slider(
                "Simulation Points", 
                min_value=20, 
                max_value=100, 
                value=50
            )
        
        # Run simulation button
        if st.button("🚀 Run Simulation", type="primary", use_container_width=True):
            # Prepare trade data
            trade_data = {
                'option_type': option_type,
                'strike': strike,
                'entry_price': entry_price,
                'target': target,
                'stop_loss': stop_loss,
                'quantity': quantity,
                'days_to_expiry': days_to_expiry,
                'current_spot': current_spot
            }
            
            # Generate spot movements
            spot_movements = np.linspace(-spot_range, spot_range, simulation_points)
            
            # Run simulation
            results = self.simulate_trade_outcome(trade_data, spot_movements)
            
            # Display results
            self.display_simulation_results(trade_data, results)
    
    def display_simulation_results(self, trade_data, results):
        """Display simulation results with charts and statistics"""
        df_results = pd.DataFrame(results)
        
        # Summary statistics
        st.markdown("### 📊 Simulation Results")
        
        col1, col2, col3, col4 = st.columns(4)
        
        max_profit = df_results['pnl'].max()
        max_loss = df_results['pnl'].min()
        profitable_scenarios = len(df_results[df_results['pnl'] > 0])
        total_scenarios = len(df_results)
        
        with col1:
            st.metric("💰 Max Profit", f"₹{max_profit:,.0f}")
        with col2:
            st.metric("📉 Max Loss", f"₹{max_loss:,.0f}")
        with col3:
            st.metric("🎯 Win Rate", f"{(profitable_scenarios/total_scenarios)*100:.1f}%")
        with col4:
            expected_pnl = df_results['pnl'].mean()
            st.metric("📈 Expected P&L", f"₹{expected_pnl:,.0f}")
        
        # P&L Chart
        self.plot_pnl_chart(df_results, trade_data)
        
        # Outcome distribution
        self.plot_outcome_distribution(df_results)
        
        # Detailed results table
        with st.expander("📋 Detailed Results", expanded=False):
            st.dataframe(
                df_results.style.format({
                    'new_spot': '{:.0f}',
                    'exit_price': '{:.2f}',
                    'pnl': '₹{:,.0f}',
                    'pnl_percent': '{:+.1f}%'
                }).background_gradient(subset=['pnl'], cmap='RdYlGn'),
                use_container_width=True
            )
    
    def plot_pnl_chart(self, df_results, trade_data):
        """Plot P&L vs Spot Movement chart"""
        fig = make_subplots(
            rows=2, cols=1,
            row_heights=[0.7, 0.3],
            subplot_titles=('P&L vs Spot Movement', 'Outcome Distribution'),
            vertical_spacing=0.1
        )
        
        # Main P&L chart
        colors = ['red' if pnl < 0 else 'green' if pnl > 0 else 'gray' for pnl in df_results['pnl']]
        
        fig.add_trace(
            go.Scatter(
                x=df_results['spot_move'],
                y=df_results['pnl'],
                mode='lines+markers',
                name='P&L',
                line=dict(color='blue', width=2),
                marker=dict(color=colors, size=6),
                hovertemplate='<b>Spot Move:</b> %{x:+.0f}<br>' +
                            '<b>P&L:</b> ₹%{y:,.0f}<br>' +
                            '<extra></extra>'
            ),
            row=1, col=1
        )
        
        # Add break-even line
        fig.add_hline(y=0, line_dash="dash", line_color="black", 
                     annotation_text="Break Even", row=1, col=1)
        
        # Add target and stop loss indicators
        target_pnl = (trade_data['target'] - trade_data['entry_price']) * trade_data['quantity']
        sl_pnl = (trade_data['stop_loss'] - trade_data['entry_price']) * trade_data['quantity']
        
        fig.add_hline(y=target_pnl, line_dash="dot", line_color="green", 
                     annotation_text=f"Target: ₹{target_pnl:,.0f}", row=1, col=1)
        fig.add_hline(y=sl_pnl, line_dash="dot", line_color="red", 
                     annotation_text=f"SL: ₹{sl_pnl:,.0f}", row=1, col=1)
        
        # Outcome distribution histogram
        outcomes = df_results['outcome'].value_counts()
        fig.add_trace(
            go.Bar(
                x=outcomes.index,
                y=outcomes.values,
                name='Outcomes',
                marker_color=['green', 'red', 'gray'],
                showlegend=False
            ),
            row=2, col=1
        )
        
        fig.update_layout(
            title=f"Trade Simulation: {trade_data['option_type']} {trade_data['strike']} @ ₹{trade_data['entry_price']}",
            template="plotly_white",
            height=600
        )
        
        fig.update_xaxes(title_text="Spot Movement (Points)", row=1, col=1)
        fig.update_yaxes(title_text="P&L (₹)", row=1, col=1)
        fig.update_xaxes(title_text="Outcome", row=2, col=1)
        fig.update_yaxes(title_text="Count", row=2, col=1)
        
        st.plotly_chart(fig, use_container_width=True)
    
    def plot_outcome_distribution(self, df_results):
        """Plot outcome distribution pie chart"""
        outcomes = df_results['outcome'].value_counts()
        
        fig = go.Figure(data=[go.Pie(
            labels=outcomes.index,
            values=outcomes.values,
            hole=0.4,
            marker_colors=['#28a745', '#dc3545', '#6c757d']
        )])
        
        fig.update_layout(
            title="Outcome Distribution",
            height=400,
            showlegend=True
        )
        
        st.plotly_chart(fig, use_container_width=True)
    
    def render_portfolio_simulator(self):
        """Render portfolio simulator for multiple trades"""
        st.markdown("### 📊 Portfolio Simulator")
        st.markdown("Simulate cumulative P&L for all logged trades")
        
        if not st.session_state.trade_log:
            st.info("📝 No trades in log. Generate some signals first!")
            return
        
        # Portfolio simulation settings
        col1, col2 = st.columns(2)
        
        with col1:
            simulation_days = st.number_input(
                "Simulation Days", 
                min_value=1, 
                max_value=30, 
                value=7
            )
            spot_volatility = st.slider(
                "Daily Volatility (%)", 
                min_value=0.5, 
                max_value=5.0, 
                value=1.5, 
                step=0.1
            )
        
        with col2:
            num_simulations = st.number_input(
                "Number of Simulations", 
                min_value=100, 
                max_value=1000, 
                value=500, 
                step=100
            )
            initial_capital = st.number_input(
                "Initial Capital (₹)", 
                min_value=10000, 
                value=100000, 
                step=10000
            )
        
        if st.button("📊 Run Portfolio Simulation", type="primary"):
            self.run_portfolio_simulation(
                simulation_days, spot_volatility, num_simulations, initial_capital
            )
    
    def run_portfolio_simulation(self, days, volatility, num_sims, initial_capital):
        """Run Monte Carlo simulation for portfolio"""
        st.info("🔄 Running Monte Carlo simulation...")
        
        # Convert trade log to portfolio
        trades_df = pd.DataFrame(st.session_state.trade_log)
        
        # Simulate price paths
        simulation_results = []
        
        for sim in range(num_sims):
            portfolio_value = initial_capital
            daily_returns = []
            
            # Generate random price path
            daily_changes = np.random.normal(0, volatility/100, days)
            
            # Calculate portfolio performance
            for day in range(days):
                day_pnl = 0
                
                # Apply daily change to each trade
                for _, trade in trades_df.iterrows():
                    spot_change = daily_changes[day] * 24000  # Assuming spot around 24000
                    
                    # Simplified P&L calculation
                    if trade['Type'] == 'CE':
                        trade_pnl = max(spot_change * 0.5, -trade['LTP'] * 25) * 75  # 75 qty
                    else:
                        trade_pnl = max(-spot_change * 0.5, -trade['LTP'] * 25) * 75
                    
                    day_pnl += trade_pnl
                
                portfolio_value += day_pnl
                daily_returns.append(portfolio_value)
            
            simulation_results.append(daily_returns)
        
        # Display results
        self.display_portfolio_results(simulation_results, initial_capital, days)
    
    def display_portfolio_results(self, simulation_results, initial_capital, days):
        """Display portfolio simulation results"""
        df_sims = pd.DataFrame(simulation_results).T
        
        # Calculate statistics
        final_values = df_sims.iloc[-1]
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            median_return = ((final_values.median() - initial_capital) / initial_capital) * 100
            st.metric("📈 Median Return", f"{median_return:+.1f}%")
        
        with col2:
            worst_case = ((final_values.min() - initial_capital) / initial_capital) * 100
            st.metric("📉 Worst Case", f"{worst_case:+.1f}%")
        
        with col3:
            best_case = ((final_values.max() - initial_capital) / initial_capital) * 100
            st.metric("🚀 Best Case", f"{best_case:+.1f}%")
        
        with col4:
            profitable_sims = len(final_values[final_values > initial_capital])
            win_rate = (profitable_sims / len(final_values)) * 100
            st.metric("🎯 Success Rate", f"{win_rate:.1f}%")
        
        # Plot simulation paths
        fig = go.Figure()
        
        # Add sample paths (max 50 for performance)
        sample_size = min(50, df_sims.shape[1])
        for i in range(sample_size):
            fig.add_trace(
                go.Scatter(
                    x=list(range(days)),
                    y=df_sims.iloc[:, i],
                    mode='lines',
                    line=dict(color='lightblue', width=1),
                    showlegend=False,
                    hoverinfo='skip'
                )
            )
        
        # Add percentiles
        percentiles = [10, 25, 50, 75, 90]
        colors = ['red', 'orange', 'blue', 'orange', 'red']
        names = ['10th', '25th', '50th (Median)', '75th', '90th']
        
        for i, (p, color, name) in enumerate(zip(percentiles, colors, names)):
            fig.add_trace(
                go.Scatter(
                    x=list(range(days)),
                    y=df_sims.quantile(p/100, axis=1),
                    mode='lines',
                    line=dict(color=color, width=3),
                    name=f'{name} percentile'
                )
            )
        
        fig.update_layout(
            title="Portfolio Value Simulation Paths",
            xaxis_title="Days",
            yaxis_title="Portfolio Value (₹)",
            template="plotly_white",
            height=500
        )
        
        st.plotly_chart(fig, use_container_width=True)
    
    def render_historical_analysis(self):
        """Render historical trade analysis"""
        st.markdown("### 📈 Historical Performance Analysis")
        
        if not st.session_state.trade_log:
            st.info("📝 No historical trades to analyze!")
            return
        
        trades_df = pd.DataFrame(st.session_state.trade_log)
        
        # Add some analysis here
        st.markdown("**🔍 Trade Statistics**")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            total_trades = len(trades_df)
            st.metric("Total Trades", total_trades)
        
        with col2:
            ce_trades = len(trades_df[trades_df['Type'] == 'CE'])
            st.metric("CE Trades", ce_trades)
        
        with col3:
            pe_trades = len(trades_df[trades_df['Type'] == 'PE'])
            st.metric("PE Trades", pe_trades)
        
        # Trade distribution chart
        if len(trades_df) > 0:
            fig = go.Figure(data=[
                go.Bar(
                    x=['CE', 'PE'],
                    y=[ce_trades, pe_trades],
                    marker_color=['green', 'red']
                )
            ])
            
            fig.update_layout(
                title="Trade Type Distribution",
                template="plotly_white",
                height=300
            )
            
            st.plotly_chart(fig, use_container_width=True)

# Main function to render simulator
def render_trade_simulator():
    """Main function to render trade simulator"""
    simulator = TradeSimulator()
    simulator.render_trade_simulator_ui()