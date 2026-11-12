import requests
from datetime import datetime

def fetch_live_market_prices():
    API_URL = "https://api.api-ninjas.com/v1/commodityprice"
    API_KEY = "B9tbGWaW39CFZD0eSVvJD7brhwWACKz7wrGqkqrG"
    
    headers = {
        "X-Api-Key": API_KEY
    }

    try:
        # We request 'coffee' from the API
        response = requests.get(API_URL, headers=headers, params={'name': 'coffee'}, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            
            if isinstance(data, list) and len(data) > 0:
                data = data[0]
                
            # The API returns price in US Cents per Pound
            cents_per_lb = float(data.get('price', 0))
            
            # Conversion: 1 Pound = 0.453592 kg. 1 USD = 83 INR (approx)
            usd_per_lb = cents_per_lb / 100
            inr_per_kg = (usd_per_lb * 83) / 0.453592
            
            # Format as a table row for our UI
            live_rates = [{
                'crop': 'Coffee',
                'variety': data.get('name', 'Coffee') + f" ({data.get('exchange', 'ICE')})",
                'price': f"₹{inr_per_kg:.2f} / kg",
                'trend': 'Live'
            }]
            
            return {'success': True, 'rates': live_rates, 'raw': data}
            
        else:
            print(f"API Error: {response.status_code} - {response.text}")
            return {'success': False}
            
    except Exception as e:
        print(f"Exception during API call: {e}")
        return {'success': False}