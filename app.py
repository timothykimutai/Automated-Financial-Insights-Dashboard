from flask import Flask, jsonify
from dash import Dash, html, dcc
import dash_bootstrap_components as dbc
from dash.dependencies import Input, Output
import plotly.graph_objs as go
from data_fetcher import FinancialDataFetcher
import pandas as pd
from datetime import datetime
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize Flask and Dash
server = Flask(__name__)
app = Dash(__name__, server=server, external_stylesheets=[dbc.themes.BOOTSTRAP])

# Initialize data fetcher
data_fetcher = FinancialDataFetcher()

# Define the layout
app.layout = dbc.Container([
    dbc.Row([
        dbc.Col([
            html.H1("Financial Insights Dashboard", className="text-center mb-4")
        ])
    ]),
    
    dbc.Row([
        dbc.Col([
            dcc.Dropdown(
                id='stock-selector',
                options=[{'label': symbol, 'value': symbol} 
                         for symbol in data_fetcher.default_symbols],
                value=data_fetcher.default_symbols[0],
                className="mb-3"
            )
        ])
    ]),
    
    dbc.Row([
        dbc.Col([
            dcc.Graph(id='price-chart')
        ])
    ]),
    
    dbc.Row([
        dbc.Col([
            html.Div(id='metrics-card', className="mt-4")
        ])
    ]),
    
    # Add a div for error messages
    dbc.Row([
        dbc.Col([
            html.Div(id='error-message', className="mt-4 text-danger")
        ])
    ]),
    
    dcc.Interval(
        id='interval-component',
        interval=300000,  # Update every 5 minutes
        n_intervals=0
    )
], fluid=True)

def create_empty_figure():
    """Create an empty figure with a message"""
    return {
        'data': [],
        'layout': {
            'title': 'No data available',
            'annotations': [{
                'text': 'No data available. Please check your connection or try again later.',
                'xref': 'paper',
                'yref': 'paper',
                'showarrow': False,
                'font': {'size': 20}
            }]
        }
    }

@app.callback(
    [Output('price-chart', 'figure'),
     Output('metrics-card', 'children'),
     Output('error-message', 'children')],
    [Input('stock-selector', 'value'),
     Input('interval-component', 'n_intervals')]
)
def update_charts(selected_symbol, n):
    try:
        # Fetch data from MongoDB
        collection = data_fetcher.db['stock_data']
        data = list(collection.find({'Symbol': selected_symbol}).sort('Date', 1))
        
        # Check if we got any data
        if not data:
            logger.warning(f"No data found for symbol {selected_symbol}")
            # Trigger a new data fetch
            data_fetcher.fetch_stock_data([selected_symbol])
            return create_empty_figure(), None, f"No data available for {selected_symbol}. Fetching new data..."
        
        df = pd.DataFrame(data)
        
        # Verify required columns exist
        required_columns = ['Date', 'Open', 'High', 'Low', 'Close', 'SMA_20', 'SMA_50']
        missing_columns = [col for col in required_columns if col not in df.columns]
        if missing_columns:
            logger.error(f"Missing required columns: {missing_columns}")
            return create_empty_figure(), None, f"Data error: Missing required columns {missing_columns}"
        
        # Create price chart
        fig = go.Figure()
        
        fig.add_trace(go.Candlestick(
            x=df['Date'],
            open=df['Open'],
            high=df['High'],
            low=df['Low'],
            close=df['Close'],
            name='OHLC'
        ))
        
        fig.add_trace(go.Scatter(
            x=df['Date'],
            y=df['SMA_20'],
            name='20 Day MA',
            line=dict(color='orange')
        ))
        
        fig.add_trace(go.Scatter(
            x=df['Date'],
            y=df['SMA_50'],
            name='50 Day MA',
            line=dict(color='blue')
        ))
        
        fig.update_layout(
            title=f'{selected_symbol} Stock Price',
            yaxis_title='Price',
            template='plotly_white',
            hovermode='x unified'
        )
        
        # Get summary metrics with error handling
        try:
            metrics = data_fetcher.get_summary_metrics([selected_symbol])
            if selected_symbol not in metrics:
                raise KeyError(f"No metrics found for {selected_symbol}")
                
            stock_metrics = metrics[selected_symbol]
            
            metrics_card = dbc.Card([
                dbc.CardBody([
                    html.H4("Summary Metrics", className="card-title"),
                    html.P(f"Latest Price: ${stock_metrics['latest_price']}", className="card-text"),
                    html.P(f"Monthly Return: {stock_metrics['monthly_return']}%", className="card-text"),
                    html.P(f"Annualized Volatility: {stock_metrics['volatility']}%", className="card-text"),
                    html.P(f"Last Updated: {stock_metrics['last_updated']}", className="card-text"),
                ])
            ])
        except Exception as metrics_error:
            logger.error(f"Error calculating metrics: {str(metrics_error)}")
            metrics_card = dbc.Card([
                dbc.CardBody([
                    html.H4("Summary Metrics Unavailable", className="card-title text-danger"),
                    html.P("Error calculating metrics. Please try again later.", className="card-text"),
                ])
            ])
        
        return fig, metrics_card, None
        
    except Exception as e:
        logger.error(f"Error updating charts: {str(e)}")
        return create_empty_figure(), None, f"Error: {str(e)}"

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