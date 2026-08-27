import io
import os
import sys
import pytest

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from fastapi import status
from fastapi.testclient import TestClient
from pypdf import PdfWriter

from app.core.config import settings
from app.db.models import DocumentRecord, DocumentStatus
from app.engine.ingestion.indexing_service import sanitize_filename, validate_pdf_content
from app.main import app


def create_sample_pdf_bytes() -> bytes:
    """Helper to generate a valid minimal PDF in-memory using pypdf."""
    writer = PdfWriter()
    writer.add_blank_page(width=612, height=792)
    buf = io.BytesIO()
    writer.write(buf)
    buf.seek(0)
    return buf.read()


def create_pdf_with_text_bytes(text_lines: list[str]) -> bytes:
    """Generate a valid minimal PDF containing actual text lines for RAG testing."""
    stream_parts = []
    y = 750
    for line in text_lines:
        safe_line = line.replace("(", "").replace(")", "")
        stream_parts.append(f"BT /F1 12 Tf 50 {y} Td ({safe_line}) Tj ET")
        y -= 25
    stream_data = "\n".join(stream_parts).encode("latin-1")

    pdf_content = (
        b"%PDF-1.4\n"
        b"1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n"
        b"2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n"
        b"3 0 obj\n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>\nendobj\n"
        b"4 0 obj\n<< /Length " + str(len(stream_data)).encode("ascii") + b" >>\nstream\n" + stream_data + b"\nendstream\nendobj\n"
        b"5 0 obj\n<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>\nendobj\n"
        b"xref\n0 6\n0000000000 65535 f \n0000000009 00000 n \n0000000058 00000 n \n0000000115 00000 n \n0000000244 00000 n \n0000000400 00000 n \ntrailer\n<< /Size 6 /Root 1 0 R >>\nstartxref\n470\n%%EOF\n"
    )
    return pdf_content


@pytest.fixture(scope="module")
def client():
    return TestClient(app)


def test_validate_pdf_content():
    """Test PDF content validation logic."""
    # Invalid extension
    with pytest.raises(ValueError, match="Invalid file extension"):
        validate_pdf_content(b"%PDF-1.4 dummy", "report.txt")

    # Empty content
    with pytest.raises(ValueError, match="empty or corrupted"):
        validate_pdf_content(b"", "report.pdf")

    # Invalid header (not starting with %PDF-)
    with pytest.raises(ValueError, match="valid PDF specification"):
        validate_pdf_content(b"NOT_A_PDF_DATA", "report.pdf")

    # Valid PDF bytes
    valid_bytes = create_sample_pdf_bytes()
    validate_pdf_content(valid_bytes, "valid_report.pdf")


def test_sanitize_filename():
    """Test filename sanitization against path traversal."""
    assert sanitize_filename("../../../etc/passwd.pdf") == "passwd.pdf"
    assert sanitize_filename("my report (2024) [v1].pdf") == "my_report__2024___v1_.pdf"
    assert sanitize_filename("financial_report") == "financial_report.pdf"


def test_list_documents_endpoint(client):
    """Test GET /api/v1/documents returns registry list."""
    response = client.get("/api/v1/documents")
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert "total" in data
    assert "ready_count" in data
    assert "documents" in data
    assert isinstance(data["documents"], list)


def test_upload_invalid_file_rejected(client):
    """Test upload endpoint rejects non-PDF or corrupt files."""
    # Reject text file
    response = client.post(
        "/api/v1/documents/upload",
        files={"file": ("malicious.txt", b"plain text", "text/plain")},
    )
    assert response.status_code == status.HTTP_400_BAD_REQUEST

    # Reject corrupt header
    response = client.post(
        "/api/v1/documents/upload",
        files={"file": ("fake.pdf", b"NOT_PDF_HEADER", "application/pdf")},
    )
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "valid PDF specification" in response.json()["detail"]


def test_upload_valid_pdf(client):
    """Test uploading a valid financial PDF."""
    pdf_bytes = create_sample_pdf_bytes()

    response = client.post(
        "/api/v1/documents/upload",
        files={"file": ("Test_Corp_Q4_Sample.pdf", pdf_bytes, "application/pdf")},
    )

    assert response.status_code in [status.HTTP_201_CREATED, status.HTTP_200_OK]
    data = response.json()
    assert "document" in data
    doc = data["document"]
    assert doc["original_filename"] == "Test_Corp_Q4_Sample.pdf"
    assert doc["processing_status"] in ["PENDING", "PROCESSING", "READY"]
    assert doc["id"] > 0

    # Retrieve individual document
    get_res = client.get(f"/api/v1/documents/{doc['id']}")
    assert get_res.status_code == status.HTTP_200_OK
    assert get_res.json()["id"] == doc["id"]


def test_get_nonexistent_document(client):
    """Test 404 for missing document ID."""
    response = client.get("/api/v1/documents/999999")
    assert response.status_code == status.HTTP_404_NOT_FOUND
