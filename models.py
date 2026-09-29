from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime

# Initialize the database object here so it can be imported by app.py
db = SQLAlchemy()

# ==================== USER MANAGEMENT ====================

class User(UserMixin, db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    role = db.Column(db.String(20), nullable=False)  # 'farmer', 'buyer', 'admin'
    name = db.Column(db.String(100), nullable=False)
    phone = db.Column(db.String(15))
    state = db.Column(db.String(50))
    district = db.Column(db.String(50))
    language = db.Column(db.String(20), default='English')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Farmer-specific fields
    land_size_acres = db.Column(db.Float)
    crop_type = db.Column(db.String(50))
    years_experience = db.Column(db.Integer)
    tree_count = db.Column(db.Integer)
    shade_percentage = db.Column(db.Float)
    
    # Buyer-specific fields
    company_name = db.Column(db.String(150))
    gst_number = db.Column(db.String(20))
    buyer_type = db.Column(db.String(50))
    is_verified = db.Column(db.Boolean, default=False)


# ==================== MARKETPLACE ====================

class Listing(db.Model):
    __tablename__ = 'listings'
    id = db.Column(db.Integer, primary_key=True)
    farmer_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    crop_type = db.Column(db.String(50), nullable=False)
    grade = db.Column(db.String(50))
    quantity_kg = db.Column(db.Float, nullable=False)
    expected_price_per_kg = db.Column(db.Float, nullable=False)
    harvest_date = db.Column(db.Date)
    description = db.Column(db.Text)
    status = db.Column(db.String(20), default='Active')  # Active, Sold, Expired
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    farmer = db.relationship('User', backref='listings')


class Order(db.Model):
    __tablename__ = 'orders'
    id = db.Column(db.Integer, primary_key=True)
    listing_id = db.Column(db.Integer, db.ForeignKey('listings.id'), nullable=False)
    buyer_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    quantity_kg = db.Column(db.Float, nullable=False)
    offered_price_per_kg = db.Column(db.Float, nullable=False)
    total_amount = db.Column(db.Float, nullable=False)
    status = db.Column(db.String(20), default='Pending')  # Pending, Accepted, Rejected, Completed
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    listing = db.relationship('Listing', backref='orders')
    buyer = db.relationship('User', backref='orders')


# ==================== CARBON CREDITS ====================

class CarbonCredit(db.Model):
    __tablename__ = 'carbon_credits'
    id = db.Column(db.Integer, primary_key=True)
    farmer_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    estimated_tonnes = db.Column(db.Float, nullable=False)
    credits_earned = db.Column(db.Float, nullable=False)
    verification_status = db.Column(db.String(20), default='Pending')
    year = db.Column(db.Integer, default=2026)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    farmer = db.relationship('User', backref='carbon_credits')


# ==================== CROP ADVISORY ====================

class SoilReport(db.Model):
    __tablename__ = 'soil_reports'
    id = db.Column(db.Integer, primary_key=True)
    farmer_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    soil_ph = db.Column(db.Float)
    organic_carbon_pct = db.Column(db.Float)
    nitrogen_kg_ha = db.Column(db.Float)
    phosphorus_kg_ha = db.Column(db.Float)
    potassium_kg_ha = db.Column(db.Float)
    zinc_ppm = db.Column(db.Float)
    boron_ppm = db.Column(db.Float)
    test_date = db.Column(db.Date)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    farmer = db.relationship('User', backref='soil_reports')


class AdvisoryLog(db.Model):
    __tablename__ = 'advisory_logs'
    id = db.Column(db.Integer, primary_key=True)
    farmer_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    advisory_type = db.Column(db.String(50))  # fertilizer, irrigation, pest
    recommendation = db.Column(db.Text)
    weather_summary = db.Column(db.Text)
    soil_summary = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    farmer = db.relationship('User', backref='advisory_logs')


class CropStage(db.Model):
    __tablename__ = 'crop_stages'
    id = db.Column(db.Integer, primary_key=True)
    farmer_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    crop_type = db.Column(db.String(50))
    current_stage = db.Column(db.String(50))  # flowering, fruiting, harvesting, vegetative
    stage_start_date = db.Column(db.Date)
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    farmer = db.relationship('User', backref='crop_stages')


# ==================== LOAN & SCHEME MODELS ====================

class GovernmentScheme(db.Model):
    __tablename__ = 'government_schemes'
    id = db.Column(db.Integer, primary_key=True)
    scheme_id = db.Column(db.String(20), unique=True)
    scheme_name = db.Column(db.String(200), nullable=False)
    category = db.Column(db.String(50))  # Subsidy, Grant, Income Support, Loan
    crop = db.Column(db.String(50))
    description = db.Column(db.Text)
    eligibility_criteria = db.Column(db.Text)   # JSON string
    documents_required = db.Column(db.Text)
    benefit_amount = db.Column(db.String(100))
    deadline = db.Column(db.Date)
    official_link = db.Column(db.String(300))


class LoanProduct(db.Model):
    __tablename__ = 'loan_products'
    id = db.Column(db.Integer, primary_key=True)
    loan_id = db.Column(db.String(20), unique=True)
    bank_name = db.Column(db.String(150))
    loan_type = db.Column(db.String(100))
    interest_rate_pct = db.Column(db.Float)
    max_amount_inr = db.Column(db.Float)
    tenure_years = db.Column(db.Integer)
    documents_required = db.Column(db.Text)
    eligibility_criteria = db.Column(db.Text)  # JSON string


class SchemeApplication(db.Model):
    __tablename__ = 'scheme_applications'
    id = db.Column(db.Integer, primary_key=True)
    farmer_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    scheme_id = db.Column(db.Integer, db.ForeignKey('government_schemes.id'))
    loan_id = db.Column(db.Integer, db.ForeignKey('loan_products.id'))
    application_type = db.Column(db.String(20))  # 'scheme' or 'loan'
    status = db.Column(db.String(20), default='Submitted')
    applied_at = db.Column(db.DateTime, default=datetime.utcnow)
    notes = db.Column(db.Text)

    farmer = db.relationship('User', backref='applications')
    scheme = db.relationship('GovernmentScheme')
    loan = db.relationship('LoanProduct')
    
# ==================== CARBON CREDIT MARKETPLACE ====================

class CarbonPool(db.Model):
    __tablename__ = 'carbon_pools'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False)
    region = db.Column(db.String(100))  # e.g., Chikmagalur
    total_tonnes = db.Column(db.Float, default=0.0)
    price_per_tonne = db.Column(db.Float, default=650.0)  # ₹650/tonne
    status = db.Column(db.String(20), default='Open')  # Open, Sold Out
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class CarbonPurchase(db.Model):
    __tablename__ = 'carbon_purchases'
    id = db.Column(db.Integer, primary_key=True)
    buyer_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    pool_id = db.Column(db.Integer, db.ForeignKey('carbon_pools.id'), nullable=False)
    tonnes_purchased = db.Column(db.Float, nullable=False)
    total_amount = db.Column(db.Float, nullable=False)
    certificate_hash = db.Column(db.String(64))  # SHA-256 hash for tamper-proofing
    purchased_at = db.Column(db.DateTime, default=datetime.utcnow)

    buyer = db.relationship('User', backref='carbon_purchases')
    pool = db.relationship('CarbonPool', backref='purchases')    