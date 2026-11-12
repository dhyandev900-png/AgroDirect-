<div align="center">
  
  <h1>🌿 AgroDirect+</h1>
  <p><i>Empowering Small Coffee & Pepper Planters through Direct Trade, AI Advisory, and Climate FinTech</i></p>

  <!-- Badges -->
  <p>
    <img src="https://img.shields.io/badge/Python-3.11-blue?style=for-the-badge&logo=python&logoColor=white" alt="Python" />
    <img src="https://img.shields.io/badge/Flask-3.0.3-black?style=for-the-badge&logo=flask&logoColor=white" alt="Flask" />
    <img src="https://img.shields.io/badge/TensorFlow-2.21-FF6F00?style=for-the-badge&logo=tensorflow&logoColor=white" alt="TensorFlow" />
    <img src="https://img.shields.io/badge/SQLite-Database-003B57?style=for-the-badge&logo=sqlite&logoColor=white" alt="SQLite" />
  </p>
  <p>
    <img src="https://img.shields.io/badge/Bootstrap-563D7C?style=for-the-badge&logo=bootstrap&logoColor=white" alt="Bootstrap" />
    <img src="https://img.shields.io/badge/Leaflet-GIS-199900?style=for-the-badge&logo=leaflet&logoColor=white" alt="Leaflet" />
    <img src="https://img.shields.io/badge/Render-Deployed-46E3B7?style=for-the-badge&logo=render&logoColor=white" alt="Render" />
  </p>

  <p>
    <b>AgroDirect+</b> is a comprehensive digital platform designed specifically for coffee and pepper farmers in South India. It addresses major challenges faced by small planters: exploitative middlemen, lack of scientific crop guidance, poor access to financial schemes, and exclusion from emerging carbon markets.
  </p>
  
  <p><i>Developed as an MCA 12-Credit Capstone Project at <b>PES University</b>.</i></p>
</div>

---

## ✨ Key Features

### 🤝 1. Direct B2B Marketplace
*   **Direct Trading:** Farmers list produce (Coffee/Pepper) with specific quality grades, quantity (in Tons), and expected prices (per 50kg bag).
*   **No Middlemen:** Corporate buyers (Exporters, Roasters) can browse, contact farmers directly via phone, and place orders, ensuring fair market prices.

### 🌾 2. Smart Crop Advisory Engine (Rule-Based AI)
*   **Motor-Hours Calculator:** Translates complex Robusta irrigation datasets (mm) into exact pump operating hours based on the farmer's specific motor horsepower.
*   **Weather-Aware Alerts:** Predicts risks for Coffee Leaf Rust, Berry Borer, and Pepper Foot Rot based on current humidity and temperature thresholds.

### 🗺️ 3. GIS Farm Mapper & Live Soil Fetch
*   **Interactive Mapping:** Farmers click their exact farm location on a Leaflet.js map.
*   **Automated Soil Data:** Fetches scientific soil data (pH, Nitrogen) directly from the global **ISRIC SoilGrids API** using GPS coordinates, eliminating manual data entry.

### 🚨 4. Community Pest Outbreak Heatmap
*   **Early Warning System:** When the AI Disease Detector identifies a disease, farmers can report it to a shared community map.
*   **Geospatial Tracking:** Drops a live red pin at the farmer's GPS coordinates, alerting neighboring estates within a 10km radius to take preventative action.

### 📸 5. AI Disease Detector (Deep Learning)
*   **MobileNetV2 CNN:** A custom-trained Convolutional Neural Network classifies leaf images into 6 categories (Rust, Footrot, Pollu, Slow Decline, Healthy, and Not Leaf).
*   **Safety Threshold:** If the AI is less than 60% confident, it rejects the image to prevent false positives and dangerous chemical application.

### 🏛️ 6. Loan & Government Scheme Assistance
*   **Automated Eligibility Checker:** Matches farmers with Government Schemes (PM-KISAN, Coffee Board) and Crop Loans.
*   **Smart PDF Generator:** Automatically generates a professional "Application Guide" with pre-filled details, a document checklist, and bank instructions.

### 🌍 7. Carbon Credit Marketplace
*   **Carbon Estimation:** Automatically estimates carbon sequestration (tCO₂/year) based on land size and shade percentage.
*   **Cryptographic Certificates:** Corporate buyers purchase pooled credits and receive a tamper-proof PDF Certificate secured with a **SHA-256 cryptographic hash** for ESG reporting.

### 📈 8. Live Market Prices
*   Fetches live global coffee prices (ICE exchange) using API Ninjas.
*   Automatically converts USD/lb to INR/kg and renders a dynamic 6-month price trend graph using Chart.js.

---

## 🛠️ Technology Stack

| Layer | Technologies Used |
| :--- | :--- |
| **Backend** | Python 3.11, Flask, Gunicorn (WSGI) |
| **Database** | SQLite (SQLAlchemy ORM) |
| **Machine Learning** | TensorFlow / Keras, MobileNetV2, NumPy |
| **Frontend UI** | HTML5, CSS3, JavaScript, Bootstrap 5, Jinja2 |
| **Data Visualization** | Chart.js, Leaflet.js (GIS), Turf.js |
| **External APIs** | OpenWeatherMap, API Ninjas (Commodities), ISRIC SoilGrids |
| **PDF Generation** | ReportLab, Hashlib (SHA-256 Cryptography) |
| **Security & Auth** | Flask-Login, Werkzeug Password Hashing |

---

## 🚀 Local Installation & Setup

<details>
<summary><b>Click to expand the setup instructions</b></summary>

**1. Clone the repository**
```bash
git clone https://github.com/dhyandev900-png/AgroDirect-.git
cd AgroDirect-