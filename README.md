# 📊 Financial Insights Dashboard

## 📖 Project Overview
The **Financial Insights Dashboard** is a web application built with Python, Dash, and Flask that provides real-time stock market insights. It fetches, processes, and visualizes financial data, making it easier to analyze trends and performance metrics for various stocks. MongoDB is used for persistent storage, and Power BI integration supports advanced reporting.

## 🚀 Features
- 📈 Interactive candlestick charts with 20-day and 50-day moving averages.
- ⚡ Real-time data fetching with automatic updates every 5 minutes.
- 🧮 Summary metrics including latest price, monthly returns, and volatility.
- 🛠️ REST API endpoints for historical data, metrics, and performance.
- 📊 Power BI-friendly data export for advanced visualization.

## 🛠️ Tech Stack
- **Python**: Flask, Dash, Pandas, Plotly
- **Database**: MongoDB
- **APIs**: Yahoo Finance (via `yfinance`)
- **Visualization**: Dash Bootstrap Components, Plotly, Power BI

## ⚙️ Installation & Setup
1. **Clone the Repository**
   ```bash
   git clone https://github.com/timothykimutai/Automated-Financial-Insights-Dashboard.git
   cd financial-insights-dashboard
   ```
2. **Install Dependencies**
   ```bash
   pip install -r requirements.txt
   ```
3. **Configure Environment**
   - Create a `.env` file with the following:
     ```bash
     MONGO_URI=mongodb://localhost:27017
     ```
4. **Run the Application**
   ```bash
   python app.py
   ```
5. **Access the Dashboard**
   - Open `http://127.0.0.1:8050/` in your browser.

## 🔍 Usage
- Select a stock from the dropdown to view historical price trends.
- View key performance metrics in the metrics card.
- Integrate Power BI using the `/api/v1/stock/metrics/all` endpoint.

## 🔗 API Endpoints
- **GET** `/api/v1/stock/historical/<symbol>`: Historical data for a specific stock.
- **GET** `/api/v1/stock/metrics/all`: Metrics for all tracked stocks.
- **GET** `/api/v1/stock/performance`: Daily performance comparisons.

## 📊 Sample Power BI Integration
- Add a Web Data Source with: `http://127.0.0.1:5000/api/v1/stock/metrics/all`
- Refresh to get the latest stock metrics.

## 🛠️ Troubleshooting
- **No data available**: Check internet connection and retry.
- **Database connection issues**: Verify MongoDB URI in `.env`.
- **Performance lag**: Optimize the `yfinance` data fetching frequency.

## 👨‍💻 Author
- Timothy Kimutai - Data Scientist | Python Developer

---


