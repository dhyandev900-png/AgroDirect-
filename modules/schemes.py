import json
from datetime import datetime, date
from io import BytesIO

from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib import colors


# ==================== ELIGIBILITY ENGINE ====================

def check_scheme_eligibility(farmer, scheme):
    """
    Evaluate whether a farmer is eligible for a scheme.
    Returns: (is_eligible: bool, missing_criteria: list, matched_criteria: list)
    """
    try:
        criteria = json.loads(scheme.eligibility_criteria) if scheme.eligibility_criteria else {}
    except (json.JSONDecodeError, TypeError):
        criteria = {}

    matched = []
    missing = []

    # Max land size
    if 'max_land_acres' in criteria:
        if farmer.land_size_acres and farmer.land_size_acres <= criteria['max_land_acres']:
            matched.append(f"Land size ({farmer.land_size_acres} acres) within limit")
        else:
            missing.append(f"Land must be ≤ {criteria['max_land_acres']} acres")

    # Min land size
    if 'min_land_acres' in criteria:
        if farmer.land_size_acres and farmer.land_size_acres >= criteria['min_land_acres']:
            matched.append(f"Land size meets minimum requirement")
        else:
            missing.append(f"Land must be ≥ {criteria['min_land_acres']} acres")

    # State
    if 'states' in criteria:
        if farmer.state in criteria['states']:
            matched.append(f"State ({farmer.state}) is eligible")
        else:
            missing.append(f"Only available in: {', '.join(criteria['states'])}")

    # Crop type
    if 'crops' in criteria:
        if farmer.crop_type and any(c in farmer.crop_type for c in criteria['crops']):
            matched.append(f"Crop type ({farmer.crop_type}) is eligible")
        else:
            missing.append(f"Only for: {', '.join(criteria['crops'])}")

    # Min experience
    if 'min_experience_years' in criteria:
        if farmer.years_experience and farmer.years_experience >= criteria['min_experience_years']:
            matched.append(f"Experience ({farmer.years_experience} years) sufficient")
        else:
            missing.append(f"Minimum {criteria['min_experience_years']} years experience required")

    # Shade percentage (for carbon / sustainability schemes)
    if 'min_shade_percentage' in criteria:
        if farmer.shade_percentage and farmer.shade_percentage >= criteria['min_shade_percentage']:
            matched.append(f"Shade percentage meets requirement")
        else:
            missing.append(f"Shade ≥ {criteria['min_shade_percentage']}% required")

    is_eligible = len(missing) == 0
    return is_eligible, missing, matched


def check_loan_eligibility(farmer, loan):
    """Similar logic for loan products."""
    try:
        criteria = json.loads(loan.eligibility_criteria) if loan.eligibility_criteria else {}
    except (json.JSONDecodeError, TypeError):
        criteria = {}

    matched = []
    missing = []

    if 'max_land_acres' in criteria:
        if farmer.land_size_acres and farmer.land_size_acres <= criteria['max_land_acres']:
            matched.append("Land size within limit")
        else:
            missing.append(f"Land must be ≤ {criteria['max_land_acres']} acres")

    if 'states' in criteria and farmer.state not in criteria['states']:
        missing.append(f"Only in: {', '.join(criteria['states'])}")

    if 'crops' in criteria:
        if not (farmer.crop_type and any(c in farmer.crop_type for c in criteria['crops'])):
            missing.append(f"Only for: {', '.join(criteria['crops'])}")

    return len(missing) == 0, missing, matched


# ==================== LOAN CALCULATOR ====================

def calculate_loan(principal, annual_rate_pct, tenure_years):
    """EMI and total repayment calculation."""
    if principal <= 0 or tenure_years <= 0:
        return {'emi': 0, 'total_interest': 0, 'total_payment': 0, 'months': 0}

    monthly_rate = annual_rate_pct / 12 / 100
    months = tenure_years * 12
    if monthly_rate == 0:
        emi = principal / months
    else:
        emi = principal * monthly_rate * ((1 + monthly_rate) ** months) / (((1 + monthly_rate) ** months) - 1)

    total_payment = emi * months
    total_interest = total_payment - principal

    return {
        'emi': round(emi, 2),
        'total_interest': round(total_interest, 2),
        'total_payment': round(total_payment, 2),
        'months': months
    }


def estimate_max_loan(farmer, loan):
    """Estimate maximum loan amount based on land size and crop."""
    if not farmer.land_size_acres:
        return 0
    # Rough heuristic: ₹40,000 per acre for coffee, ₹30,000 for pepper
    per_acre = 40000 if 'Coffee' in (farmer.crop_type or '') else 30000
    estimated = farmer.land_size_acres * per_acre
    return min(estimated, loan.max_amount_inr or estimated)


# ==================== PDF FORM GENERATION ====================

def generate_application_pdf(farmer, item, item_type='scheme'):
    """Generate a pre-filled PDF application form."""
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, topMargin=1.5*cm, bottomMargin=1.5*cm)
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle('TitleStyle', parent=styles['Title'], fontSize=16, textColor=colors.HexColor('#198754'))
    heading_style = ParagraphStyle('HeadingStyle', parent=styles['Heading2'], fontSize=12, textColor=colors.HexColor('#198754'))
    normal = styles['Normal']

    story = []
    story.append(Paragraph("AgroDirect+ Application Form", title_style))
    story.append(Spacer(1, 0.5*cm))
    story.append(Paragraph(f"Type: {item_type.upper()}", normal))
    story.append(Paragraph(f"Date: {date.today().strftime('%d-%m-%Y')}", normal))
    story.append(Spacer(1, 0.5*cm))

    story.append(Paragraph("Applicant Details", heading_style))
    applicant_data = [
        ['Name', farmer.name or ''],
        ['Email', farmer.email or ''],
        ['Phone', farmer.phone or ''],
        ['State', farmer.state or ''],
        ['District', farmer.district or ''],
        ['Land Size (acres)', str(farmer.land_size_acres or '')],
        ['Crop Type', farmer.crop_type or ''],
        ['Experience (years)', str(farmer.years_experience or '')],
    ]
    t = Table(applicant_data, colWidths=[5*cm, 10*cm])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#e8f5e9')),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('PADDING', (0, 0), (-1, -1), 6),
    ]))
    story.append(t)
    story.append(Spacer(1, 0.5*cm))

    if item_type == 'scheme':
        story.append(Paragraph("Scheme Details", heading_style))
        item_data = [
            ['Scheme Name', item.scheme_name or ''],
            ['Category', item.category or ''],
            ['Crop', item.crop or ''],
            ['Benefit', item.benefit_amount or ''],
            ['Description', item.description or ''],
        ]
    else:
        story.append(Paragraph("Loan Details", heading_style))
        item_data = [
            ['Bank', item.bank_name or ''],
            ['Loan Type', item.loan_type or ''],
            ['Interest Rate', f"{item.interest_rate_pct}% p.a." if item.interest_rate_pct else ''],
            ['Max Amount', f"₹{item.max_amount_inr:,.0f}" if item.max_amount_inr else ''],
            ['Tenure', f"{item.tenure_years} years" if item.tenure_years else ''],
        ]

    t2 = Table(item_data, colWidths=[5*cm, 10*cm])
    t2.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#e3f2fd')),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('PADDING', (0, 0), (-1, -1), 6),
    ]))
    story.append(t2)
    story.append(Spacer(1, 0.5*cm))

    story.append(Paragraph("Documents Required", heading_style))
    docs = (item.documents_required or '').split(',')
    for d in docs:
        d = d.strip()
        if d:
            story.append(Paragraph(f"• {d}", normal))
    story.append(Spacer(1, 1*cm))

    story.append(Paragraph("Declaration", heading_style))
    story.append(Paragraph(
        "I hereby declare that the information provided above is true and correct to the best of my knowledge. "
        "I understand that any false information may lead to rejection of my application.", normal))
    story.append(Spacer(1, 1.5*cm))

    sign_data = [['_________________________', '_________________________'],
                 ['Applicant Signature', 'Date']]
    sign_table = Table(sign_data, colWidths=[7.5*cm, 7.5*cm])
    sign_table.setStyle(TableStyle([('FONTSIZE', (0, 0), (-1, -1), 10)]))
    story.append(sign_table)

    doc.build(story)
    buffer.seek(0)
    return buffer

# ==================== CARBON CERTIFICATE GENERATOR ====================

def generate_carbon_certificate(buyer, purchase):
    """Generate a PDF certificate for carbon credit purchase."""
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, topMargin=2*cm, bottomMargin=2*cm)
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle('TitleStyle', parent=styles['Title'], fontSize=22, textColor=colors.HexColor('#198754'), alignment=1)
    normal = styles['Normal']
    center = ParagraphStyle('Center', parent=normal, alignment=1)
    
    story = []
    story.append(Spacer(1, 2*cm))
    story.append(Paragraph("Certificate of Carbon Offset", title_style))
    story.append(Spacer(1, 1*cm))
    
    story.append(Paragraph("This certifies that", center))
    story.append(Spacer(1, 0.5*cm))
    story.append(Paragraph(f"<b>{buyer.company_name}</b>", ParagraphStyle('Company', parent=normal, fontSize=16, alignment=1)))
    story.append(Spacer(1, 0.5*cm))
    story.append(Paragraph(f"has successfully purchased <b>{purchase.tonnes_purchased} tonnes of CO₂ equivalent</b>", center))
    story.append(Paragraph(f"from the <b>{purchase.pool.name}</b>", center))
    story.append(Spacer(1, 1*cm))
    
    data = [
        ['Transaction ID:', f'CP-{purchase.id:06d}'],
        ['Date of Purchase:', purchase.purchased_at.strftime('%d-%m-%Y')],
        ['Total Amount Paid:', f'₹{purchase.total_amount:,.2f}'],
        ['Certificate Hash (SHA-256):', purchase.certificate_hash],
    ]
    t = Table(data, colWidths=[5*cm, 10*cm])
    t.setStyle(TableStyle([
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#e8f5e9')),
        ('PADDING', (0, 0), (-1, -1), 8),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
    ]))
    story.append(t)
    story.append(Spacer(1, 2*cm))
    
    story.append(Paragraph("This certificate verifies the environmental impact and can be used for ESG reporting.", center))
    story.append(Spacer(1, 1*cm))
    story.append(Paragraph("<i>Verified by AgroDirect+ Carbon Registry</i>", center))
    
    doc.build(story)
    buffer.seek(0)
    return buffer