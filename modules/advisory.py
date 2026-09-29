import requests
from datetime import datetime, date
from config import Config

# ==================== WEATHER SERVICE ====================

def get_weather(city):
    """Fetch current weather + 5-day forecast from OpenWeatherMap"""
    api_key = Config.WEATHER_API_KEY
    if not api_key or api_key == 'your_openweathermap_api_key_here':
        return _mock_weather(city)

    try:
        # Current weather
        current_url = f"{Config.WEATHER_BASE_URL}/weather"
        params = {'q': city, 'appid': api_key, 'units': 'metric'}
        current_resp = requests.get(current_url, params=params, timeout=5).json()

        # 5-day forecast
        forecast_url = f"{Config.WEATHER_BASE_URL}/forecast"
        forecast_resp = requests.get(forecast_url, params=params, timeout=5).json()

        if current_resp.get('cod') != 200:
            return _mock_weather(city)

        current = {
            'temp': current_resp['main']['temp'],
            'humidity': current_resp['main']['humidity'],
            'rainfall_mm': current_resp.get('rain', {}).get('1h', 0),
            'description': current_resp['weather'][0]['description'],
            'city': current_resp['name']
        }

        forecast = []
        for item in forecast_resp.get('list', [])[:8]:  # next ~24 hours
            forecast.append({
                'datetime': item['dt_txt'],
                'temp': item['main']['temp'],
                'humidity': item['main']['humidity'],
                'rainfall_mm': item.get('rain', {}).get('3h', 0),
                'description': item['weather'][0]['description']
            })

        return {'current': current, 'forecast': forecast, 'source': 'live'}

    except Exception as e:
        print(f"Weather API error: {e}")
        return _mock_weather(city)


def _mock_weather(city):
    """Fallback mock data when API key is missing or fails"""
    return {
        'current': {
            'temp': 26.5,
            'humidity': 85,
            'rainfall_mm': 12.5,
            'description': 'moderate rain',
            'city': city
        },
        'forecast': [
            {'datetime': '2026-10-01 09:00', 'temp': 25.0, 'humidity': 88, 'rainfall_mm': 15.0, 'description': 'light rain'},
            {'datetime': '2026-10-01 12:00', 'temp': 27.0, 'humidity': 80, 'rainfall_mm': 5.0, 'description': 'overcast clouds'},
            {'datetime': '2026-10-01 15:00', 'temp': 28.5, 'humidity': 72, 'rainfall_mm': 0.0, 'description': 'scattered clouds'},
            {'datetime': '2026-10-02 09:00', 'temp': 24.5, 'humidity': 90, 'rainfall_mm': 22.0, 'description': 'heavy rain'},
            {'datetime': '2026-10-02 12:00', 'temp': 26.0, 'humidity': 85, 'rainfall_mm': 8.0, 'description': 'light rain'},
        ],
        'source': 'mock'
    }


# ==================== FERTILIZER RECOMMENDATION ENGINE ====================

def recommend_fertilizer(soil, crop_type, crop_stage, weather):
    """
    Rule-based fertilizer recommendation using soil + weather + crop stage.
    Returns a list of recommendation dicts.
    """
    recommendations = []
    current = weather['current']
    rainfall_next_24h = sum(f['rainfall_mm'] for f in weather['forecast'][:8])

    # ---------- Nitrogen ----------
    if soil.nitrogen_kg_ha < 200:
        dose = "Increase nitrogen dose by 20%"
    elif soil.nitrogen_kg_ha > 280:
        dose = "Reduce nitrogen dose by 15% (avoid excess vegetative growth)"
    else:
        dose = "Standard nitrogen dose is adequate"

    # Crop stage adjustments
    if crop_stage == 'flowering':
        n_note = "Apply nitrogen now to support flowering. Use urea 100g/plant."
    elif crop_stage == 'fruiting':
        n_note = "Reduce nitrogen; focus on potassium for fruit development."
    elif crop_stage == 'vegetative':
        n_note = "Apply nitrogen for healthy vegetative growth."
    else:
        n_note = "Maintain current nitrogen schedule."

    recommendations.append({
        'nutrient': 'Nitrogen (N)',
        'soil_value': f"{soil.nitrogen_kg_ha} kg/ha",
        'action': dose,
        'timing': n_note
    })

    # ---------- Phosphorus ----------
    if soil.phosphorus_kg_ha < 18:
        p_action = "Apply DAP or SSP to correct phosphorus deficiency"
    else:
        p_action = "Phosphorus level is adequate"

    recommendations.append({
        'nutrient': 'Phosphorus (P)',
        'soil_value': f"{soil.phosphorus_kg_ha} kg/ha",
        'action': p_action,
        'timing': "Apply at root zone during early morning or evening"
    })

    # ---------- Potassium ----------
    if soil.potassium_kg_ha < 200:
        k_action = "Apply Muriate of Potash (MOP) 250g/plant"
    else:
        k_action = "Potassium level is adequate"

    # Weather-aware timing
    if rainfall_next_24h > 20:
        k_timing = "Do NOT apply now — heavy rain expected. Wait 2 days."
    elif rainfall_next_24h > 5:
        k_timing = "Good time to apply — light rain will help absorption."
    else:
        k_timing = "Apply and irrigate lightly after application."

    recommendations.append({
        'nutrient': 'Potassium (K)',
        'soil_value': f"{soil.potassium_kg_ha} kg/ha",
        'action': k_action,
        'timing': k_timing
    })

    # ---------- pH Correction ----------
    if soil.soil_ph < 5.5:
        recommendations.append({
            'nutrient': 'Soil pH',
            'soil_value': str(soil.soil_ph),
            'action': "Apply agricultural lime @ 500 kg/acre",
            'timing': "Apply 3-4 weeks before next fertilizer cycle"
        })
    elif soil.soil_ph > 7.0:
        recommendations.append({
            'nutrient': 'Soil pH',
            'soil_value': str(soil.soil_ph),
            'action': "Apply gypsum or elemental sulfur to reduce pH",
            'timing': "Apply before monsoon"
        })

    # ---------- Micronutrients ----------
    if soil.zinc_ppm and soil.zinc_ppm < 1.0:
        recommendations.append({
            'nutrient': 'Zinc (Zn)',
            'soil_value': f"{soil.zinc_ppm} ppm",
            'action': "Spray Zinc Sulphate 0.5% foliar solution",
            'timing': "Spray during early morning, repeat after 15 days"
        })
    if soil.boron_ppm and soil.boron_ppm < 0.4:
        recommendations.append({
            'nutrient': 'Boron (B)',
            'soil_value': f"{soil.boron_ppm} ppm",
            'action': "Apply Borax @ 5 kg/acre",
            'timing': "Apply with basal fertilizer"
        })

    return recommendations


# ==================== IRRIGATION ADVISORY ====================

def irrigation_advisory(weather, crop_stage, soil_type='loam'):
    current = weather['current']
    rainfall_24h = sum(f['rainfall_mm'] for f in weather['forecast'][:8])
    humidity = current['humidity']
    temp = current['temp']

    if rainfall_24h > 25:
        advice = "Skip irrigation. Sufficient rainfall expected in next 24 hours."
        priority = "LOW"
    elif rainfall_24h > 10:
        advice = "Reduce irrigation by 50%. Light rain expected."
        priority = "LOW"
    elif rainfall_24h > 3:
        advice = "Normal irrigation. Light rain may supplement."
        priority = "MEDIUM"
    elif temp > 32 and humidity < 50:
        advice = "Increase irrigation frequency. High temperature and low humidity."
        priority = "HIGH"
    else:
        advice = "Maintain regular irrigation schedule."
        priority = "MEDIUM"

    # Crop-stage adjustments
    if crop_stage == 'flowering':
        stage_note = "Critical stage: Ensure consistent moisture. Avoid water stress."
    elif crop_stage == 'fruiting':
        stage_note = "Reduce irrigation slightly to concentrate flavors (for coffee)."
    elif crop_stage == 'harvesting':
        stage_note = "Stop irrigation 1 week before harvest."
    else:
        stage_note = "Standard irrigation appropriate for current stage."

    return {
        'advice': advice,
        'priority': priority,
        'stage_note': stage_note,
        'rainfall_forecast_mm': round(rainfall_24h, 1),
        'humidity': humidity,
        'temperature': temp
    }


# ==================== PEST & DISEASE ALERTS ====================

def pest_disease_alerts(weather, crop_type, crop_stage):
    alerts = []
    current = weather['current']
    humidity = current['humidity']
    temp = current['temp']
    rainfall_24h = sum(f['rainfall_mm'] for f in weather['forecast'][:8])

    # Coffee-specific
    if 'Coffee' in crop_type:
        if humidity > 85 and 18 <= temp <= 25:
            alerts.append({
                'disease': 'Coffee Leaf Rust',
                'risk': 'HIGH',
                'reason': f"High humidity ({humidity}%) + moderate temp ({temp}°C)",
                'action': "Apply Bordeaux mixture 1% or copper oxychloride. Inspect leaves for orange-yellow spots."
            })
        if rainfall_24h > 30 and crop_stage == 'fruiting':
            alerts.append({
                'disease': 'Berry Borer',
                'risk': 'MEDIUM',
                'reason': "High rainfall during fruiting stage",
                'action': "Monitor berries for entry holes. Apply neem-based biopesticide."
            })
        if humidity < 50 and temp > 32:
            alerts.append({
                'disease': 'White Stem Borer',
                'risk': 'MEDIUM',
                'reason': "Dry hot conditions favor this pest",
                'action': "Check for ridges on main stem. Remove affected branches."
            })

    # Pepper-specific
    if 'Pepper' in crop_type:
        if humidity > 90 and rainfall_24h > 20:
            alerts.append({
                'disease': 'Foot Rot (Phytophthora)',
                'risk': 'CRITICAL',
                'reason': f"Very high humidity ({humidity}%) + heavy rain ({rainfall_24h}mm expected)",
                'action': "Immediate: Drench soil with 0.2% copper oxychloride. Improve drainage. Remove infected vines."
            })
        if humidity > 80 and 25 <= temp <= 30:
            alerts.append({
                'disease': 'Pollu Beetle / Thrips',
                'risk': 'MEDIUM',
                'reason': "Warm humid weather favors thrips population",
                'action': "Spray neem oil 3ml/L. Monitor new leaves for curling."
            })
        if rainfall_24h > 40:
            alerts.append({
                'disease': 'Slow Wilt / Nematode',
                'risk': 'MEDIUM',
                'reason': "Waterlogged conditions increase nematode risk",
                'action': "Ensure proper drainage. Apply Trichoderma viride bioagent."
            })

    if not alerts:
        alerts.append({
            'disease': 'No immediate threat detected',
            'risk': 'LOW',
            'reason': "Current weather conditions are not favorable for major pests/diseases.",
            'action': "Continue regular monitoring. Inspect plants weekly."
        })

    return alerts


# ==================== HARVEST WINDOW PREDICTION ====================

def harvest_window(crop_type, crop_stage, weather):
    rainfall_24h = sum(f['rainfall_mm'] for f in weather['forecast'][:8])

    if crop_stage != 'fruiting':
        return {
            'ready': False,
            'message': f"Crop is in '{crop_stage}' stage. Harvest window will open after fruiting completes."
        }

    if rainfall_24h > 30:
        advice = "Delay harvest. Heavy rain expected — risk of mold and quality loss."
    elif rainfall_24h > 10:
        advice = "Harvest within 2-3 days after rain stops. Ensure dry storage."
    else:
        advice = "Good harvest window. Proceed with picking."

    return {
        'ready': True,
        'message': advice,
        'expected_window': "Next 5-10 days" if rainfall_24h < 20 else "After rainfall clears"
    }