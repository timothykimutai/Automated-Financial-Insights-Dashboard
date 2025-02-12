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

    def fetch_stock_data(self, symbols=None, period="1y"):
        """
        Fetch stock data for given symbols and period
        """
        if symbols is None:
            symbols = self.default_symbols
            
        all_data = {}
        for symbol in symbols:
            try:
                logger.info(f"Fetching data for {symbol}")
                
                # Create Ticker object
                ticker = yf.Ticker(symbol)
                
                # Fetch historical data
                df = ticker.history(period=period)
                
                if df.empty:
                    logger.warning(f"Empty dataset received for {symbol}")
                    continue
                
                # Reset index to make Date a column
                df = df.reset_index()
                
                # Ensure Date column is datetime
                df['Date'] = pd.to_datetime(df['Date'])
                
                # Convert all price columns to numeric, replacing any invalid values with NaN
                price_columns = ['Open', 'High', 'Low', 'Close', 'Volume']
                for col in price_columns:
                    if col in df.columns:
                        df[col] = pd.to_numeric(df[col], errors='coerce')
                
                # Drop any rows where Close price is NaN
                df = df.dropna(subset=['Close'])
                
                if df.empty:
                    logger.warning(f"No valid price data for {symbol} after cleaning")
                    continue
                
                # Calculate returns and metrics
                df['Daily_Return'] = df['Close'].pct_change()
                df['Volatility'] = df['Daily_Return'].rolling(window=20, min_periods=1).std()
                df['SMA_20'] = df['Close'].rolling(window=20, min_periods=1).mean()
                df['SMA_50'] = df['Close'].rolling(window=50, min_periods=1).mean()
                
                # Fill NaN values with 0 for returns and metrics
                df['Daily_Return'] = df['Daily_Return'].fillna(0)
                df['Volatility'] = df['Volatility'].fillna(0)
                df['SMA_20'] = df['SMA_20'].fillna(df['Close'])
                df['SMA_50'] = df['SMA_50'].fillna(df['Close'])
                
                # Add symbol column
                df['Symbol'] = symbol
                
                # Convert date to string for MongoDB
                df['Date'] = df['Date'].dt.strftime('%Y-%m-%d')
                
                # Convert DataFrame to records
                records = df.to_dict('records')
                
                # Store in MongoDB
                self.store_data(symbol, records)
                
                all_data[symbol] = records
                logger.info(f"Successfully processed {len(records)} records for {symbol}")
                
            except Exception as e:
                logger.error(f"Error processing {symbol}: {str(e)}")
                continue
                
        return all_data
    
    def store_data(self, symbol, records):
        """
        Store the fetched data in MongoDB
        """
        if not records:
            logger.warning(f"No records to store for {symbol}")
            return
            
        try:
            collection = self.db['stock_data']
            
            # Delete existing data for this symbol
            collection.delete_many({'Symbol': symbol})
            
            # Insert new data
            collection.insert_many(records)
            logger.info(f"Successfully stored {len(records)} records for {symbol}")
            
        except Exception as e:
            logger.error(f"Error storing data for {symbol}: {str(e)}")
            raise
    
    def get_summary_metrics(self, symbols=None):
        """
        Calculate summary metrics for the specified symbols
        """
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
                
                # Ensure we have numeric Close prices
                df['Close'] = pd.to_numeric(df['Close'], errors='coerce')
                df['Daily_Return'] = pd.to_numeric(df['Daily_Return'], errors='coerce')
                
                # Calculate metrics
                latest_price = float(df['Close'].iloc[0])
                oldest_price = float(df['Close'].iloc[-1])
                monthly_return = ((latest_price / oldest_price - 1) * 100) if oldest_price != 0 else 0
                
                # Calculate annualized volatility
                daily_std = df['Daily_Return'].std()
                annualized_volatility = daily_std * np.sqrt(252) * 100 if not pd.isna(daily_std) else 0
                
                summary_metrics[symbol] = {
                    'latest_price': round(latest_price, 2),
                    'monthly_return': round(monthly_return, 2),
                    'volatility': round(annualized_volatility, 2),
                    'last_updated': data[0]['Date']
                }
                
            except Exception as e:
                logger.error(f"Error calculating metrics for {symbol}: {str(e)}")
                continue
        
        return summary_metrics

if __name__ == "__main__":
    # Test the data fetcher
    fetcher = FinancialDataFetcher()
    try:
        print("Starting initial data fetch...")
        data = fetcher.fetch_stock_data(['AAPL'])  # Test with a single symbol first
        print("Data fetched and stored successfully!")
        
        # Test metrics calculation
        metrics = fetcher.get_summary_metrics(['AAPL'])
        print("\nMetrics:", metrics)
    except Exception as e:
        print(f"Error during test: {str(e)}")