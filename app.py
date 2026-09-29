from flask import Flask, render_template, redirect, url_for, flash, request, send_file
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, date
from io import BytesIO
import json

from models import (db, User, Listing, Order, CarbonCredit, SoilReport,
                    AdvisoryLog, CropStage, GovernmentScheme, LoanProduct,
                    SchemeApplication)
from config import Config
from modules.advisory import (get_weather, recommend_fertilizer,
                               irrigation_advisory, pest_disease_alerts,
                               harvest_window)
from modules.schemes import (check_scheme_eligibility, check_loan_eligibility,
                              calculate_loan, estimate_max_loan,
                              generate_application_pdf)
import hashlib
from models import db, User, Listing, Order, CarbonCredit, SoilReport, AdvisoryLog, CropStage, GovernmentScheme, LoanProduct, SchemeApplication, CarbonPool, CarbonPurchase
from modules.schemes import (check_scheme_eligibility, check_loan_eligibility, calculate_loan, estimate_max_loan, generate_application_pdf, generate_carbon_certificate)

app = Flask(__name__)
app.config.from_object(Config)
db.init_app(app)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


# ==================== BASIC ROUTES ====================

@app.route('/')
def index():
    return render_template('index.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        user = User.query.filter_by(email=email).first()
        
        if user and check_password_hash(user.password, password):
            login_user(user)
            if user.role == 'farmer':
                return redirect(url_for('farmer_dashboard'))
            elif user.role == 'buyer':
                return redirect(url_for('buyer_dashboard'))
            else:
                return redirect(url_for('admin_dashboard'))
        flash('Invalid email or password', 'danger')
    return render_template('login.html')


@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))


# ==================== REGISTRATION ROUTES ====================

@app.route('/register/farmer', methods=['GET', 'POST'])
def register_farmer():
    if request.method == 'POST':
        data = request.form
        if User.query.filter_by(email=data['email']).first():
            flash('Email already registered!', 'danger')
            return redirect(url_for('register_farmer'))
        
        user = User(
            email=data['email'],
            password=generate_password_hash(data['password']),
            role='farmer',
            name=data['name'],
            phone=data['phone'],
            state=data['state'],
            district=data['district'],
            language=data.get('language', 'English'),
            land_size_acres=float(data['land_size_acres']),
            crop_type=data['crop_type'],
            years_experience=int(data.get('years_experience', 0)),
            tree_count=int(data.get('tree_count', 0)),
            shade_percentage=float(data.get('shade_percentage', 0))
        )
        db.session.add(user)
        db.session.commit()
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
            email=data['email'],
            password=generate_password_hash(data['password']),
            role='buyer',
            name=data['name'],
            phone=data['phone'],
            company_name=data['company_name'],
            gst_number=data['gst_number'],
            buyer_type=data['buyer_type'],
            state=data.get('state', ''),
            district=data.get('district', '')
        )
        db.session.add(user)
        db.session.commit()
        flash('Buyer registration successful! Please login.', 'success')
        return redirect(url_for('login'))
    return render_template('register_buyer.html')


# ==================== DASHBOARD ROUTES ====================

@app.route('/farmer/dashboard')
@login_required
def farmer_dashboard():
    if current_user.role != 'farmer':
        return redirect(url_for('index'))
    listings = Listing.query.filter_by(farmer_id=current_user.id).all()
    orders = Order.query.join(Listing).filter(Listing.farmer_id == current_user.id).all()
    
    # Carbon estimate (auto-generate if not exists)
    carbon = CarbonCredit.query.filter_by(farmer_id=current_user.id).first()
    if not carbon:
        carbon = calculate_carbon(current_user)
    
    return render_template('farmer_dashboard.html', 
                         listings=listings, orders=orders, carbon=carbon)


@app.route('/buyer/dashboard')
@login_required
def buyer_dashboard():
    if current_user.role != 'buyer':
        return redirect(url_for('index'))
    listings = Listing.query.filter_by(status='Active').all()
    my_orders = Order.query.filter_by(buyer_id=current_user.id).all()
    return render_template('buyer_dashboard.html', listings=listings, orders=my_orders)


@app.route('/admin/dashboard')
@login_required
def admin_dashboard():
    if current_user.role != 'admin':
        return redirect(url_for('index'))
    farmers = User.query.filter_by(role='farmer').all()
    buyers = User.query.filter_by(role='buyer').all()
    listings = Listing.query.all()
    return render_template('admin_dashboard.html', farmers=farmers, buyers=buyers, listings=listings)


# ==================== MARKETPLACE ROUTES ====================

@app.route('/marketplace')
@login_required
def marketplace():
    crop_filter = request.args.get('crop', '')
    state_filter = request.args.get('state', '')
    
    query = Listing.query.filter_by(status='Active')
    if crop_filter:
        query = query.filter(Listing.crop_type.like(f'%{crop_filter}%'))
    if state_filter:
        query = query.join(User).filter(User.state == state_filter)
    
    listings = query.all()
    return render_template('marketplace.html', listings=listings)


@app.route('/add_listing', methods=['GET', 'POST'])
@login_required
def add_listing():
    if current_user.role != 'farmer':
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        listing = Listing(
            farmer_id=current_user.id,
            crop_type=request.form['crop_type'],
            grade=request.form['grade'],
            quantity_kg=float(request.form['quantity_kg']),
            expected_price_per_kg=float(request.form['expected_price_per_kg']),
            harvest_date=datetime.strptime(request.form['harvest_date'], '%Y-%m-%d').date(),
            description=request.form.get('description', '')
        )
        db.session.add(listing)
        db.session.commit()
        flash('Listing added successfully!', 'success')
        return redirect(url_for('farmer_dashboard'))
    return render_template('add_listing.html')


@app.route('/place_order/<int:listing_id>', methods=['POST'])
@login_required
def place_order(listing_id):
    if current_user.role != 'buyer':
        return redirect(url_for('index'))
    
    listing = Listing.query.get_or_404(listing_id)
    quantity = float(request.form['quantity_kg'])
    offered_price = float(request.form['offered_price_per_kg'])
    
    order = Order(
        listing_id=listing_id,
        buyer_id=current_user.id,
        quantity_kg=quantity,
        offered_price_per_kg=offered_price,
        total_amount=quantity * offered_price
    )
    db.session.add(order)
    db.session.commit()
    flash('Order placed successfully!', 'success')
    return redirect(url_for('buyer_dashboard'))


# ==================== CROP ADVISORY ROUTES ====================

@app.route('/advisory', methods=['GET', 'POST'])
@login_required
def advisory_dashboard():
    if current_user.role != 'farmer':
        return redirect(url_for('index'))

    soil = SoilReport.query.filter_by(farmer_id=current_user.id)\
                           .order_by(SoilReport.created_at.desc()).first()
    stage = CropStage.query.filter_by(farmer_id=current_user.id)\
                           .order_by(CropStage.created_at.desc()).first()

    return render_template('advisory_dashboard.html', soil=soil, stage=stage)


@app.route('/advisory/soil', methods=['GET', 'POST'])
@login_required
def soil_input():
    if current_user.role != 'farmer':
        return redirect(url_for('index'))

    if request.method == 'POST':
        soil = SoilReport(
            farmer_id=current_user.id,
            soil_ph=float(request.form['soil_ph']),
            organic_carbon_pct=float(request.form.get('organic_carbon_pct', 0)),
            nitrogen_kg_ha=float(request.form['nitrogen_kg_ha']),
            phosphorus_kg_ha=float(request.form['phosphorus_kg_ha']),
            potassium_kg_ha=float(request.form['potassium_kg_ha']),
            zinc_ppm=float(request.form.get('zinc_ppm', 0)),
            boron_ppm=float(request.form.get('boron_ppm', 0)),
            test_date=date.today()
        )
        db.session.add(soil)
        db.session.commit()
        flash('Soil report saved!', 'success')
        return redirect(url_for('advisory_dashboard'))
    return render_template('soil_input.html')


@app.route('/advisory/stage', methods=['POST'])
@login_required
def set_crop_stage():
    if current_user.role != 'farmer':
        return redirect(url_for('index'))

    stage = CropStage(
        farmer_id=current_user.id,
        crop_type=current_user.crop_type,
        current_stage=request.form['current_stage'],
        stage_start_date=date.today(),
        notes=request.form.get('notes', '')
    )
    db.session.add(stage)
    db.session.commit()
    flash('Crop stage updated!', 'success')
    return redirect(url_for('advisory_dashboard'))


@app.route('/advisory/generate')
@login_required
def generate_advisory():
    if current_user.role != 'farmer':
        return redirect(url_for('index'))

    soil = SoilReport.query.filter_by(farmer_id=current_user.id)\
                           .order_by(SoilReport.created_at.desc()).first()
    stage_record = CropStage.query.filter_by(farmer_id=current_user.id)\
                                  .order_by(CropStage.created_at.desc()).first()

    if not soil:
        flash('Please add your soil report first.', 'warning')
        return redirect(url_for('soil_input'))

    stage = stage_record.current_stage if stage_record else 'vegetative'
    crop_type = current_user.crop_type or 'Coffee'
    city = current_user.district or 'Chikmagalur'

    weather = get_weather(city)
    fert = recommend_fertilizer(soil, crop_type, stage, weather)
    irrig = irrigation_advisory(weather, stage)
    pests = pest_disease_alerts(weather, crop_type, stage)
    harvest = harvest_window(crop_type, stage, weather)

    # Log advisory
    log = AdvisoryLog(
        farmer_id=current_user.id,
        advisory_type='full',
        recommendation=f"{len(fert)} fertilizer items, {len(pests)} pest alerts",
        weather_summary=f"{weather['current']['description']}, {weather['current']['temp']}°C",
        soil_summary=f"pH {soil.soil_ph}, N {soil.nitrogen_kg_ha}, P {soil.phosphorus_kg_ha}, K {soil.potassium_kg_ha}"
    )
    db.session.add(log)
    db.session.commit()

    return render_template('advisory_result.html',
                           weather=weather, soil=soil, stage=stage,
                           crop_type=crop_type, fertilizer=fert,
                           irrigation=irrig, pests=pests, harvest=harvest)


# ==================== LOAN & SCHEME ROUTES ====================

@app.route('/schemes')
@login_required
def schemes_dashboard():
    if current_user.role != 'farmer':
        return redirect(url_for('index'))

    schemes = GovernmentScheme.query.all()
    loans = LoanProduct.query.all()

    scheme_results = []
    for s in schemes:
        eligible, missing, matched = check_scheme_eligibility(current_user, s)
        scheme_results.append({
            'scheme': s, 'eligible': eligible,
            'missing': missing, 'matched': matched
        })

    loan_results = []
    for l in loans:
        eligible, missing, matched = check_loan_eligibility(current_user, l)
        max_amount = estimate_max_loan(current_user, l) if eligible else 0
        emi_data = calculate_loan(max_amount, l.interest_rate_pct or 7.0, l.tenure_years or 3)
        loan_results.append({
            'loan': l, 'eligible': eligible,
            'missing': missing, 'matched': matched,
            'max_amount': max_amount, 'emi_data': emi_data
        })

    my_applications = SchemeApplication.query.filter_by(farmer_id=current_user.id).all()

    return render_template('schemes_dashboard.html',
                           schemes=scheme_results, loans=loan_results,
                           applications=my_applications)


@app.route('/schemes/apply/<int:scheme_id>', methods=['POST'])
@login_required
def apply_scheme(scheme_id):
    if current_user.role != 'farmer':
        return redirect(url_for('index'))

    app_record = SchemeApplication(
        farmer_id=current_user.id,
        scheme_id=scheme_id,
        application_type='scheme',
        status='Submitted'
    )
    db.session.add(app_record)
    db.session.commit()
    flash('Scheme application submitted! Download the pre-filled form below.', 'success')
    return redirect(url_for('schemes_dashboard'))


@app.route('/loans/apply/<int:loan_id>', methods=['POST'])
@login_required
def apply_loan(loan_id):
    if current_user.role != 'farmer':
        return redirect(url_for('index'))

    app_record = SchemeApplication(
        farmer_id=current_user.id,
        loan_id=loan_id,
        application_type='loan',
        status='Submitted'
    )
    db.session.add(app_record)
    db.session.commit()
    flash('Loan application submitted! Download the pre-filled form below.', 'success')
    return redirect(url_for('schemes_dashboard'))


@app.route('/application/<int:app_id>/pdf')
@login_required
def download_application_pdf(app_id):
    app_record = SchemeApplication.query.get_or_404(app_id)
    if app_record.farmer_id != current_user.id:
        flash('Unauthorized', 'danger')
        return redirect(url_for('schemes_dashboard'))

    if app_record.application_type == 'scheme':
        pdf_buffer = generate_application_pdf(current_user, app_record.scheme, 'scheme')
        filename = f"scheme_application_{app_record.id}.pdf"
    else:
        pdf_buffer = generate_application_pdf(current_user, app_record.loan, 'loan')
        filename = f"loan_application_{app_record.id}.pdf"

    return send_file(pdf_buffer, as_attachment=True, download_name=filename, mimetype='application/pdf')


@app.route('/loan/calculator', methods=['GET', 'POST'])
@login_required
def loan_calculator():
    result = None
    if request.method == 'POST':
        principal = float(request.form['principal'])
        rate = float(request.form['rate'])
        tenure = int(request.form['tenure'])
        result = calculate_loan(principal, rate, tenure)
    return render_template('loan_products.html', result=result)


# ==================== HELPER FUNCTIONS ====================

def calculate_carbon(farmer):
    """Calculate carbon credits for a farmer"""
    if not farmer.land_size_acres or not farmer.crop_type:
        return None
    
    rates = {
        'Coffee': 12.5 if (farmer.shade_percentage or 0) > 30 else 6.5,
        'Pepper': 8.0,
        'Coffee+Pepper': 15.0
    }
    rate = rates.get(farmer.crop_type, 10.0)
    land_hectares = farmer.land_size_acres * 0.4047
    annual_tonnes = land_hectares * rate
    
    credit = CarbonCredit(
        farmer_id=farmer.id,
        estimated_tonnes=round(annual_tonnes, 2),
        credits_earned=round(annual_tonnes, 2),
        verification_status='Pending'
    )
    db.session.add(credit)
    db.session.commit()
    return credit


# ==================== CLI COMMANDS ====================

@app.cli.command('init-db')
def init_db():
    """Initialize database and create admin user."""
    db.create_all()
    if not User.query.filter_by(email='admin@agrodirect.com').first():
        admin = User(
            email='admin@agrodirect.com',
            password=generate_password_hash('admin123'),
            role='admin',
            name='Administrator'
        )
        db.session.add(admin)
        db.session.commit()
    print('Database initialized! Admin login: admin@agrodirect.com / admin123')


@app.cli.command('seed-data')
def seed_data():
    """Seed schemes, loans, and sample farmers."""
    if GovernmentScheme.query.count() == 0:
        schemes = [
            GovernmentScheme(
                scheme_id='SC001', scheme_name='Coffee Board Replanting Subsidy',
                category='Subsidy', crop='Coffee',
                description='50% subsidy for replanting old coffee plants above 5 years.',
                eligibility_criteria=json.dumps({'max_land_acres': 10, 'crops': ['Coffee'], 'min_experience_years': 5}),
                documents_required='Land record, Aadhaar, Bank passbook, Plantation age certificate',
                benefit_amount='50% of replanting cost (max ₹40,000/acre)',
                official_link='https://coffeeboard.gov.in/schemes.html'
            ),
            GovernmentScheme(
                scheme_id='SC002', scheme_name='Spices Board Quality Certification Support',
                category='Subsidy', crop='Pepper',
                description='Financial assistance for organic certification of pepper.',
                eligibility_criteria=json.dumps({'crops': ['Pepper'], 'max_land_acres': 25}),
                documents_required='GI certificate application, Land record, Aadhaar',
                benefit_amount='Up to ₹25,000 for certification',
                official_link='http://www.indianspices.com/schemes.html'
            ),
            GovernmentScheme(
                scheme_id='SC003', scheme_name='PM-KISAN',
                category='Income Support', crop='All',
                description='₹6,000 per year income support for all landholding farmers.',
                eligibility_criteria=json.dumps({'max_land_acres': 50}),
                documents_required='Aadhaar, Land record, Bank passbook',
                benefit_amount='₹6,000/year in 3 installments',
                official_link='https://pmkisan.gov.in'
            ),
            GovernmentScheme(
                scheme_id='SC004', scheme_name='Karnataka Coffee Development Grant',
                category='Grant', crop='Coffee',
                description='Grant for drip irrigation installation in coffee plantations.',
                eligibility_criteria=json.dumps({'states': ['Karnataka'], 'crops': ['Coffee'], 'max_land_acres': 20}),
                documents_required='Land record, Quotation, Aadhaar',
                benefit_amount='Up to ₹50,000 for drip system',
                official_link='https://coffeeboard.gov.in'
            ),
            GovernmentScheme(
                scheme_id='SC005', scheme_name='Kerala State Pepper Development Scheme',
                category='Subsidy', crop='Pepper',
                description='Support for pepper vine replanting and disease management.',
                eligibility_criteria=json.dumps({'states': ['Kerala'], 'crops': ['Pepper'], 'max_land_acres': 5}),
                documents_required='State ID, Land record, Aadhaar',
                benefit_amount='₹15,000/acre for replanting',
                official_link='http://www.indianspices.com'
            ),
        ]
        db.session.add_all(schemes)

    if LoanProduct.query.count() == 0:
        loans = [
            LoanProduct(
                loan_id='LN001', bank_name='State Bank of India',
                loan_type='Coffee Crop Loan', interest_rate_pct=7.0,
                max_amount_inr=500000, tenure_years=3,
                documents_required='Land record, Aadhaar, Income proof, Soil test report',
                eligibility_criteria=json.dumps({'crops': ['Coffee'], 'max_land_acres': 25})
            ),
            LoanProduct(
                loan_id='LN002', bank_name='Canara Bank',
                loan_type='Pepper Crop Loan', interest_rate_pct=6.5,
                max_amount_inr=300000, tenure_years=2,
                documents_required='Land record, Aadhaar, Soil test, Bank statement',
                eligibility_criteria=json.dumps({'crops': ['Pepper'], 'max_land_acres': 15})
            ),
            LoanProduct(
                loan_id='LN003', bank_name='Karnataka Bank',
                loan_type='Plantation Development Loan', interest_rate_pct=8.0,
                max_amount_inr=1000000, tenure_years=5,
                documents_required='Land record, Project report, Aadhaar',
                eligibility_criteria=json.dumps({'states': ['Karnataka'], 'max_land_acres': 30})
            ),
            LoanProduct(
                loan_id='LN004', bank_name='NABARD (via PACS)',
                loan_type='Kisan Credit Card', interest_rate_pct=4.0,
                max_amount_inr=200000, tenure_years=5,
                documents_required='Aadhaar, Land record, Passport photo',
                eligibility_criteria=json.dumps({'max_land_acres': 50})
            ),
            LoanProduct(
                loan_id='LN005', bank_name='Federal Bank',
                loan_type='Agri Gold Loan', interest_rate_pct=7.5,
                max_amount_inr=400000, tenure_years=3,
                documents_required='Land record, Aadhaar, Bank statement',
                eligibility_criteria=json.dumps({'states': ['Kerala', 'Karnataka', 'Tamil Nadu']})
            ),
        ]
        db.session.add_all(loans)

    db.session.commit()
    print('Seed data loaded successfully!')

# ==================== CARBON CREDIT MARKETPLACE ROUTES ====================

@app.route('/carbon/marketplace')
@login_required
def carbon_marketplace():
    if current_user.role not in ['buyer', 'farmer', 'admin']:
        return redirect(url_for('index'))
    
    pools = CarbonPool.query.filter_by(status='Open').all()
    purchases = []
    if current_user.role == 'buyer':
        purchases = CarbonPurchase.query.filter_by(buyer_id=current_user.id).all()
    
    # Get farmer's own carbon credits
    my_credits = None
    if current_user.role == 'farmer':
        my_credits = CarbonCredit.query.filter_by(farmer_id=current_user.id).first()
        
    return render_template('carbon_marketplace.html', pools=pools, purchases=purchases, my_credits=my_credits)


@app.route('/carbon/pool/create', methods=['POST'])
@login_required
def create_carbon_pool():
    if current_user.role != 'farmer':
        return redirect(url_for('index'))
    
    credit = CarbonCredit.query.filter_by(farmer_id=current_user.id).first()
    if not credit or credit.credits_earned <= 0:
        flash('You do not have any carbon credits to pool.', 'warning')
        return redirect(url_for('carbon_marketplace'))
    
    region = current_user.district or 'General'
    pool_name = f"{region} Plantation Carbon Pool"
    
    # Check if an open pool exists for this region
    pool = CarbonPool.query.filter_by(region=region, status='Open').first()
    
    if pool:
        pool.total_tonnes += credit.credits_earned
    else:
        pool = CarbonPool(name=pool_name, region=region, total_tonnes=credit.credits_earned)
        db.session.add(pool)
    
    # Mark credit as pooled (optional: set status)
    credit.verification_status = 'Pooled'
    db.session.commit()
    
    flash(f'Successfully added {credit.credits_earned} tonnes to the {pool_name}!', 'success')
    return redirect(url_for('carbon_marketplace'))


@app.route('/carbon/buy/<int:pool_id>', methods=['POST'])
@login_required
def buy_carbon_credits(pool_id):
    if current_user.role != 'buyer':
        return redirect(url_for('index'))
    
    pool = CarbonPool.query.get_or_404(pool_id)
    tonnes = float(request.form['tonnes'])
    
    if tonnes > pool.total_tonnes:
        flash('Not enough tonnes available in this pool.', 'danger')
        return redirect(url_for('carbon_marketplace'))
    
    total_amount = tonnes * pool.price_per_tonne
    
    # Generate tamper-proof hash (Blockchain-like)
    hash_input = f"{current_user.id}{pool.id}{tonnes}{datetime.utcnow()}"
    cert_hash = hashlib.sha256(hash_input.encode()).hexdigest()
    
    purchase = CarbonPurchase(
        buyer_id=current_user.id,
        pool_id=pool.id,
        tonnes_purchased=tonnes,
        total_amount=total_amount,
        certificate_hash=cert_hash
    )
    
    pool.total_tonnes -= tonnes
    if pool.total_tonnes <= 0:
        pool.status = 'Sold Out'
        
    db.session.add(purchase)
    db.session.commit()
    
    flash(f'Successfully purchased {tonnes} tonnes for ₹{total_amount:,.2f}! Certificate generated.', 'success')
    return redirect(url_for('carbon_marketplace'))


@app.route('/carbon/certificate/<int:purchase_id>')
@login_required
def download_carbon_certificate(purchase_id):
    purchase = CarbonPurchase.query.get_or_404(purchase_id)
    if purchase.buyer_id != current_user.id:
        flash('Unauthorized', 'danger')
        return redirect(url_for('carbon_marketplace'))
    
    pdf_buffer = generate_carbon_certificate(current_user, purchase)
    filename = f"carbon_certificate_{purchase.id}.pdf"
    return send_file(pdf_buffer, as_attachment=True, download_name=filename, mimetype='application/pdf')


# ==================== RUN APP ====================

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True, port=5001)