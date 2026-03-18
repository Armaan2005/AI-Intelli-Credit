from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet

def generate_report(data, filename="report.pdf"):
    doc = SimpleDocTemplate(filename)
    styles = getSampleStyleSheet()

    content = []

    content.append(Paragraph("Intelli-Credit AI Report", styles['Title']))
    content.append(Spacer(1, 20))

    content.append(Paragraph(f"Risk: {data['risk']}", styles['Normal']))
    content.append(Paragraph(f"Decision: {data['decision']}", styles['Normal']))
    content.append(Paragraph(f"Loan Amount: {data['loan_amount']}", styles['Normal']))
    content.append(Paragraph(f"Interest Rate: {data['interest_rate']}", styles['Normal']))
    content.append(Paragraph(f"Score: {data['score']}", styles['Normal']))

    content.append(Spacer(1, 20))

    content.append(Paragraph("Reasons:", styles['Heading2']))
    for r in data["reasons"]:
        content.append(Paragraph(f"- {r}", styles['Normal']))

    doc.build(content)

    return filename