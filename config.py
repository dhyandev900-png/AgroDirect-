import os

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'agrodirect-secret-key-2026'
    SQLALCHEMY_DATABASE_URI = 'sqlite:///database.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    WEATHER_API_KEY = 'd3fe99351443005fe101f979f5d445f2'
    WEATHER_BASE_URL = 'https://api.openweathermap.org/data/2.5'
