"""
NyayaFlow - Document Generation Utility
Step 3a: LLM-drafted Markdown legal document → formatted PDF via ReportLab

Exposes:
    generate_legal_document(doc_type, fields) -> bytes  (PDF bytes)
    SUPPORTED_DOC_TYPES                                 (dict of available templates)
"""

import os
import io
from datetime import datetime
from groq import Groq
from dotenv import load_dotenv

load_dotenv()

GROQ_MODEL = "llama-3.3-70b-versatile"

SUPPORTED_DOC_TYPES = {
    "rental_agreement":     "Residential Rental Agreement",
    "nda":                  "Non-Disclosure Agreement (NDA)",
    "freelance_contract":   "Freelance Service Agreement",
    "employment_offer":     "Employment Offer Letter",
    "vendor_agreement":     "Vendor / Supplier Agreement",
    "partnership_deed":     "Partnership Deed",
    "affidavit":            "General Affidavit",
}

DOC_PROMPTS = {
    "rental_agreement": """
Draft a complete, legally sound Residential Rental Agreement for India in formal English.
Use the following details:
- Landlord Name: {landlord_name}
- Tenant Name: {tenant_name}
- Property Address: {property_address}
- Monthly Rent: ₹{monthly_rent}
- Security Deposit: ₹{security_deposit}
- Lease Start Date: {start_date}
- Lease Duration: {duration_months} months
- State: {state}

Include clauses for: rent payment terms, maintenance responsibilities, termination notice period 
(as per local tenancy law of {state}), restrictions on subletting, dispute resolution.
Format with clear section headings. Output plain text suitable for a PDF.
""",

    "nda": """
Draft a comprehensive Non-Disclosure Agreement (NDA) suitable for Indian businesses.
Details:
- Disclosing Party: {disclosing_party}
- Receiving Party: {receiving_party}
- Purpose: {purpose}
- Duration of Confidentiality: {duration_years} years
- Governing Law: Laws of India and jurisdiction of {jurisdiction}

Include: definition of confidential information, exclusions, obligations of receiving party,
return/destruction of information, remedies for breach. Output clean plain text for PDF.
""",

    "freelance_contract": """
Draft a Freelance Service Agreement for India.
Details:
- Client Name: {client_name}
- Freelancer Name: {freelancer_name}
- Scope of Work: {scope_of_work}
- Project Fee: ₹{project_fee}
- Payment Terms: {payment_terms}
- Delivery Timeline: {timeline}
- Intellectual Property: IP transfers to client upon full payment.

Include: payment milestones, revision policy, termination clause, governing law (India).
Output clean plain text for PDF.
""",

    "employment_offer": """
Draft a formal Employment Offer Letter for an Indian company.
Details:
- Company Name: {company_name}
- Candidate Name: {candidate_name}
- Position: {position}
- Annual CTC: ₹{annual_ctc}
- Joining Date: {joining_date}
- Probation Period: {probation_months} months
- Reporting Manager: {reporting_manager}

Include: compensation breakdown, benefits summary, at-will clauses, confidentiality reminder.
Output clean plain text for PDF.
""",

    "affidavit": """
Draft a General Affidavit suitable for use in Indian courts/government offices.
Details:
- Deponent Name: {deponent_name}
- Deponent Address: {deponent_address}
- Statement of Facts: {statement_of_facts}
- Purpose: {purpose}
- Location: {location}
- Date: {date}

Format with proper legal affidavit structure: declaration, numbered statements, 
verification clause, signature block. Output clean plain text for PDF.
""",
}


# ─── LLM document drafting ────────────────────────────────────────────────────

def draft_document_text(doc_type: str, fields: dict) -> str:
    """Ask Groq to draft the legal document text from template + user fields."""
    if doc_type not in DOC_PROMPTS:
        raise ValueError(f"Unsupported doc type: {doc_type}")

    template = DOC_PROMPTS[doc_type]
    try:
        prompt = template.format(**fields)
    except KeyError as e:
        raise ValueError(f"Missing required field for {doc_type}: {e}")

    client = Groq(api_key=os.getenv("GROQ_API_KEY"))
    response = client.chat.completions.create(
        model=GROQ_MODEL,
        messages=[
            {
                "role": "system",
                "content": (
                    "You are a senior Indian corporate lawyer drafting legal documents. "
                    "Output only the document text. No preamble, no markdown backticks. "
                    "Use clear section headings in ALL CAPS. Number all clauses. "
                    "Include a signature block at the end."
                ),
            },
            {"role": "user", "content": prompt},
        ],
        temperature=0.1,
        max_tokens=2048,
    )
    return response.choices[0].message.content


# ─── PDF rendering with ReportLab ────────────────────────────────────────────

def text_to_pdf(title: str, document_text: str) -> bytes:
    """Render a plain-text legal document into a nicely formatted PDF."""
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import cm
    from reportlab.lib import colors
    from reportlab.platypus import (
        SimpleDocTemplate, Paragraph, Spacer, HRFlowable, Table, TableStyle
    )
    from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY, TA_LEFT

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        topMargin=2.5 * cm,
        bottomMargin=2.5 * cm,
        leftMargin=2.5 * cm,
        rightMargin=2.5 * cm,
    )

    styles = getSampleStyleSheet()

    # Custom styles
    title_style = ParagraphStyle(
        "DocTitle",
        parent=styles["Title"],
        fontSize=16,
        spaceAfter=6,
        alignment=TA_CENTER,
        fontName="Helvetica-Bold",
        textColor=colors.HexColor("#1a1a2e"),
    )
    heading_style = ParagraphStyle(
        "SectionHeading",
        parent=styles["Heading2"],
        fontSize=11,
        spaceBefore=14,
        spaceAfter=4,
        fontName="Helvetica-Bold",
        textColor=colors.HexColor("#16213e"),
    )
    body_style = ParagraphStyle(
        "Body",
        parent=styles["Normal"],
        fontSize=10,
        leading=16,
        spaceAfter=6,
        alignment=TA_JUSTIFY,
        fontName="Helvetica",
    )
    meta_style = ParagraphStyle(
        "Meta",
        parent=styles["Normal"],
        fontSize=8,
        textColor=colors.grey,
        alignment=TA_CENTER,
    )

    story = []

    # Header
    story.append(Spacer(1, 0.3 * cm))
    story.append(Paragraph("NYAYAFLOW", ParagraphStyle(
        "Brand", fontSize=9, alignment=TA_CENTER,
        textColor=colors.HexColor("#e63946"), fontName="Helvetica-Bold",
        spaceAfter=2,
    )))
    story.append(Paragraph(title.upper(), title_style))
    story.append(Paragraph(
        f"Generated on: {datetime.now().strftime('%d %B %Y, %I:%M %p IST')}",
        meta_style,
    ))
    story.append(Spacer(1, 0.3 * cm))
    story.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor("#e63946")))
    story.append(Spacer(1, 0.4 * cm))

    # Body: parse lines and apply styles
    lines = document_text.split("\n")
    for line in lines:
        line = line.strip()
        if not line:
            story.append(Spacer(1, 0.2 * cm))
            continue
        # ALL CAPS lines → section heading
        if line.isupper() and len(line) > 3:
            story.append(Paragraph(line, heading_style))
        # Numbered clauses
        elif line[0].isdigit() and (line[1] in (".", ")") or (len(line) > 2 and line[2] in (".", ")"))):
            story.append(Paragraph(line, body_style))
        else:
            story.append(Paragraph(line, body_style))

    # Footer disclaimer
    story.append(Spacer(1, 0.5 * cm))
    story.append(HRFlowable(width="100%", thickness=0.5, color=colors.grey))
    story.append(Spacer(1, 0.2 * cm))
    story.append(Paragraph(
        "⚠️ This document was generated by NyayaFlow AI. It provides a starting template and "
        "does not constitute professional legal advice. Please have this reviewed by a qualified "
        "advocate before execution.",
        ParagraphStyle(
            "Disclaimer", fontSize=8, textColor=colors.grey,
            alignment=TA_CENTER, leading=12,
        ),
    ))

    doc.build(story)
    buffer.seek(0)
    return buffer.read()


# ─── Public interface ─────────────────────────────────────────────────────────

def generate_legal_document(doc_type: str, fields: dict) -> bytes:
    """
    Full pipeline: fields → LLM draft → PDF bytes.
    Returns PDF as bytes for Flask to send as a file download.
    """
    title       = SUPPORTED_DOC_TYPES.get(doc_type, "Legal Document")
    doc_text    = draft_document_text(doc_type, fields)
    pdf_bytes   = text_to_pdf(title, doc_text)
    return pdf_bytes
