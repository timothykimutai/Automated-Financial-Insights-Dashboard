import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from pymongo import MongoClient
import logging
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class FinancialDataFetcher:
    def __init__(self):
        # Initialize MongoDB connection
        self.mongo_uri = os.getenv('MONGO_URI', 'mongodb://localhost:27017/')
        self.client = MongoClient(self.mongo_uri)
        self.db = self.client['financial_dashboard']
        
        # Default symbols to track
        self.default_symbols = ['AAPL', 'GOOGL', 'MSFT', 'AMZN', 'META']

    def fetch_stock_data(self, symbols=None):
        if symbols is None:
            symbols = self.default_symbols

        collection = self.db['stock_data']

        for symbol in symbols:
            try:
                logger.info(f"Fetching latest data for {symbol}")

                # Get last available date from MongoDB
                latest_record = collection.find_one(
                    {"Symbol": symbol}, sort=[("Date", -1)]
                )
                last_date = latest_record['Date'] if latest_record else "2025-02-12"
                start_date = (pd.to_datetime(last_date) + timedelta(days=1)).strftime('%Y-%m-%d')

                # Fetch new stock data
                df = yf.download(symbol, start=start_date)

                if df.empty:
                    logger.warning(f"No new data for {symbol}")
                    continue

                # Reset index and clean data
                df = df.reset_index()
                df['Date'] = df['Date'].dt.strftime('%Y-%m-%d')
                df['Symbol'] = symbol

                # Calculate indicators
                df['Daily_Return'] = df['Close'].pct_change().fillna(0)
                df['Volatility'] = df['Daily_Return'].rolling(window=20, min_periods=1).std().fillna(0)
                df['SMA_20'] = df['Close'].rolling(window=20, min_periods=1).mean().fillna(df['Close'])
                df['SMA_50'] = df['Close'].rolling(window=50, min_periods=1).mean().fillna(df['Close'])

                # Convert to dictionary
                records = df.to_dict('records')

                # Insert or update records
                for record in records:
                    collection.update_one(
                        {"Symbol": symbol, "Date": record["Date"]},
                        {"$set": record},
                        upsert=True  # Insert if not found
                    )

                logger.info(f"Updated {len(records)} records for {symbol}")

            except Exception as e:
                logger.error(f"Error fetching data for {symbol}: {str(e)}")

    def get_summary_metrics(self, symbols=None):
        if symbols is None:
            symbols = self.default_symbols
            
        summary_metrics = {}
        collection = self.db['stock_data']
        
        for symbol in symbols:
            try:
                # Get the last 30 days of data
                cursor = collection.find(
                    {'Symbol': symbol},
                    {'Date': 1, 'Close': 1, 'Daily_Return': 1}
                ).sort('Date', -1).limit(30)
                
                data = list(cursor)
                
                if not data:
                    logger.warning(f"No data found for {symbol}")
                    continue
                
                # Convert to DataFrame
                df = pd.DataFrame(data)
                
                # Ensure proper sorting
                df = df.sort_values(by='Date', ascending=True)
                
                # Ensure numeric Close prices
                df['Close'] = pd.to_numeric(df['Close'], errors='coerce')
                df['Daily_Return'] = pd.to_numeric(df['Daily_Return'], errors='coerce')
                
                # Calculate metrics
                latest_price = df['Close'].iloc[-1] if not df['Close'].isnull().all() else 0
                oldest_price = df['Close'].iloc[0] if not df['Close'].isnull().all() else 0
                monthly_return = ((latest_price / oldest_price - 1) * 100) if oldest_price != 0 else 0
                
                # Calculate annualized volatility
                daily_std = df['Daily_Return'].std()
                annualized_volatility = daily_std * np.sqrt(252) * 100 if not pd.isna(daily_std) else 0
                
                summary_metrics[symbol] = {
                    'latest_price': round(latest_price, 2),
                    'monthly_return': round(monthly_return, 2),
                    'volatility': round(annualized_volatility, 2),
                    'last_updated': df['Date'].iloc[-1] if not df.empty else "N/A"
                }
                
            except Exception as e:
                logger.error(f"Error calculating metrics for {symbol}: {str(e)}")
                continue
        
        return summary_metrics

if __name__ == "__main__":
    fetcher = FinancialDataFetcher()
    try:
        print("Starting initial data fetch...")
        fetcher.fetch_stock_data(['AAPL'])  
        print("Data fetched and stored successfully!")
        
        # Test metrics calculation
        metrics = fetcher.get_summary_metrics(['AAPL'])
        print("\nMetrics:", metrics)
    except Exception as e:
        print(f"Error during test: {str(e)}")
