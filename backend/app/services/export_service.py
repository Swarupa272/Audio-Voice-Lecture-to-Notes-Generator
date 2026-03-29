from io import BytesIO
from typing import Tuple

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.pdfgen import canvas


def export_notes_as_text(title: str, notes_text: str) -> Tuple[bytes, str]:
    """
    Export notes as a UTF-8 encoded text file.

    Returns:
        file_bytes, filename
    """
    content = f"{title}\n\n{notes_text}".encode("utf-8")
    filename = "lecture_notes.txt"
    return content, filename


def export_notes_as_pdf(title: str, notes_text: str) -> Tuple[bytes, str]:
    """
    Export notes as a simple but readable PDF using reportlab.

    Returns:
        file_bytes, filename
    """
    buffer = BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4

    # Margins
    x_margin = 2 * cm
    y_margin = 2 * cm
    max_width = width - 2 * x_margin
    y = height - y_margin

    pdf.setTitle(title)

    # Title
    pdf.setFont("Helvetica-Bold", 16)
    pdf.drawString(x_margin, y, title)
    y -= 1.5 * cm

    pdf.setFont("Helvetica", 11)

    # Simple word-wrapped rendering of notes text
    for paragraph in notes_text.split("\n"):
        if not paragraph.strip():
            y -= 0.5 * cm
            continue

        text = pdf.beginText(x_margin, y)
        text.setFont("Helvetica", 11)

        words = paragraph.split(" ")
        line = ""
        for word in words:
            prospective = f"{line} {word}".strip()
            if pdf.stringWidth(prospective, "Helvetica", 11) <= max_width:
                line = prospective
            else:
                text.textLine(line)
                line = word
                y -= 0.5 * cm
                text.setTextOrigin(x_margin, y)

            if y <= y_margin:
                pdf.drawText(text)
                pdf.showPage()
                y = height - y_margin
                text = pdf.beginText(x_margin, y)
                text.setFont("Helvetica", 11)

        if line:
            text.textLine(line)
            y -= 0.5 * cm

        pdf.drawText(text)

        if y <= y_margin:
            pdf.showPage()
            y = height - y_margin

    pdf.showPage()
    pdf.save()
    buffer.seek(0)

    filename = "lecture_notes.pdf"
    return buffer.read(), filename

