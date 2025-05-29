import pytest
import os
import logging
from pathlib import Path

from shandu.local_kb.document_parser import parse_document, extract_text_from_pdf, extract_text_from_docx, extract_text_from_txt

# Test data content (should match what's in the sample files)
SAMPLE_TXT_CONTENT_EXPECTED = [
    "This is a sample text file for testing the document parser.",
    "It contains multiple lines of text.",
    "The quick brown fox jumps over the lazy dog.",
    "UTF-8 characters are also supported: éàçüö.",
    "End of sample.txt."
]

SAMPLE_DOCX_CONTENT_EXPECTED = [
    "This is a sample DOCX document for testing.",
    "It has a few lines of text.",
    "The purpose is to verify DOCX parsing functionality.",
    "Special characters: éàçüö."
]

SAMPLE_PDF_CONTENT_EXPECTED = [
    "This is a sample PDF document for testing.",
    "It contains a few lines of text to verify PDF parsing.",
    "The quick brown fox jumps over the lazy dog.",
    "Special characters: éàçüö are included.",
    "End of sample PDF content."
]


# --- Tests for individual extractors ---

def test_extract_text_from_txt(sample_txt_path: Path):
    """Test TXT extraction."""
    content = extract_text_from_txt(str(sample_txt_path))
    assert content is not None
    # Normalize line endings and compare line by line for flexibility
    normalized_content_lines = [line.strip() for line in content.strip().splitlines()]
    normalized_expected_lines = [line.strip() for line in SAMPLE_TXT_CONTENT_EXPECTED]
    assert normalized_content_lines == normalized_expected_lines

def test_extract_text_from_docx(sample_docx_path: Path):
    """Test DOCX extraction."""
    if not os.path.exists(sample_docx_path):
        pytest.skip("sample.docx not found, skipping DOCX test.")
    
    try:
        import docx
    except ImportError:
        pytest.skip("python-docx library not installed, skipping DOCX test.")

    content = extract_text_from_docx(str(sample_docx_path))
    assert content is not None
    normalized_content_lines = [line.strip() for line in content.strip().splitlines() if line.strip()]
    normalized_expected_lines = [line.strip() for line in SAMPLE_DOCX_CONTENT_EXPECTED]
    assert normalized_content_lines == normalized_expected_lines

def test_extract_text_from_pdf(sample_pdf_path: Path):
    """Test PDF extraction."""
    if not os.path.exists(sample_pdf_path):
        pytest.skip("sample.pdf not found, skipping PDF test.")
    
    try:
        import PyPDF2
    except ImportError:
        pytest.skip("PyPDF2 library not installed, skipping PDF test.")

    content = extract_text_from_pdf(str(sample_pdf_path))
    assert content is not None
    
    # PDF text extraction can be tricky with exact formatting, so we check for keywords
    # and presence of lines rather than exact string match for the whole content.
    content_lower = content.lower()
    for expected_line_part in SAMPLE_PDF_CONTENT_EXPECTED:
        # Check for significant parts of each expected line
        # Making checks more robust to minor variations in PDF text extraction
        significant_words = expected_line_part.lower().split()
        if len(significant_words) > 2: # Take first few and last few words
             check_part = " ".join(significant_words[:2]) + ".*" + " ".join(significant_words[-2:])
        elif significant_words:
            check_part = significant_words[0]
        else:
            continue
        
        # A more lenient check: if the text contains the core parts of the expected lines
        # For example, if "This is a sample PDF document for testing." is expected,
        # check if "this is a sample" and "for testing" (or similar) are present.
        # This is still not perfect. True PDF content validation is complex.
        assert expected_line_part.lower().replace(" ", "") in content_lower.replace(" ", "").replace("\n", "")
        # A simpler check:
        # assert expected_line_part.lower() in content_lower


# --- Tests for main parse_document function ---

def test_parse_document_txt(sample_txt_path: Path):
    """Test parse_document with a TXT file."""
    content = parse_document(str(sample_txt_path))
    assert content is not None
    normalized_content_lines = [line.strip() for line in content.strip().splitlines()]
    normalized_expected_lines = [line.strip() for line in SAMPLE_TXT_CONTENT_EXPECTED]
    assert normalized_content_lines == normalized_expected_lines

def test_parse_document_docx(sample_docx_path: Path):
    """Test parse_document with a DOCX file."""
    if not os.path.exists(sample_docx_path):
        pytest.skip("sample.docx not found, skipping DOCX parse_document test.")
    try:
        import docx
    except ImportError:
        pytest.skip("python-docx library not installed, skipping DOCX parse_document test.")
        
    content = parse_document(str(sample_docx_path))
    assert content is not None
    normalized_content_lines = [line.strip() for line in content.strip().splitlines() if line.strip()]
    normalized_expected_lines = [line.strip() for line in SAMPLE_DOCX_CONTENT_EXPECTED]
    assert normalized_content_lines == normalized_expected_lines

def test_parse_document_pdf(sample_pdf_path: Path):
    """Test parse_document with a PDF file."""
    if not os.path.exists(sample_pdf_path):
        pytest.skip("sample.pdf not found, skipping PDF parse_document test.")
    try:
        import PyPDF2
    except ImportError:
        pytest.skip("PyPDF2 library not installed, skipping PDF parse_document test.")

    content = parse_document(str(sample_pdf_path))
    assert content is not None
    content_lower = content.lower()
    for expected_line_part in SAMPLE_PDF_CONTENT_EXPECTED:
         assert expected_line_part.lower().replace(" ", "") in content_lower.replace(" ", "").replace("\n", "")


def test_parse_document_empty_txt(empty_txt_path: Path):
    """Test parse_document with an empty TXT file."""
    content = parse_document(str(empty_txt_path))
    assert content == ""

def test_parse_document_non_existent_file(caplog):
    """Test parse_document with a non-existent file."""
    non_existent_path = "non_existent_file.txt"
    with caplog.at_level(logging.ERROR):
        content = parse_document(non_existent_path)
    assert content is None
    assert f"File not found during parsing: The file {non_existent_path} does not exist." in caplog.text

def test_parse_document_unsupported_file_type(unsupported_file_path: Path, caplog):
    """Test parse_document with an unsupported file type."""
    with caplog.at_level(logging.WARNING):
        content = parse_document(str(unsupported_file_path))
    assert content is None
    assert f"Unsupported file type for document: {str(unsupported_file_path)}" in caplog.text
    assert "extension: .unsupported" in caplog.text


# --- Tests for graceful failure (mocking needed for true corrupted/passworded files) ---
# These tests are basic and rely on the error handling within the parsers.
# True testing of corrupted/passworded files would require actual sample files.

def test_extract_text_from_pdf_corrupted_mock(tmp_path, caplog, monkeypatch):
    """Test PDF extraction failure on a mock corrupted/unreadable PDF."""
    if PyPDF2 is None:
        pytest.skip("PyPDF2 not installed, skipping mock corrupted PDF test.")

    # Create a dummy file that is not a valid PDF
    bad_pdf_path = tmp_path / "bad.pdf"
    bad_pdf_path.write_text("This is not a PDF.")

    # Option 1: Monkeypatch PyPDF2.PdfReader to raise an error
    class MockPdfReader:
        def __init__(self, stream):
            raise PyPDF2.errors.PdfReadError("Mocked PDF read error")
    
    if 'PyPDF2' in globals() and PyPDF2 is not None: # Check if PyPDF2 was successfully imported
        monkeypatch.setattr("PyPDF2.PdfReader", MockPdfReader)
        with caplog.at_level(logging.ERROR):
            content = extract_text_from_pdf(str(bad_pdf_path))
        assert content == ""
        assert f"Error reading PDF file {str(bad_pdf_path)}" in caplog.text
        assert "Mocked PDF read error" in caplog.text
    else: # PyPDF2 was not imported due to import error in document_parser.py
        with caplog.at_level(logging.ERROR):
             content = extract_text_from_pdf(str(bad_pdf_path))
        assert content == ""
        assert "PyPDF2 library is not installed" in caplog.text # Check for the initial warning/error

def test_extract_text_from_docx_corrupted_mock(tmp_path, caplog, monkeypatch):
    """Test DOCX extraction failure on a mock corrupted DOCX."""
    if docx is None:
        pytest.skip("python-docx not installed, skipping mock corrupted DOCX test.")

    bad_docx_path = tmp_path / "bad.docx"
    bad_docx_path.write_text("This is not a real DOCX file, just plain text.")

    # Monkeypatch docx.Document to raise an error typical for corrupted files
    # The actual error can vary, so we use a generic Exception for this mock.
    def mock_docx_document(path):
        raise Exception("Mocked DOCX loading error (e.g., package not found)")

    if 'docx' in globals() and docx is not None:
        monkeypatch.setattr("docx.Document", mock_docx_document)
        with caplog.at_level(logging.ERROR):
            content = extract_text_from_docx(str(bad_docx_path))
        assert content == ""
        assert f"An unexpected error occurred while parsing DOCX file {str(bad_docx_path)}" in caplog.text
        assert "Mocked DOCX loading error" in caplog.text
    else:
         with caplog.at_level(logging.ERROR):
            content = extract_text_from_docx(str(bad_docx_path))
         assert content == ""
         assert "python-docx library is not installed" in caplog.text
