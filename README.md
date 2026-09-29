# 🌿 AgroDirect+ 
### Empowering Small Coffee & Pepper Planters through Direct Trade, AI Advisory, and Climate FinTech

![Python](https://img.shields.io/badge/Python-3.11-blue.svg)
![Flask](https://img.shields.io/badge/Flask-3.0.3-green.svg)
![SQLite](https://img.shields.io/badge/Database-SQLite-lightgrey.svg)
![License](https://img.shields.io/badge/License-Academic-orange.svg)

**AgroDirect+** is a comprehensive digital platform designed specifically for coffee and pepper farmers in South India. It addresses three major challenges faced by small planters: exploitative middlemen, lack of scientific crop guidance, and poor access to financial schemes and emerging carbon markets.

This project is developed as an MCA 12-Credit Capstone Project at **PES University**.

---

## ✨ Key Features

### 🤝 1. Direct Farmer-to-Corporate Marketplace
*   Farmers can list their produce (Coffee/Pepper) with quality grades, quantity, and expected prices.
*   Corporate buyers (Exporters, Roasters, Spice Brands) can browse, negotiate, and place direct orders.
*   Eliminates middlemen, ensuring fair prices for farmers.

### 🌾 2. Smart Crop Advisory Engine
*   **Weather Integration:** Fetches real-time weather data (OpenWeatherMap API) based on the farmer's district.
*   **Soil Analysis:** Farmers input soil test reports (pH, N, P, K, Zinc, Boron).
*   **AI Recommendations:** Rule-based + ML engine provides personalized advice on fertilizer dosage, irrigation timing, pest control, and harvest windows.
*   **Weather-Aware Alerts:** Alerts for Coffee Leaf Rust, Berry Borer, and Pepper Foot Rot based on current humidity and temperature.

### 🏛️ 3. Loan & Government Scheme Assistance
*   Integrated database of 5+ Government Schemes (Coffee Board, Spices Board, PM-KISAN) and Crop Loans (SBI, NABARD).
*   Automated Eligibility Checker based on land size, crop type, state, and experience.
*   **Pre-filled PDF Generation:** Automatically generates a professional, ready-to-submit application form with the farmer's details.
*   Built-in **EMI Calculator** for crop loans.

### 🌍 4. Carbon Credit Marketplace (Novel Feature)
*   Automatically estimates carbon sequestration (tCO₂/year) based on land size, crop type, and shade percentage.
*   Farmers can "pool" their credits into regional carbon pools.
*   Corporate buyers can purchase these credits to offset their emissions (ESG compliance).
*   Generates a **tamper-proof PDF Certificate** with a SHA-256 hash for every purchase.

### 👤 5. Role-Based Access Control
*   **Farmer Dashboard:** Manage listings, view advisories, check schemes.
*   **Buyer Dashboard:** Browse produce, purchase carbon credits.
*   **Admin Panel:** Manage users and verify buyers.

---

## 🛠️ Technology Stack

| Layer | Technology |
|-------|------------|
| **Backend** | Python 3.11, Flask |
| **Database** | SQLite (SQLAlchemy ORM) |
| **Frontend** | HTML5, CSS3, JavaScript, Bootstrap 5, Jinja2 |
| **Data Processing** | Pandas, NumPy |
| **PDF Generation** | ReportLab |
| **Weather API** | OpenWeatherMap |
| **Authentication** | Flask-Login, Werkzeug Security |
| **Deployment** | Render / Heroku (WSGI: Gunicorn) |

---

## 🚀 How to Run Locally

1. **Clone the repository:**
   ```bash
   git clone https://github.com/YOUR_USERNAME/agrodirect.git
   cd agrodirect