import os
import numpy as np
import tensorflow as tf
import requests
from datetime import datetime, date
from tensorflow.keras.preprocessing import image
from werkzeug.utils import secure_filename
from PIL import Image
from flask import Flask, render_template, redirect, url_for, flash, request, send_file
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, date
import json
import hashlib

from models import (db, User, Listing, Order, CarbonCredit, SoilReport, AdvisoryLog, CropStage, 
                    GovernmentScheme, LoanProduct, SchemeApplication, CarbonPool, CarbonPurchase)
from config import Config
from modules.market import fetch_live_market_prices
from modules.advisory import get_weather, generate_ai_advisory
from modules.schemes import (check_scheme_eligibility, check_loan_eligibility, calculate_loan, 
                             estimate_max_loan, generate_application_pdf, generate_carbon_certificate)
from models import db, User, Listing, Order, CarbonCredit, SoilReport, AdvisoryLog, CropStage, GovernmentScheme, LoanProduct, SchemeApplication, CarbonPool, CarbonPurchase, PestReport

app = Flask(__name__)
app.config.from_object(Config)
app.config['UPLOAD_FOLDER'] = 'static/uploads'
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
db.init_app(app)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

@app.route('/')
def index(): return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        user = User.query.filter_by(email=request.form['email']).first()
        if user and check_password_hash(user.password, request.form['password']):
            login_user(user)
            if user.role == 'farmer': return redirect(url_for('farmer_dashboard'))
            elif user.role == 'buyer': return redirect(url_for('buyer_dashboard'))
            else: return redirect(url_for('admin_dashboard'))
        flash('Invalid email or password', 'danger')
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))

@app.route('/register/farmer', methods=['GET', 'POST'])
def register_farmer():
    if request.method == 'POST':
        data = request.form
        if User.query.filter_by(email=data['email']).first():
            flash('Email already registered!', 'danger')
            return redirect(url_for('register_farmer'))
        user = User(
            email=data['email'], password=generate_password_hash(data['password']), role='farmer',
            name=data['name'], phone=data['phone'], state=data['state'], district=data['district'],
            location=data['district'], land_size_acres=float(data['land_size_acres']),
            crop_type=data['crop_type'], years_experience=int(data.get('years_experience', 0)),
            tree_count=int(data.get('tree_count', 0)), shade_percentage=float(data.get('shade_percentage', 0))
        )
        db.session.add(user); db.session.commit()
        flash('Registration successful! Please login.', 'success')
        return redirect(url_for('login'))
    return render_template('register_farmer.html')

@app.route('/register/buyer', methods=['GET', 'POST'])
def register_buyer():
    if request.method == 'POST':
        data = request.form
        if User.query.filter_by(email=data['email']).first():
            flash('Email already registered!', 'danger')
            return redirect(url_for('register_buyer'))
        user = User(
            email=data['email'], password=generate_password_hash(data['password']), role='buyer',
            name=data['name'], phone=data['phone'], company_name=data['company_name'],
            gst_number=data['gst_number'], buyer_type=data['buyer_type'],
            state=data.get('state', ''), district=data.get('district', '')
        )
        db.session.add(user); db.session.commit()
        flash('Buyer registration successful! Please login.', 'success')
        return redirect(url_for('login'))
    return render_template('register_buyer.html')

@app.route('/farmer/dashboard')
@login_required
def farmer_dashboard():
    if current_user.role != 'farmer': return redirect(url_for('index'))
    listings = Listing.query.filter_by(farmer_id=current_user.id).all()
    orders = Order.query.join(Listing).filter(Listing.farmer_id == current_user.id).all()
    carbon = CarbonCredit.query.filter_by(farmer_id=current_user.id).first()
    if not carbon: carbon = calculate_carbon(current_user)
    return render_template('farmer_dashboard.html', listings=listings, orders=orders, carbon=carbon)

@app.route('/buyer/dashboard')
@login_required
def buyer_dashboard():
    if current_user.role != 'buyer': return redirect(url_for('index'))
    listings = Listing.query.filter_by(status='Active').all()
    my_orders = Order.query.filter_by(buyer_id=current_user.id).all()
    return render_template('buyer_dashboard.html', listings=listings, orders=my_orders)

@app.route('/market-prices')
@login_required
def market_prices():
    # 1. Try to fetch live data from API Ninjas
    api_response = fetch_live_market_prices()
    
    api_status = "Offline (Using Reference Data)"
    current_rates = []
    
    if api_response and api_response.get('success'):
        api_status = "Live API Data"
        current_rates = api_response['rates'] # Live Coffee data
        
    # 2. Fallback Data (Used if API fails)
    if not current_rates:
        current_rates = [
            {'crop': 'Coffee', 'variety': 'Arabica Parchment', 'price': '₹480 - ₹492 / kg', 'trend': 'Stable'},
            {'crop': 'Coffee', 'variety': 'Arabica Cherry', 'price': '₹260 - ₹290 / kg', 'trend': 'Stable'},
            {'crop': 'Coffee', 'variety': 'Robusta Parchment', 'price': '₹356 - ₹366 / kg', 'trend': 'Stable'},
            {'crop': 'Coffee', 'variety': 'Robusta Cherry', 'price': '₹160 - ₹196 / kg', 'trend': 'Volatile'},
            {'crop': 'Pepper', 'variety': 'Black Pepper (Garbled)', 'price': '₹725 - ₹750 / kg', 'trend': 'Rising'},
            {'crop': 'Pepper', 'variety': 'Black Pepper (Ungarbled)', 'price': '₹705 - ₹730 / kg', 'trend': 'Rising'},
        ]

    # 3. Chart Data (Keep your existing chart data here)
    price_history = {
        'labels': ['May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct'],
        'datasets': [
            {'label': 'Arabica Parchment (₹/kg)', 'data': [480, 475, 485, 490, 485, 482], 'borderColor': '#198754', 'backgroundColor': 'rgba(25, 135, 84, 0.1)', 'tension': 0.4, 'fill': True},
            {'label': 'Robusta Parchment (₹/kg)', 'data': [365, 360, 355, 358, 362, 360], 'borderColor': '#0d6efd', 'backgroundColor': 'rgba(13, 110, 253, 0.1)', 'tension': 0.4, 'fill': True},
            {'label': 'Arabica Cherry (₹/kg)', 'data': [265, 260, 270, 275, 272, 270], 'borderColor': '#ffc107', 'backgroundColor': 'rgba(255, 193, 7, 0.1)', 'tension': 0.4, 'fill': True},
            {'label': 'Robusta Cherry (₹/kg)', 'data': [185, 180, 178, 175, 178, 180], 'borderColor': '#dc3545', 'backgroundColor': 'rgba(220, 53, 69, 0.1)', 'tension': 0.4, 'fill': True},
            {'label': 'Black Pepper (₹/kg)', 'data': [690, 685, 700, 710, 720, 740], 'borderColor': '#6f42c1', 'backgroundColor': 'rgba(111, 66, 193, 0.1)', 'tension': 0.4, 'fill': True}
        ]
    }

    return render_template('market_prices.html', price_history=price_history, current_rates=current_rates, api_status=api_status)

@app.route('/admin/dashboard')
@login_required
def admin_dashboard():
    if current_user.role != 'admin': return redirect(url_for('index'))
    return render_template('admin_dashboard.html', farmers=User.query.filter_by(role='farmer').all(), buyers=User.query.filter_by(role='buyer').all(), listings=Listing.query.all())

@app.route('/admin/verify_buyer/<int:user_id>')
@login_required
def verify_buyer(user_id):
    if current_user.role != 'admin': return redirect(url_for('index'))
    user = User.query.get_or_404(user_id)
    if user.role == 'buyer':
        user.is_verified = True
        db.session.commit()
        flash(f'Buyer {user.company_name} has been verified.', 'success')
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/delete_user/<int:user_id>', methods=['POST'])
@login_required
def delete_user(user_id):
    if current_user.role != 'admin': return redirect(url_for('index'))
    user = User.query.get_or_404(user_id)
    if user.role != 'admin': # Prevent deleting self
        db.session.delete(user)
        db.session.commit()
        flash(f'User {user.name} has been deleted.', 'danger')
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/delete_listing/<int:listing_id>', methods=['POST'])
@login_required
def admin_delete_listing(listing_id):
    if current_user.role != 'admin': return redirect(url_for('index'))
    listing = Listing.query.get_or_404(listing_id)
    db.session.delete(listing)
    db.session.commit()
    flash('Listing has been removed from the platform.', 'danger')
    return redirect(url_for('admin_dashboard'))

@app.route('/marketplace')
@login_required
def marketplace(): return render_template('marketplace.html', listings=Listing.query.filter_by(status='Active').all())

@app.route('/add_listing', methods=['GET', 'POST'])
@login_required
def add_listing():
    if current_user.role != 'farmer': return redirect(url_for('index'))
    
    if request.method == 'POST':
        testing_requested = request.form.get('testing_requested') == 'yes'
        
        # If testing is requested, don't save outturn/moisture
        outturn = None if testing_requested else float(request.form.get('outturn_pct') or 0)
        moisture = None if testing_requested else float(request.form.get('moisture_pct') or 0)
        
        listing = Listing(
            farmer_id=current_user.id, 
            crop_type=request.form['crop_type'],
            coffee_type=request.form.get('coffee_type', ''),
            outturn_pct=outturn,
            moisture_pct=moisture,
            testing_requested=testing_requested,
            grade=request.form.get('grade', 'Standard'),
            quantity_kg=float(request.form['quantity_kg']), 
            expected_price_per_kg=float(request.form['expected_price_per_kg']),
            harvest_date=datetime.strptime(request.form['harvest_date'], '%Y-%m-%d').date()
        )
        db.session.add(listing); db.session.commit()
        flash('Listing added successfully!', 'success')
        return redirect(url_for('farmer_dashboard'))
        
    return render_template('add_listing.html')

@app.route('/place_order/<int:listing_id>', methods=['POST'])
@login_required
def place_order(listing_id):
    if current_user.role != 'buyer': return redirect(url_for('index'))
    listing = Listing.query.get_or_404(listing_id)
    quantity = float(request.form['quantity_kg'])
    order = Order(listing_id=listing_id, buyer_id=current_user.id, quantity_kg=quantity,
                  offered_price_per_kg=float(request.form['offered_price_per_kg']), total_amount=quantity * float(request.form['offered_price_per_kg']))
    db.session.add(order); db.session.commit()
    flash('Order placed successfully!', 'success')
    return redirect(url_for('buyer_dashboard'))

@app.route('/update_order/<int:order_id>/<string:status>', methods=['POST'])
@login_required
def update_order_status(order_id, status):
    if current_user.role != 'farmer': 
        return redirect(url_for('index'))
    
    order = Order.query.get_or_404(order_id)
    
    # Security check: Ensure this order belongs to a listing owned by this farmer
    if order.listing.farmer_id == current_user.id:
        order.status = status
        db.session.commit()
        flash(f'Order {status.lower()} successfully!', 'success')
    else:
        flash('Unauthorized action.', 'danger')
        
    return redirect(url_for('farmer_dashboard'))

@app.route('/disease-detector', methods=['GET', 'POST'])
@login_required
def disease_detector():
    if current_user.role != 'farmer': return redirect(url_for('index'))
    
    prediction = None
    image_path = None
    
    # 🧠 THE KNOWLEDGE BASE (Moved inside the route)
    disease_info = {
        'Coffee_Leaf_Diseases': {
            'description': 'Coffee Leaf Rust (Hemileia vastatrix) is a devastating fungal disease that attacks the leaves, causing severe defoliation and massive yield loss.',
            'symptoms': 'Yellow-orange powdery spots on the underside of leaves, yellowing on the top, and premature leaf drop.',
            'prevention': 'Maintain proper spacing between plants for airflow. Prune shade trees during monsoon to reduce humidity. Apply balanced fertilizers to keep plants strong.',
            'treatment': 'Apply copper-based fungicides (Bordeaux mixture 1% or Copper Oxychloride). Remove and burn severely infected leaves.'
        },
        'Footrot': {
            'description': 'Foot Rot (Quick Wilt) is a lethal soil-borne fungal disease caused by Phytophthora capsici. It attacks the root collar and spreads rapidly.',
            'symptoms': 'Blackening at the base of the stem, water-soaked lesions, sudden wilting of leaves even when soil is wet, and eventual plant death.',
            'prevention': 'Ensure excellent soil drainage (avoid waterlogging). Use raised beds in heavy rainfall areas. Plant disease-free vines and apply Trichoderma bio-agents to the soil.',
            'treatment': 'Drench the soil around the base with 0.2% Copper Oxychloride or Metalaxyl. Remove and destroy infected vines immediately to prevent spread to neighboring plants.'
        },
        'Pollu_Disease': {
            'description': 'Pollu disease is caused by thrips and berry borers feeding on the tender shoots and developing berries.',
            'symptoms': 'Premature dropping of berries, hollow or scarred berries, silvering or scabbing on the undersides of leaves, and curled shoot tips.',
            'prevention': 'Regular monitoring during the flowering and fruiting stage. Maintain shade trees to regulate temperature. Keep the plantation free of weeds.',
            'treatment': 'Spray Neem oil (3ml/L) or Imidacloprid (as per agricultural guidelines). Use yellow sticky traps to catch adult insects.'
        },
        'Slow-Decline': {
            'description': 'Slow Decline is a gradual dying of the vine often caused by a combination of root-knot nematodes, poor soil nutrition, and drought stress.',
            'symptoms': 'Slow yellowing of leaves, stunted growth, gradual dieback of branches from the tip downwards over 1-2 years.',
            'prevention': 'Apply organic manure (FYM) and bio-fertilizers regularly. Avoid water stress during dry months. Practice crop rotation if possible.',
            'treatment': 'Apply bio-agents like Paecilomyces lilacinus or Trichoderma viride to the soil to control nematodes. Ensure adequate NPK supplementation.'
        },
        'Healthy': {
            'description': 'Your plant is healthy! No signs of disease were detected.',
            'symptoms': 'Vibrant green leaves, no spots, no wilting, and normal growth.',
            'prevention': 'Maintain your current irrigation and fertilization schedule. Keep monitoring for early signs of pests.',
            'treatment': 'No chemical treatment required. Keep up the good work!'
        },
        'Not_Leaf': {
            'description': 'The image uploaded is not a coffee or pepper leaf.',
            'symptoms': 'Contains human faces, random objects, or backgrounds.',
            'prevention': 'Please ensure you are uploading a close-up photo of a plant leaf.',
            'treatment': 'Retake the photo focusing only on a single leaf with a clear background.'
        },
        'Unknown': {
            'description': 'The AI could not confidently identify this image.',
            'symptoms': 'The image might be blurry, or the lighting is too dark.',
            'prevention': 'Hold the camera steady.',
            'treatment': 'Please upload a clear, well-lit, close-up photo of an infected leaf.'
        }
    }
    
    if request.method == 'POST':
        if 'leaf_image' not in request.files:
            flash('No file uploaded', 'danger')
            return redirect(request.url)
            
        file = request.files['leaf_image']
        if file.filename == '':
            flash('No file selected', 'danger')
            return redirect(request.url)
            
        if file:
            filename = secure_filename(file.filename)
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(filepath)
            image_path = f"uploads/{filename}"
            
            try:
                # Load model and class names
                model = tf.keras.models.load_model('leaf_disease_model.keras')
                class_names = json.load(open('class_names.json'))
                
                # Preprocess image
                img = image.load_img(filepath, target_size=(224, 224))
                arr = np.expand_dims(image.img_to_array(img), 0)
                
                # Predict
                probs = model.predict(arr)[0]
                top_2 = np.argsort(probs)[-2:][::-1]
                
                raw_label = class_names[top_2[0]]
                conf = float(probs[top_2[0]]) * 100
                margin = (probs[top_2[0]] - probs[top_2[1]]) * 100
                
                # Logic based on the AI's recommendation
                if raw_label == "Not_Leaf":
                    status = "alert"
                    msg = "This is not a coffee/pepper leaf. Please upload a clear leaf photo."
                    final_class = 'Not Leaf'
                elif conf < 60.0 or margin < 20.0:
                    status = "uncertain"
                    msg = "Unclear image. Please retake in good light with the leaf filling the frame."
                    final_class = 'Unknown'
                elif raw_label == "Healthy":
                    status = "healthy"
                    msg = f"Leaf looks healthy ({conf:.1f}%)."
                    final_class = 'Healthy'
                else:
                    status = "disease"
                    final_class = raw_label.replace('_', ' ')
                    msg = f"Disease Detected: {final_class}"
                
                # 🔥 ADDING THE DETAILS DICTIONARY HERE
                prediction = {
                    'status': status,
                    'class': final_class,
                    'confidence': round(conf, 2),
                    'message': msg,
                    'details': disease_info.get(raw_label, disease_info['Unknown'])
                }
                
            except Exception as e:
                flash(f'AI Error: {e}', 'danger')
                
    return render_template('disease_detector.html', prediction=prediction, image_path=image_path)

@app.route('/advisory', methods=['GET', 'POST'])
@login_required
def advisory_dashboard():
    soil = SoilReport.query.filter_by(farmer_id=current_user.id).order_by(SoilReport.created_at.desc()).first()
    stage = CropStage.query.filter_by(farmer_id=current_user.id).order_by(CropStage.created_at.desc()).first()
    return render_template('advisory_dashboard.html', soil=soil, stage=stage)
@app.route('/advisory/fetch-soil', methods=['POST'])
@login_required
def fetch_soil_api():
    if current_user.role != 'farmer': return redirect(url_for('index'))
    
    area = float(request.form['area_acres'])
    lat = float(request.form['lat'])
    lon = float(request.form['lon'])
    
    # Save to user profile
    current_user.land_size_acres = area
    current_user.latitude = lat
    current_user.longitude = lon
    db.session.commit()
    
    try:
        # Fetch from ISRIC SoilGrids API
        url = f"https://rest.isric.org/soilgrids/v2.0/properties/query?lon={lon}&lat={lat}&property=nitrogen&property=phh2o&depth=0-5cm&value=mean"
        response = requests.get(url, timeout=15).json()
        
        layers = response['properties']['layers']
        nitrogen_val = None
        ph_val = None
        
        for layer in layers:
            if layer['name'] == 'nitrogen' and layer['depths'][0]['values']['mean'] is not None:
                nitrogen_val = layer['depths'][0]['values']['mean']
            if layer['name'] == 'phh2o' and layer['depths'][0]['values']['mean'] is not None:
                ph_val = layer['depths'][0]['values']['mean'] / 10.0
        
        if nitrogen_val is not None and ph_val is not None:
            nitrogen_kg_ha = nitrogen_val * 0.02 
            
            new_soil = SoilReport(
                farmer_id=current_user.id,
                soil_ph=round(ph_val, 1),
                nitrogen_kg_ha=round(nitrogen_kg_ha, 1),
                phosphorus_kg_ha=20.0, # Default baseline
                potassium_kg_ha=200.0, # Default baseline
                zinc_ppm=1.2, 
                boron_ppm=0.5,
                test_date=date.today()
            )
            db.session.add(new_soil)
            db.session.commit()
            flash(f'Live Soil Data Fetched! Area: {area} Acres. pH: {round(ph_val,1)}, Nitrogen: {round(nitrogen_kg_ha,1)} kg/ha.', 'success')
        else:
            flash(f'Farm mapped! Area: {area} Acres. (Live soil data not available for this coordinate, using existing data).', 'warning')
            
    except Exception as e:
        flash(f'Farm mapped! Area saved. Error fetching API: {str(e)}', 'warning')
        
    return redirect(url_for('advisory_dashboard'))

@app.route('/advisory/soil', methods=['GET', 'POST'])
@login_required
def soil_input():
    if request.method == 'POST':
        soil = SoilReport(
            farmer_id=current_user.id, soil_ph=float(request.form['soil_ph']),
            nitrogen_kg_ha=float(request.form['nitrogen_kg_ha']), phosphorus_kg_ha=float(request.form['phosphorus_kg_ha']),
            potassium_kg_ha=float(request.form['potassium_kg_ha']), zinc_ppm=float(request.form.get('zinc_ppm', 0)),
            boron_ppm=float(request.form.get('boron_ppm', 0)), soil_moisture=request.form.get('soil_moisture'),
            soil_texture=request.form.get('soil_texture'), test_date=date.today()
        )
        db.session.add(soil); db.session.commit()
        flash('Soil report saved!', 'success')
        return redirect(url_for('advisory_dashboard'))
    return render_template('soil_input.html')

@app.route('/advisory/generate', methods=['POST'])
@login_required
def generate_advisory():
    soil = SoilReport.query.filter_by(farmer_id=current_user.id).order_by(SoilReport.created_at.desc()).first()
    if not soil:
        flash('Please add your soil report first.', 'warning')
        return redirect(url_for('soil_input'))
    
    location = request.form.get('location', current_user.district)
    current_user.location = location
    
    has_irrigated = request.form.get('has_irrigated') == 'yes'
    motor_flow_rate = int(request.form.get('motor_flow_rate', 30000))
    
    stage_record = CropStage(
        farmer_id=current_user.id, 
        crop_type=current_user.crop_type, 
        current_stage=request.form.get('current_stage', 'vegetative'), 
        stage_start_date=date.today(),
        has_irrigated=has_irrigated
    )
    db.session.add(stage_record); db.session.commit()

    weather = get_weather(location)
    
    plan = generate_ai_advisory(
        soil, 
        current_user.crop_type, 
        stage_record.current_stage, 
        weather, 
        has_irrigated=has_irrigated, 
        land_size_acres=current_user.land_size_acres or 1.0,
        motor_flow_rate=motor_flow_rate
    )
    
    return render_template('advisory_result.html', weather=weather, soil=soil, stage=stage_record.current_stage, crop_type=current_user.crop_type, plan=plan)

@app.route('/schemes')
@login_required
def schemes_dashboard():
    schemes = [{'scheme': s, 'eligible': check_scheme_eligibility(current_user, s)[0], 'missing': check_scheme_eligibility(current_user, s)[1]} for s in GovernmentScheme.query.all()]
    loans = []
    for l in LoanProduct.query.all():
        eligible, missing, _ = check_loan_eligibility(current_user, l)
        max_amt = estimate_max_loan(current_user, l) if eligible else 0
        loans.append({'loan': l, 'eligible': eligible, 'missing': missing, 'max_amount': max_amt, 'emi_data': calculate_loan(max_amt, l.interest_rate_pct or 7.0, l.tenure_years or 3)})
    return render_template('schemes_dashboard.html', schemes=schemes, loans=loans, applications=SchemeApplication.query.filter_by(farmer_id=current_user.id).all())

@app.route('/schemes/apply/<int:scheme_id>', methods=['POST'])
@login_required
def apply_scheme(scheme_id):
    db.session.add(SchemeApplication(farmer_id=current_user.id, scheme_id=scheme_id, application_type='scheme'))
    db.session.commit(); flash('Scheme application submitted!', 'success')
    return redirect(url_for('schemes_dashboard'))

@app.route('/loans/apply/<int:loan_id>', methods=['POST'])
@login_required
def apply_loan(loan_id):
    db.session.add(SchemeApplication(farmer_id=current_user.id, loan_id=loan_id, application_type='loan'))
    db.session.commit(); flash('Loan application submitted!', 'success')
    return redirect(url_for('schemes_dashboard'))

@app.route('/application/<int:app_id>/pdf')
@login_required
def download_application_pdf(app_id):
    app_rec = SchemeApplication.query.get_or_404(app_id)
    pdf = generate_application_pdf(current_user, app_rec.scheme if app_rec.application_type == 'scheme' else app_rec.loan, app_rec.application_type)
    return send_file(pdf, as_attachment=True, download_name=f"guide_{app_id}.pdf", mimetype='application/pdf')

@app.route('/loan/calculator', methods=['GET', 'POST'])
@login_required
def loan_calculator():
    result = calculate_loan(float(request.form['principal']), float(request.form['rate']), int(request.form['tenure'])) if request.method == 'POST' else None
    return render_template('loan_products.html', result=result)

@app.route('/carbon/marketplace')
@login_required
def carbon_marketplace():
    # Admins see all pools, others only see 'Open' pools
    if current_user.role == 'admin':
        pools = CarbonPool.query.all()
    else:
        pools = CarbonPool.query.filter_by(status='Open').all()
        
    purchases = CarbonPurchase.query.filter_by(buyer_id=current_user.id).all() if current_user.role == 'buyer' else []
    my_credits = CarbonCredit.query.filter_by(farmer_id=current_user.id).first() if current_user.role == 'farmer' else None
    
    return render_template('carbon_marketplace.html', pools=pools, purchases=purchases, my_credits=my_credits)

@app.route('/admin/delete_carbon_pool/<int:pool_id>', methods=['POST'])
@login_required
def admin_delete_carbon_pool(pool_id):
    if current_user.role != 'admin': return redirect(url_for('index'))
    
    pool = CarbonPool.query.get_or_404(pool_id)
    # Also delete associated purchases to maintain database integrity
    CarbonPurchase.query.filter_by(pool_id=pool_id).delete()
    
    db.session.delete(pool)
    db.session.commit()
    flash('Carbon Pool removed successfully.', 'danger')
    return redirect(url_for('carbon_marketplace'))

@app.route('/carbon/pool/create', methods=['POST'])
@login_required
def create_carbon_pool():
    credit = CarbonCredit.query.filter_by(farmer_id=current_user.id).first()
    if not credit or credit.credits_earned <= 0:
        flash('No credits available.', 'warning'); return redirect(url_for('carbon_marketplace'))
    region = current_user.district or 'General'
    pool = CarbonPool.query.filter_by(region=region, status='Open').first()
    if pool: pool.total_tonnes += credit.credits_earned
    else: db.session.add(CarbonPool(name=f"{region} Carbon Pool", region=region, total_tonnes=credit.credits_earned))
    credit.verification_status = 'Pooled'; db.session.commit()
    flash('Credits pooled successfully!', 'success'); return redirect(url_for('carbon_marketplace'))

@app.route('/carbon/buy/<int:pool_id>', methods=['POST'])
@login_required
def buy_carbon_credits(pool_id):
    pool = CarbonPool.query.get_or_404(pool_id)
    tonnes = float(request.form['tonnes'])
    if tonnes > pool.total_tonnes:
        flash('Not enough tonnes available.', 'danger'); return redirect(url_for('carbon_marketplace'))
    total = tonnes * pool.price_per_tonne
    cert_hash = hashlib.sha256(f"{current_user.id}{pool.id}{tonnes}{datetime.utcnow()}".encode()).hexdigest()
    db.session.add(CarbonPurchase(buyer_id=current_user.id, pool_id=pool.id, tonnes_purchased=tonnes, total_amount=total, certificate_hash=cert_hash))
    pool.total_tonnes -= tonnes
    if pool.total_tonnes <= 0: pool.status = 'Sold Out'
    db.session.commit(); flash('Purchase successful! Certificate generated.', 'success')
    return redirect(url_for('carbon_marketplace'))

@app.route('/carbon/certificate/<int:purchase_id>')
@login_required
def download_carbon_certificate(purchase_id):
    purchase = CarbonPurchase.query.get_or_404(purchase_id)
    pdf = generate_carbon_certificate(current_user, purchase)
    return send_file(pdf, as_attachment=True, download_name=f"carbon_cert_{purchase.id}.pdf", mimetype='application/pdf')

def calculate_carbon(farmer):
    if not farmer.land_size_acres: return None
    rate = {'Coffee': 12.5 if (farmer.shade_percentage or 0) > 30 else 6.5, 'Pepper': 8.0, 'Coffee+Pepper': 15.0}.get(farmer.crop_type, 10.0)
    t = farmer.land_size_acres * 0.4047 * rate
    credit = CarbonCredit(farmer_id=farmer.id, estimated_tonnes=round(t, 2), credits_earned=round(t, 2))
    db.session.add(credit); db.session.commit(); return credit

with app.app_context():
    db.create_all()

@app.cli.command('init-db')
def init_db():
    db.create_all()
    if not User.query.filter_by(email='admin@agrodirect.com').first():
        db.session.add(User(email='admin@agrodirect.com', password=generate_password_hash('admin123'), role='admin', name='Admin'))
        db.session.commit()
    print('Database initialized!')
@app.route('/map-farm', methods=['GET'])
@login_required
def map_farm():
    if current_user.role != 'farmer': return redirect(url_for('index'))
    return render_template('farm_mapper.html')

@app.route('/save-farm-map', methods=['POST'])
@login_required
def save_farm_map():
    if current_user.role != 'farmer': return redirect(url_for('index'))
    
    area = float(request.form['area_acres'])
    lat = float(request.form['lat'])
    lon = float(request.form['lon'])
    
    # 1. Save area and coordinates to the user's profile
    current_user.land_size_acres = area
    current_user.latitude = lat
    current_user.longitude = lon
    db.session.commit()
    
    # 2. Fetch Live Soil Data from ISRIC SoilGrids API
    try:
        # We fetch Nitrogen (nitrogen) and pH (phh2o) at 0-5cm topsoil depth
        url = f"https://rest.isric.org/soilgrids/v2.0/properties/query?lon={lon}&lat={lat}&property=nitrogen&property=phh2o&depth=0-5cm&value=mean"
        response = requests.get(url, timeout=15).json()
        
        layers = response['properties']['layers']
        nitrogen_val = None
        ph_val = None
        
        for layer in layers:
            if layer['name'] == 'nitrogen' and layer['depths'][0]['values']['mean'] is not None:
                nitrogen_val = layer['depths'][0]['values']['mean'] # in cg/kg
            if layer['name'] == 'phh2o' and layer['depths'][0]['values']['mean'] is not None:
                ph_val = layer['depths'][0]['values']['mean'] / 10.0 # scaled by 10
        
        # 3. Automatically generate a Soil Report
        if nitrogen_val is not None and ph_val is not None:
            # Convert Nitrogen from cg/kg to approx kg/ha
            nitrogen_kg_ha = nitrogen_val * 0.02 
            
            new_soil = SoilReport(
                farmer_id=current_user.id,
                soil_ph=round(ph_val, 1),
                nitrogen_kg_ha=round(nitrogen_kg_ha, 1),
                phosphorus_kg_ha=20.0, # Default baseline
                potassium_kg_ha=200.0, # Default baseline
                zinc_ppm=1.2, 
                boron_ppm=0.5,
                test_date=date.today()
            )
            db.session.add(new_soil)
            db.session.commit()
            flash(f'Farm mapped successfully! Area: {area} Acres. Live Soil Data fetched (pH: {round(ph_val,1)}, Nitrogen: {round(nitrogen_kg_ha,1)} kg/ha).', 'success')
        else:
            flash(f'Farm mapped! Area: {area} Acres. (Soil data not available for this exact coordinate, using defaults).', 'warning')
            
    except Exception as e:
        flash(f'Farm mapped! Area saved. Error fetching soil data: {str(e)}', 'warning')
        
    return redirect(url_for('advisory_dashboard'))

# 1. Route to view the community map
@app.route('/community-alerts')
@login_required
def community_alerts():
    if current_user.role != 'farmer': return redirect(url_for('index'))
    
    # Fetch all reports to show on the map
    reports = PestReport.query.order_by(PestReport.reported_at.desc()).limit(50).all()
    
    # Convert to JSON for Leaflet
    reports_data = [{
        'disease': r.disease_name,
        'lat': r.latitude,
        'lon': r.longitude,
        'date': r.reported_at.strftime('%d-%m-%Y'),
        'farmer': r.farmer.name
    } for r in reports]
    
    return render_template('community_alerts.html', reports=reports_data)

# 2. Route to submit a new report (We will trigger this from the AI result page)
@app.route('/report-outbreak', methods=['POST'])
@login_required
def report_outbreak():
    if current_user.role != 'farmer': return redirect(url_for('index'))
    
    disease = request.form.get('disease_name')
    
    # Use the farmer's stored GPS coordinates (from the Farm Mapper feature)
    if not current_user.latitude or not current_user.longitude:
        # Fallback to district center if they haven't mapped their farm
        lat, lon = 13.3161, 75.7720 # Chikmagalur default
        flash('Please map your farm in the Advisory section for accurate pinning. Using district default.', 'warning')
    else:
        lat, lon = current_user.latitude, current_user.longitude

    report = PestReport(
        farmer_id=current_user.id,
        disease_name=disease,
        latitude=lat,
        longitude=lon
    )
    db.session.add(report)
    db.session.commit()
    
    flash(f'Outbreak reported! Farmers in your area have been alerted about {disease}.', 'danger')
    return redirect(url_for('community_alerts'))

@app.cli.command('seed-data')
def seed_data():
    if GovernmentScheme.query.count() == 0:
        db.session.add_all([
            GovernmentScheme(scheme_id='SC001', scheme_name='Coffee Board Replanting Subsidy', category='Subsidy', crop='Coffee', description='50% subsidy for replanting.', eligibility_criteria=json.dumps({'max_land_acres': 10, 'crops': ['Coffee'], 'min_experience_years': 5}), documents_required='Land record, Aadhaar, Bank passbook', benefit_amount='50% of cost (max ₹40,000/acre)', official_link='https://coffeeboard.gov.in'),
            GovernmentScheme(scheme_id='SC002', scheme_name='Spices Board Quality Support', category='Subsidy', crop='Pepper', description='Assistance for organic certification.', eligibility_criteria=json.dumps({'crops': ['Pepper']}), documents_required='GI certificate, Land record', benefit_amount='Up to ₹25,000', official_link='http://www.indianspices.com'),
            GovernmentScheme(scheme_id='SC003', scheme_name='PM-KISAN', category='Income Support', crop='All', description='Income support for farmers.', eligibility_criteria=json.dumps({'max_land_acres': 50}), documents_required='Aadhaar, Land record', benefit_amount='₹6,000/year', official_link='https://pmkisan.gov.in')
        ])
    if LoanProduct.query.count() == 0:
        db.session.add_all([
            LoanProduct(loan_id='LN001', bank_name='SBI', loan_type='Coffee Crop Loan', interest_rate_pct=7.0, max_amount_inr=500000, tenure_years=3, documents_required='Land record, Aadhaar', eligibility_criteria=json.dumps({'crops': ['Coffee']})),
            LoanProduct(loan_id='LN002', bank_name='NABARD', loan_type='Kisan Credit Card', interest_rate_pct=4.0, max_amount_inr=200000, tenure_years=5, documents_required='Aadhaar, Land record', eligibility_criteria=json.dumps({'max_land_acres': 50}))
        ])
    db.session.commit(); print('Seed data loaded!')

if __name__ == '__main__': app.run(debug=True, port=5001)