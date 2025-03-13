from flask import Flask, jsonify
from dash import Dash, html, dcc
import dash_bootstrap_components as dbc
from dash.dependencies import Input, Output, State
import plotly.graph_objs as go
from data_fetcher import FinancialDataFetcher
import pandas as pd
from datetime import datetime
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize Flask and Dash with a theme
server = Flask(__name__)
app = Dash(
    __name__, 
    server=server, 
    external_stylesheets=[dbc.themes.FLATLY],  # Changed theme to FLATLY 
    meta_tags=[{"name": "viewport", "content": "width=device-width, initial-scale=1"}]  # Responsive meta tag
)

# Initialize data fetcher
data_fetcher = FinancialDataFetcher()

# Custom CSS
app.index_string = '''
<!DOCTYPE html>
<html>
    <head>
        {%metas%}
        <title>Financial Insights Dashboard</title>
        {%favicon%}
        {%css%}
        <style>
            .nav-pills .nav-link.active {
                background-color: #2C3E50;
            }
            .card {
                box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
                transition: all 0.3s ease;
            }
            .card:hover {
                transform: translateY(-5px);
                box-shadow: 0 8px 15px rgba(0, 0, 0, 0.1);
            }
            .main-title {
                color: #2C3E50;
                font-weight: 700;
                letter-spacing: 0.5px;
            }
            .metric-value {
                font-size: 24px;
                font-weight: 500;
            }
            .metric-label {
                color: #7b8a8b;
                font-size: 14px;
            }
            .footer {
                margin-top: 30px;
                padding: 20px 0;
                border-top: 1px solid #ecf0f1;
                text-align: center;
                color: #95a5a6;
                font-size: 14px;
            }
        </style>
    </head>
    <body>
        {%app_entry%}
        <footer>
            {%config%}
            {%scripts%}
            {%renderer%}
        </footer>
    </body>
</html>
'''

# Define the layout with improved UI
app.layout = dbc.Container([
    dbc.Row([
        dbc.Col([
            html.Div([
               html.H1("Financial Insights Dashboard", className="main-title")
], className="d-flex justify-content-center align-items-center my-4")
        ])
    ]),
    
    dbc.Row([
        dbc.Col(lg=3, md=4, sm=12, children=[
            dbc.Card([
                dbc.CardHeader("Controls", className="bg-primary text-white"),
                dbc.CardBody([
                    html.P("Select Stock Symbol", className="mb-1"),
                    dcc.Dropdown(
                        id='stock-selector',
                        options=[{'label': symbol, 'value': symbol} 
                                for symbol in data_fetcher.default_symbols],
                        value=data_fetcher.default_symbols[0],
                        className="mb-3"
                    ),
                    html.P("Select Time Range", className="mb-1 mt-3"),
                    dbc.RadioItems(
                        id='time-range',
                        options=[
                            
                            {'label': '3 Months', 'value': '3M'},
                            {'label': '6 Months', 'value': '6M'},
                            {'label': '1 Year', 'value': '1Y'},
                            {'label': 'All Time', 'value': 'ALL'}
                        ],
                        value='3M',
                        inline=True,
                        className="mb-3"
                    ),
                    dbc.Button("Refresh Data", id="refresh-button", color="primary", className="mt-2 w-100")
                ])
            ], className="mb-4"),
            
            dbc.Card([
                dbc.CardHeader("Summary Metrics", className="bg-primary text-white"),
                dbc.CardBody(id='metrics-card', children=[
                    dbc.Spinner(color="primary")
                ])
            ], className="mb-4"),
            
            html.Div(id='error-message', className="alert alert-danger d-none")
        ]),
        
        dbc.Col(lg=9, md=8, sm=12, children=[
            dbc.Card([
                dbc.CardHeader(
                    dbc.Tabs([
                        dbc.Tab(label="Price Chart", tab_id="price-tab", activeTabClassName="fw-bold"),
                        dbc.Tab(label="Volume", tab_id="volume-tab", activeTabClassName="fw-bold"),
                        dbc.Tab(label="Performance", tab_id="performance-tab", activeTabClassName="fw-bold")
                    ], id="chart-tabs", active_tab="price-tab")
                ),
                dbc.CardBody([
                    dbc.Spinner(
                        dcc.Graph(id='main-chart', style={"height": "60vh"}),
                        color="primary",
                        type="grow"
                    )
                ])
            ], className="mb-4"),
            
            dbc.Row([
                dbc.Col(md=6, children=[
                    dbc.Card([
                        dbc.CardHeader("Moving Averages", className="bg-info text-white"),
                        dbc.CardBody([
                            dcc.Graph(id='ma-chart', style={"height": "30vh"})
                        ])
                    ])
                ]),
                dbc.Col(md=6, children=[
                    dbc.Card([
                        dbc.CardHeader("Trading Volume", className="bg-info text-white"),
                        dbc.CardBody([
                            dcc.Graph(id='volume-chart', style={"height": "30vh"})
                        ])
                    ])
                ])
            ])
        ])
    ]),
    
    dbc.Row([
        dbc.Col([
            html.Div(className="footer", children=[
                html.P("Financial Insights Dashboard © 2025"),
                html.P("Data updates every 5 minutes")
            ])
        ])
    ]),
    
    dcc.Interval(
        id='interval-component',
        interval=300000,  # Update every 5 minutes
        n_intervals=0
    )
], fluid=True, className="p-4 bg-light")

def create_empty_figure(message="No data available"):
    return {
        'data': [],
        'layout': {
            'xaxis': {'showgrid': False, 'zeroline': False},
            'yaxis': {'showgrid': False, 'zeroline': False},
            'annotations': [{
                'text': message,
                'xref': 'paper',
                'yref': 'paper',
                'showarrow': False,
                'font': {'size': 20}
            }]
        }
    }

@app.callback(
    [Output('main-chart', 'figure'),
     Output('ma-chart', 'figure'),
     Output('volume-chart', 'figure'),
     Output('metrics-card', 'children'),
     Output('error-message', 'children'),
     Output('error-message', 'className')],
    [Input('chart-tabs', 'active_tab'),
     Input('stock-selector', 'value'),
     Input('time-range', 'value'),
     Input('interval-component', 'n_intervals'),
     Input('refresh-button', 'n_clicks')]
)
def update_charts(active_tab, selected_symbol, time_range, n_intervals, n_clicks):
    try:
        # Fetch data from MongoDB
        try:
            collection = data_fetcher.db['stock_data']
            data = list(collection.find({'Symbol': selected_symbol}).sort('Date', 1))
        except Exception as db_error:
            logger.error(f"Database error: {str(db_error)}")
            return [create_empty_figure(f"Database error: Unable to fetch {selected_symbol} data")] * 3, \
                   [html.P("Database connection error", className="text-danger")], \
                   f"Database error: {str(db_error)}", "alert alert-danger"
        
        if not data:
            logger.warning(f"No data found for symbol {selected_symbol}")
            # Trigger a new data fetch
            try:
                data_fetcher.fetch_stock_data([selected_symbol])
            except Exception as fetch_error:
                logger.error(f"Error fetching data: {str(fetch_error)}")
            
            return [create_empty_figure(f"No data available for {selected_symbol}")] * 3, \
                   [html.P("No data available", className="text-danger")], \
                   f"No data available for {selected_symbol}. Trying to fetch new data...", \
                   "alert alert-warning"
        
        df = pd.DataFrame(data)
        
        # Ensure Date is in datetime format
        df['Date'] = pd.to_datetime(df['Date'])
        
        # Filter based on time range
        if time_range != 'ALL':
            months = int(time_range[:-1])
            cutoff_date = pd.Timestamp.now() - pd.DateOffset(months=months)
            df = df[df['Date'] >= cutoff_date]
        
        # Calculate moving averages if they don't exist
        if 'SMA_20' not in df.columns:
            df['SMA_20'] = df['Close'].rolling(window=20).mean()
        
        if 'SMA_50' not in df.columns:
            df['SMA_50'] = df['Close'].rolling(window=50).mean()
        
        # Create main chart
        if active_tab == "price-tab":
            main_fig = go.Figure()
            
            main_fig.add_trace(go.Candlestick(
                x=df['Date'],
                open=df['Open'],
                high=df['High'],
                low=df['Low'],
                close=df['Close'],
                name='OHLC'
            ))
            
            main_fig.update_layout(
                title=f'{selected_symbol} Stock Price',
                xaxis_title='Date',
                yaxis_title='Price ($)',
                template='plotly_white',
                hovermode='x unified',
                margin=dict(l=40, r=40, t=40, b=40)
            )
        
        elif active_tab == "volume-tab":
            main_fig = go.Figure()
            
            main_fig.add_trace(go.Bar(
                x=df['Date'],
                y=df['Volume'],
                name='Volume',
                marker={'color': 'rgba(58, 71, 80, 0.6)'}
            ))
            
            main_fig.update_layout(
                title=f'{selected_symbol} Trading Volume',
                xaxis_title='Date',
                yaxis_title='Volume',
                template='plotly_white',
                hovermode='x unified',
                margin=dict(l=40, r=40, t=40, b=40)
            )
        
        elif active_tab == "performance-tab":
            # Calculate % change from first price
            first_close = df.iloc[0]['Close']
            df['PercentChange'] = ((df['Close'] - first_close) / first_close) * 100
            
            main_fig = go.Figure()
            
            main_fig.add_trace(go.Scatter(
                x=df['Date'],
                y=df['PercentChange'],
                mode='lines',
                name='Performance',
                line=dict(color='green', width=2)
            ))
            
            main_fig.update_layout(
                title=f'{selected_symbol} Performance',
                xaxis_title='Date',
                yaxis_title='Percent Change (%)',
                template='plotly_white',
                hovermode='x unified',
                margin=dict(l=40, r=40, t=40, b=40)
            )
        
        # Create MA chart
        ma_fig = go.Figure()
        
        ma_fig.add_trace(go.Scatter(
            x=df['Date'],
            y=df['Close'],
            mode='lines',
            name='Close',
            line=dict(color='black', width=1)
        ))
        
        # Only add the MA traces if we have enough data
        if not df['SMA_20'].isna().all():
            ma_fig.add_trace(go.Scatter(
                x=df['Date'],
                y=df['SMA_20'],
                mode='lines',
                name='20 Day MA',
                line=dict(color='orange', width=2)
            ))
        
        if not df['SMA_50'].isna().all():
            ma_fig.add_trace(go.Scatter(
                x=df['Date'],
                y=df['SMA_50'],
                mode='lines',
                name='50 Day MA',
                line=dict(color='blue', width=2)
            ))
        
        ma_fig.update_layout(
            title='Moving Averages',
            xaxis_title='Date',
            yaxis_title='Price ($)',
            template='plotly_white',
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
            margin=dict(l=40, r=40, t=40, b=40)
        )
        
        # Create volume chart
        volume_fig = go.Figure()
        
        volume_fig.add_trace(go.Bar(
            x=df['Date'],
            y=df['Volume'],
            name='Volume',
            marker={'color': 'rgba(58, 71, 80, 0.6)'}
        ))
        
        volume_fig.update_layout(
            title='Trading Volume',
            xaxis_title='Date',
            yaxis_title='Volume',
            template='plotly_white',
            margin=dict(l=40, r=40, t=40, b=40)
        )
        
        # Get summary metrics with error handling
        try:
            metrics = data_fetcher.get_summary_metrics([selected_symbol])
            if selected_symbol not in metrics:
                raise KeyError(f"No metrics found for {selected_symbol}")
                
            stock_metrics = metrics[selected_symbol]
            
            # Determine color for monthly return
            monthly_return = float(stock_metrics['monthly_return'])
            return_color = "success" if monthly_return >= 0 else "danger"
            
            metrics_card = [
                dbc.Row([
                    dbc.Col([
                        html.P("Latest Price", className="metric-label mb-0"),
                        html.P(f"${stock_metrics['latest_price']}", className="metric-value")
                    ], width=6),
                    dbc.Col([
                        html.P("Monthly Return", className="metric-label mb-0"),
                        html.P(f"{stock_metrics['monthly_return']}%", 
                               className=f"metric-value text-{return_color}")
                    ], width=6)
                ], className="mb-3"),
                dbc.Row([
                    dbc.Col([
                        html.P("Volatility", className="metric-label mb-0"),
                        html.P(f"{stock_metrics['volatility']}%", className="metric-value")
                    ], width=6),
                    dbc.Col([
                        html.P("52-Week High", className="metric-label mb-0"),
                        html.P(f"${df['High'].max():.2f}", className="metric-value")
                    ], width=6)
                ], className="mb-3"),
                dbc.Row([
                    dbc.Col([
                        html.P("Last Updated", className="metric-label mb-0"),
                        html.P(f"{stock_metrics['last_updated']}", 
                               className="text-muted", style={"fontSize": "12px"})
                    ], width=12)
                ])
            ]
        except Exception as metrics_error:
            logger.error(f"Error calculating metrics: {str(metrics_error)}")
            metrics_card = [
                html.H5("Summary Metrics Unavailable", className="text-danger"),
                html.P(f"Error: {str(metrics_error)}")
            ]
        
        return main_fig, ma_fig, volume_fig, metrics_card, "", "alert alert-danger d-none"
        
    except Exception as e:
        logger.error(f"Error updating charts: {str(e)}")
        return [create_empty_figure("Error: Unable to load data")] * 3, \
               [html.P("Metrics unavailable", className="text-danger")], \
               f"Error: {str(e)}", "alert alert-danger"

@server.route('/api/summary')
def get_summary():
    """API endpoint for summary metrics"""
    try:
        metrics = data_fetcher.get_summary_metrics()
        return jsonify(metrics)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    # Initial data fetch
    try:
        logger.info("Performing initial data fetch...")
        data_fetcher.fetch_stock_data()
        logger.info("Initial data fetch completed successfully")
    except Exception as e:
        logger.error(f"Error during initial data fetch: {str(e)}")
    
    # Run the server
    app.run_server(debug=True, port=8050)