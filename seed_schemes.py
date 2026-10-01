from app import app, db, GovernmentScheme, LoanProduct
import json

with app.app_context():
    # Clear existing data (optional, for a fresh start)
    # db.session.query(GovernmentScheme).delete()
    # db.session.query(LoanProduct).delete()
    # db.session.commit()

    # --- Seed Government Schemes ---
    schemes = [
        GovernmentScheme(
            scheme_id='SC001',
            scheme_name='Integrated Coffee Development Project (ICDP)',
            category='Subsidy',
            crop='Coffee',
            description='Support for replanting, water augmentation, and infrastructure like drying yards and pulpers.',
            eligibility_criteria=json.dumps({'max_land_acres': 50, 'crops': ['Coffee']}),
            documents_required='Land records, Aadhaar, bank passbook, project report/quotation',
            benefit_amount='Varies by activity (e.g., 40% subsidy for machinery up to ₹15 lakh)',
            official_link='https://coffeeboard.gov.in/schemes.html'
        ),
        GovernmentScheme(
            scheme_id='SC002',
            scheme_name='SPICED Scheme',
            category='Subsidy',
            crop='Pepper',
            description='Provides assistance for post-harvest improvement, including pepper threshers and graders.',
            eligibility_criteria=json.dumps({'crops': ['Pepper'], 'max_land_acres': 25}),
            documents_required='Land documents, Aadhaar, bank details, quotations for machinery',
            benefit_amount='25% subsidy for general category; 35% for SC/ST, small & marginal farmers, and women',
            official_link='http://www.indianspices.com/schemes.html'
        ),
        GovernmentScheme(
            scheme_id='SC003',
            scheme_name='PM-KISAN',
            category='Income Support',
            crop='All',
            description='Direct income support to supplement the financial needs of landholding farmer families.',
            eligibility_criteria=json.dumps({'max_land_acres': 50}),
            documents_required='Aadhaar, land record documents, bank account details',
            benefit_amount='₹6,000 per year in three equal instalments of ₹2,000 each',
            official_link='https://pmkisan.gov.in'
        ),
        GovernmentScheme(
            scheme_id='SC004',
            scheme_name='MIDH - National Horticulture Mission (Pepper)',
            category='Subsidy',
            crop='Pepper',
            description='40% subsidy for planting material inputs for perennial spices like black pepper.',
            eligibility_criteria=json.dumps({'crops': ['Pepper'], 'max_land_acres': 10}),
            documents_required='Land records, Aadhaar, bank details, project proposal',
            benefit_amount='40% subsidy limited to ₹20,000 per hectare for a maximum of 4 hectares',
            official_link='https://midh.gov.in'
        ),
        GovernmentScheme(
            scheme_id='SC005',
            scheme_name='Agriculture Infrastructure Fund (AIF)',
            category='Loan-linked Subsidy',
            crop='All',
            description='Financing facility for post-harvest management infrastructure and community farming assets.',
            eligibility_criteria=json.dumps({'max_land_acres': 100}),
            documents_required='Project report, land documents, Aadhaar, bank details',
            benefit_amount='3% interest subvention on loans up to ₹2 crore for up to 7 years',
            official_link='https://agriinfra.dac.gov.in'
        ),
    ]
    db.session.add_all(schemes)

    # --- Seed Loan Products ---
    loans = [
        LoanProduct(
            loan_id='LN001',
            bank_name='Kisan Credit Card (KCC)',
            loan_type='Short-term Crop Loan',
            interest_rate_pct=7.0,
            max_amount_inr=300000,
            tenure_years=5,
            documents_required='Aadhaar, PAN, land records (Pattadar passbook, etc.), passport-size photo, crop details',
            eligibility_criteria=json.dumps({'max_land_acres': 50})
        ),
        LoanProduct(
            loan_id='LN002',
            bank_name='Canara Bank',
            loan_type='Plantation Loan',
            interest_rate_pct=8.0,
            max_amount_inr=1000000,
            tenure_years=5,
            documents_required='Original Coffee/Cardamom Registration Certificate (CRC/CDRC), land records, Aadhaar',
            eligibility_criteria=json.dumps({'crops': ['Coffee', 'Pepper'], 'max_land_acres': 25})
        ),
        LoanProduct(
            loan_id='LN003',
            bank_name='NABARD (Refinance)',
            loan_type='Long-term Investment Credit',
            interest_rate_pct=6.5,
            max_amount_inr=2000000,
            tenure_years=7,
            documents_required='Project report, land records, Aadhaar, bank details',
            eligibility_criteria=json.dumps({'crops': ['Coffee', 'Pepper']})
        ),
    ]
    db.session.add_all(loans)

    db.session.commit()
    print("Real-world schemes and loans seeded successfully!")