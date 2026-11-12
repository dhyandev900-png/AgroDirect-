import json
from datetime import date
from io import BytesIO
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib import colors

def check_scheme_eligibility(farmer, scheme):
    try:
        criteria = json.loads(scheme.eligibility_criteria) if scheme.eligibility_criteria else {}
    except: criteria = {}
    matched, missing = [], []
    if 'max_land_acres' in criteria:
        if farmer.land_size_acres and farmer.land_size_acres <= criteria['max_land_acres']: matched.append(f"Land size within limit")
        else: missing.append(f"Land must be ≤ {criteria['max_land_acres']} acres")
    if 'states' in criteria:
        if farmer.state in criteria['states']: matched.append(f"State eligible")
        else: missing.append(f"Only in: {', '.join(criteria['states'])}")
    if 'crops' in criteria:
        if farmer.crop_type and any(c in farmer.crop_type for c in criteria['crops']): matched.append(f"Crop eligible")
        else: missing.append(f"Only for: {', '.join(criteria['crops'])}")
    return len(missing) == 0, missing, matched

def check_loan_eligibility(farmer, loan):
    try:
        criteria = json.loads(loan.eligibility_criteria) if loan.eligibility_criteria else {}
    except: criteria = {}
    matched, missing = [], []
    if 'max_land_acres' in criteria:
        if farmer.land_size_acres and farmer.land_size_acres <= criteria['max_land_acres']: matched.append("Land within limit")
        else: missing.append(f"Land must be ≤ {criteria['max_land_acres']} acres")
    if 'states' in criteria and farmer.state not in criteria['states']: missing.append("State not eligible")
    if 'crops' in criteria and not (farmer.crop_type and any(c in farmer.crop_type for c in criteria['crops'])): missing.append("Crop not eligible")
    return len(missing) == 0, missing, matched

def calculate_loan(principal, annual_rate_pct, tenure_years):
    if principal <= 0 or tenure_years <= 0: return {'emi': 0, 'total_interest': 0, 'total_payment': 0, 'months': 0}
    monthly_rate = annual_rate_pct / 12 / 100
    months = tenure_years * 12
    emi = principal / months if monthly_rate == 0 else principal * monthly_rate * ((1 + monthly_rate) ** months) / (((1 + monthly_rate) ** months) - 1)
    total_payment = emi * months
    return {'emi': round(emi, 2), 'total_interest': round(total_payment - principal, 2), 'total_payment': round(total_payment, 2), 'months': months}

def estimate_max_loan(farmer, loan):
    if not farmer.land_size_acres: return 0
    per_acre = 40000 if 'Coffee' in (farmer.crop_type or '') else 30000
    return min(farmer.land_size_acres * per_acre, loan.max_amount_inr or (farmer.land_size_acres * per_acre))

def generate_application_pdf(farmer, item, item_type='scheme'):
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, topMargin=1.5*cm, bottomMargin=1.5*cm)
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle('TitleStyle', parent=styles['Title'], fontSize=18, textColor=colors.HexColor('#198754'), alignment=1)
    heading_style = ParagraphStyle('HeadingStyle', parent=styles['Heading2'], fontSize=14, textColor=colors.HexColor('#0f5132'), spaceBefore=15)
    normal = styles['Normal']
    
    story = []
    story.append(Paragraph("AgroDirect+ Application Guide", title_style))
    story.append(Spacer(1, 0.5*cm))
    story.append(Paragraph(f"<b>Prepared for:</b> {farmer.name} ({farmer.phone})", normal))
    story.append(Paragraph(f"<b>Date:</b> {date.today().strftime('%d-%m-%Y')}", normal))
    story.append(Spacer(1, 1*cm))

    if item_type == 'scheme':
        story.append(Paragraph(f"Scheme: {item.scheme_name}", heading_style))
        story.append(Paragraph(f"<b>Category:</b> {item.category}", normal))
        story.append(Paragraph(f"<b>Description:</b> {item.description}", normal))
        story.append(Paragraph(f"<b>Benefit:</b> {item.benefit_amount}", normal))
    else:
        story.append(Paragraph(f"Loan Product: {item.loan_type}", heading_style))
        story.append(Paragraph(f"<b>Bank/Institution:</b> {item.bank_name}", normal))
        story.append(Paragraph(f"<b>Interest Rate:</b> {item.interest_rate_pct}% p.a.", normal))
        story.append(Paragraph(f"<b>Max Amount:</b> Rs. {item.max_amount_inr:,.0f}", normal))

    story.append(Paragraph("Required Documents Checklist", heading_style))
    story.append(Paragraph("Please gather the following documents before visiting the bank/office:", normal))
    story.append(Spacer(1, 0.3*cm))
    
    docs = (item.documents_required or '').split(',')
    table_data = [['✔', 'Document Name']]
    for d in docs:
        if d.strip(): table_data.append(['☐', d.strip()])
            
    t = Table(table_data, colWidths=[1.5*cm, 13*cm])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#e8f5e9')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.HexColor('#0f5132')),
        ('ALIGN', (0, 0), (0, -1), 'CENTER'), ('GRID', (0, 0), (-1, -1), 0.5, colors.lightgrey),
        ('FONTSIZE', (0, 0), (-1, -1), 11), ('PADDING', (0, 0), (-1, -1), 8),
    ]))
    story.append(t)

    story.append(Paragraph("Step-by-Step Application Process", heading_style))
    steps = [
        "Gather all the documents listed in the checklist above. Ensure they are self-attested.",
        f"Visit the nearest branch of {item.bank_name if item_type == 'loan' else 'the designated government office/portal'}.",
        "Fill out the physical application form provided by the officer (or apply online if available).",
        "Attach your documents and submit the application. Ask for an acknowledgment receipt.",
        "Track your application status using the reference number."
    ]
    for i, step in enumerate(steps, 1):
        story.append(Paragraph(f"<b>Step {i}:</b> {step}", normal))
        story.append(Spacer(1, 0.2*cm))
        
    story.append(Spacer(1, 1.5*cm))
    story.append(Paragraph("Need help? Contact AgroDirect Support at support@agrodirect.com", ParagraphStyle('Footer', parent=normal, textColor=colors.grey, alignment=1)))
    doc.build(story)
    buffer.seek(0)
    return buffer

def generate_carbon_certificate(buyer, purchase):
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, topMargin=2*cm, bottomMargin=2*cm)
    styles = getSampleStyleSheet()
    
    # Custom styles
    title_style = ParagraphStyle('TitleStyle', parent=styles['Title'], fontSize=24, textColor=colors.HexColor('#198754'), alignment=1, spaceAfter=20)
    normal = styles['Normal']
    center = ParagraphStyle('Center', parent=normal, alignment=1, fontSize=12)
    name_style = ParagraphStyle('NameStyle', parent=normal, alignment=1, fontSize=18, fontName='Helvetica-Bold', spaceBefore=10, spaceAfter=10)
    
    story = []
    story.append(Spacer(1, 2*cm))
    
    # Title
    story.append(Paragraph("Certificate of Carbon Offset", title_style))
    story.append(Spacer(1, 1*cm))
    
    # Certification Text
    story.append(Paragraph("This certifies that", center))
    story.append(Spacer(1, 0.5*cm))
    
    # Buyer Name (Added spacing here to fix the overlap)
    buyer_name = buyer.company_name if buyer.company_name else buyer.name
    story.append(Paragraph(f"<b>{buyer_name}</b>", name_style))
    story.append(Spacer(1, 0.5*cm))
    
    # Replaced CO₂ with CO2 to fix the black box
    story.append(Paragraph(f"has successfully purchased <b>{purchase.tonnes_purchased} tonnes of CO2 equivalent</b>", center))
    story.append(Paragraph(f"from the <b>{purchase.pool.name}</b>", center))
    story.append(Spacer(1, 1.5*cm))
    
    # Table Data (Replaced ₹ with Rs. to fix the black box)
    data = [
        ['Transaction ID:', f'CP-{purchase.id:06d}'],
        ['Date of Purchase:', purchase.purchased_at.strftime('%d-%m-%Y')],
        ['Total Amount Paid:', f'Rs. {purchase.total_amount:,.2f}'],
        ['Certificate Hash (SHA-256):', purchase.certificate_hash],
    ]
    
    t = Table(data, colWidths=[5*cm, 10*cm])
    t.setStyle(TableStyle([
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#e8f5e9')),
        ('PADDING', (0, 0), (-1, -1), 10),
        ('FONTSIZE', (0, 0), (-1, -1), 11),
    ]))
    story.append(t)
    story.append(Spacer(1, 2.5*cm))
    
    # Footer Text
    story.append(Paragraph("This certificate verifies the environmental impact and can be used for ESG reporting.", center))
    story.append(Spacer(1, 0.5*cm))
    story.append(Paragraph("<i>Verified by AgroDirect+ Carbon Registry</i>", center))
    
    doc.build(story)
    buffer.seek(0)
    return buffer