import requests
from datetime import datetime
import hashlib
from config import Config

def get_weather(city):
    api_key = Config.WEATHER_API_KEY
    
    # Check if API key is missing or still the placeholder
    if not api_key or api_key == '7c94758cf7fae3f386208d73a848dd91':
        print(f"WARNING: No OpenWeatherMap API Key. Generating dynamic mock weather for {city}.")
        return _mock_weather(city)
        
    try:
        url = f"{Config.WEATHER_BASE_URL}/weather"
        params = {'q': city, 'appid': api_key, 'units': 'metric'}
        resp = requests.get(url, params=params, timeout=5).json()
        
        # If the city is not found, or API key is invalid
        if resp.get('cod') != 200:
            print(f"API Error: {resp.get('message')}. Falling back to mock data.")
            return _mock_weather(city)

        return {
            'current': {
                'temp': resp['main']['temp'],
                'humidity': resp['main']['humidity'],
                'rainfall_mm': resp.get('rain', {}).get('1h', 0),
                'description': resp['weather'][0]['description'],
                'city': resp['name']
            },
            'source': 'live'
        }
    except Exception as e:
        print(f"Exception during API call: {e}. Falling back to mock data.")
        return _mock_weather(city)

def _mock_weather(city):
    # Generate deterministic but different weather based on the city name
    city_hash = int(hashlib.md5(city.encode()).hexdigest(), 16)
    
    # Temperatures between 22.0°C and 30.0°C
    temp = 22.0 + (city_hash % 80) / 10.0
    # Humidity between 60% and 95%
    humidity = 60 + (city_hash % 35)
    # Rainfall between 0mm and 10mm
    rain = (city_hash % 20) / 2.0
    
    descriptions = ['clear sky', 'scattered clouds', 'light rain', 'overcast clouds', 'moderate rain']
    desc = descriptions[city_hash % len(descriptions)]
    
    return {
        'current': {
            'temp': round(temp, 1),
            'humidity': humidity,
            'rainfall_mm': round(rain, 1),
            'description': desc,
            'city': city
        },
        'source': 'mock'
    }

def generate_ai_advisory(soil, crop_type, crop_stage, weather, has_irrigated=False, land_size_acres=1.0, motor_flow_rate=30000):
    current = weather['current']
    rain = current['rainfall_mm']
    humidity = current['humidity']
    temp = current['temp']
    current_month = datetime.now().strftime('%B')
    
    plan = {
        'immediate': [],
        'this_week': [],
        'long_term': [],
        'soil_health_score': 0,
        'alerts': []
    }

    # Helper function to format hours based on motor flow rate
    def calculate_hours(litres):
        hours_exact = litres / motor_flow_rate
        hours = int(hours_exact)
        minutes = int((hours_exact - hours) * 60)
        if hours > 0:
            return f"{hours} hrs {minutes} mins"
        return f"{minutes} mins"

    # 1. Calculate Soil Health Score
    score = 100
    if soil.soil_ph < 5.5 or soil.soil_ph > 7.0: score -= 20
    if soil.nitrogen_kg_ha < 200: score -= 15
    if soil.potassium_kg_ha < 200: score -= 15
    if soil.phosphorus_kg_ha < 18: score -= 10
    if soil.zinc_ppm < 1.0: score -= 10
    plan['soil_health_score'] = max(0, score)

    # 2. Immediate Actions (No daily irrigation nagging)
    if rain > 5:
        plan['immediate'].append("🌧️ <b>Hold fertilizer application.</b> Heavy rain may wash away nutrients.")
    else:
        plan['immediate'].append("☀️ <b>Good day for field inspection.</b> Check leaves for early signs of pests.")
            
    if crop_stage == 'flowering':
        plan['immediate'].append("🌸 <b>Critical Stage:</b> Inspect flowers carefully to ensure healthy pollination.")
    elif crop_stage == 'fruiting':
        plan['immediate'].append("🍒 <b>Fruiting Stage:</b> Check berry development. Ensure adequate shade.")

    # 3. Pest & Disease Alerts
    if 'Coffee' in crop_type and humidity > 80:
        plan['alerts'].append("🚨 <b>Coffee Leaf Rust Risk:</b> High humidity detected. Inspect leaves.")
    if 'Pepper' in crop_type and humidity > 85 and rain > 10:
        plan['alerts'].append("🚨 <b>Foot Rot Risk:</b> Excess moisture. Ensure proper drainage.")

    # 4. Smart Irrigation Logic (Robusta Dataset + Motor Hours)
    if has_irrigated:
        plan['this_week'].append("✅ <b>Irrigation Complete:</b> You indicated the farm was recently irrigated. Skip watering for now.")
    elif crop_stage == 'harvesting':
        plan['this_week'].append("🛑 <b>Stop Irrigation:</b> Do not irrigate during harvesting to prevent mold, berry splitting, or root rot. Keep the crop dry.")
    elif rain > 10:
        plan['this_week'].append("🌧️ <b>Skip Irrigation:</b> Sufficient rainfall expected/detected. Natural moisture is adequate.")
    elif 'Coffee' in crop_type:
        # Dataset-specific logic for Robusta Coffee
        if crop_stage == 'flowering' or current_month == 'February':
            # Blossom Irrigation: 40mm per acre
            water = int(land_size_acres * 161874)
            hours = calculate_hours(water)
            plan['this_week'].append(f"🌸 <b>Blossom Irrigation:</b> Apply <b>{water:,} litres</b> (40mm). Run your motor for approximately <b>{hours}</b> to encourage uniform flowering.")
            plan['this_week'].append("🌿 <b>Management:</b> Apply nutrients based on your soil test results.")
        elif crop_stage == 'vegetative' or current_month == 'March':
            # Backing Irrigation: 25mm per acre
            water = int(land_size_acres * 101171)
            hours = calculate_hours(water)
            plan['this_week'].append(f"🌱 <b>Backing Irrigation:</b> Apply <b>{water:,} litres</b> (25mm). Run your motor for approximately <b>{hours}</b> to improve fruit setting.")
            plan['this_week'].append("🌿 <b>Management:</b> Maintain soil moisture. Prepare for April organic manure application.")
        elif current_month in ['June', 'July', 'August', 'September']:
             plan['this_week'].append("🌧️ <b>Monsoon Season:</b> Irrigation is generally rainfall-dependent. Monitor soil moisture and ensure proper drainage.")
             plan['this_week'].append("🛠️ <b>Management:</b> Focus on weed management, pest monitoring, and disease control during monsoon.")
        else:
             water = int(land_size_acres * 120000) # approx 30mm
             hours = calculate_hours(water)
             plan['this_week'].append(f"💧 <b>Berry Development:</b> Apply <b>{water:,} litres</b>. Run motor for approx <b>{hours}</b> to prevent moisture stress during dry spells.")
             plan['this_week'].append("🌿 <b>Management:</b> Apply organic manure and mulch the base to retain moisture.")
    else:
        # Generic logic for Pepper or other crops
        water = int(land_size_acres * 40000)
        hours = calculate_hours(water)
        plan['this_week'].append(f"💧 <b>Irrigation Required:</b> Apply <b>{water:,} liters</b>. Run motor for approx <b>{hours}</b>.")

    # 5. Fertilizer & Soil Corrections
    if soil.nitrogen_kg_ha < 200:
        plan['this_week'].append("🧪 <b>Nitrogen Deficiency:</b> Apply Urea (100g/plant) or organic compost.")
    if soil.potassium_kg_ha < 200:
        plan['this_week'].append("🧪 <b>Potassium Deficiency:</b> Apply Muriate of Potash (MOP) 250g/plant.")
    if soil.soil_ph < 5.5:
        plan['this_week'].append("⚗️ <b>Acidic Soil:</b> Apply Agricultural Lime (500 kg/acre).")
    elif soil.soil_ph > 7.0:
        plan['this_week'].append("⚗️ <b>Alkaline Soil:</b> Apply Gypsum to lower pH.")
        
    if soil.soil_moisture == 'Low':
        plan['this_week'].append("💧 <b>Low Soil Moisture:</b> Consider mulching to retain water.")
    if soil.soil_texture == 'Sandy':
        plan['this_week'].append("🏜️ <b>Sandy Soil:</b> Water more frequently but in smaller quantities.")

    # 6. Long Term Strategy
    plan['long_term'].append("🌱 Maintain shade tree canopy at 40-50% for temperature control.")
    plan['long_term'].append("📊 Upload a new soil test report every 6 months to track progress.")
    plan['long_term'].append("📅 In November, plan for harvest and post-harvest processing to ensure quality beans.")
    if plan['soil_health_score'] < 60:
         plan['long_term'].append("🔄 Focus on organic matter (FYM/compost) to rebuild soil health over time.")

    return plan