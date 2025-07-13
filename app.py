from flask import Flask, render_template, request
import pandas as pd
import plotly.express as px
import plotly.io as pio
import requests
from datetime import datetime

app = Flask(__name__)

# Generate simulated historical data (June 1 to July 14, 2025)
def generate_dummy_data():
    data = {
        'Date': pd.date_range(start="2025-06-01", end="2025-07-14", freq='D').tolist() * 5,
        'Route': ['Sydney-Melbourne', 'Brisbane-Sydney', 'Melbourne-Perth', 'Sydney-Perth', 'Adelaide-Sydney'] * 44,
        'Price': [100 + i % 30 + (i % 5) * 10 for i in range(220)],
    }
    df = pd.DataFrame(data)
    return df

# Fetch live flight data from OpenSky API (Australian airspace bounding box)
def fetch_realtime_flights():
    try:
        url = "https://opensky-network.org/api/states/all?lamin=-44.0&lomin=113.0&lamax=-10.0&lomax=154.0"
        response = requests.get(url, timeout=10)

        if response.status_code == 200:
            data = response.json()
            if 'states' in data and data['states']:
                columns = [
                    "icao24", "callsign", "origin_country", "time_position", "last_contact",
                    "longitude", "latitude", "baro_altitude", "on_ground", "velocity",
                    "heading", "vertical_rate", "sensors", "geo_altitude", "squawk",
                    "spi", "position_source"
                ]
                df = pd.DataFrame(data['states'], columns=columns)
                df['timestamp'] = pd.to_datetime(datetime.utcnow())
                df['route'] = df['origin_country'] + " (Est.)"
                df['price'] = 100 + (df['velocity'].fillna(0) % 50).astype(int)  # Simulated price for display
                return df
        return pd.DataFrame()
    except Exception as e:
        print("Error fetching data:", e)
        return pd.DataFrame()

@app.route('/', methods=['GET', 'POST'])
def index():
    chart_div = None
    summary_table = None
    live_table = None

    # Load simulated historical data
    df_dummy = generate_dummy_data()
    df_dummy['Date'] = pd.to_datetime(df_dummy['Date']).dt.date  # Convert to date for filtering

    # Fetch live data (no date filter)
    df_live = fetch_realtime_flights()

    if request.method == 'POST':
        start_date = request.form.get('start_date')
        end_date = request.form.get('end_date')

        try:
            start = pd.to_datetime(start_date).date()
            end = pd.to_datetime(end_date).date()

            # Filter simulated data by date range
            df_filtered = df_dummy[(df_dummy['Date'] >= start) & (df_dummy['Date'] <= end)]

            if df_filtered.empty:
                chart_div = "<p>No flight data available for selected dates.</p>"
            else:
                # Plot price trends for simulated data
                fig = px.line(df_filtered, x="Date", y="Price", color="Route", title="Simulated Price Trend Over Time")
                chart_div = pio.to_html(fig, full_html=False)

                # Summary table for simulated data
                summary = df_filtered.groupby('Route')['Price'].agg(['mean', 'min', 'max']).reset_index()
                summary.columns = ['Route', 'Avg Price', 'Min Price', 'Max Price']
                summary_table = summary.to_html(classes='table table-striped', index=False)

        except Exception as e:
            chart_div = f"<p>Error processing your request: {e}</p>"

    # Prepare live data table (top 20 flights)
    if not df_live.empty:
        live_table = df_live[['icao24', 'callsign', 'origin_country', 'velocity', 'route', 'price']].head(20).to_html(classes='table table-striped', index=False)
    else:
        live_table = "<p>No live flight data available at the moment.</p>"

    return render_template('index.html', chart_div=chart_div, summary_table=summary_table, live_table=live_table)

if __name__ == '__main__':
    app.run(debug=True)
