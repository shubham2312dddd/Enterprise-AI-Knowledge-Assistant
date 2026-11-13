import pymupdf
from typing import TypedDict


PREVIEW_LENGTH = 500


class ExtractedPage(TypedDict):
    page_number: int
    text: str


class PDFExtraction(TypedDict):
    page_count: int
    character_count: int
    text_preview: str
    pages: list[ExtractedPage]
    empty_pages: list[int]


class InvalidPDFError(ValueError):
    """Raised when a PDF cannot be opened or read."""


def extract_pdf_information(pdf_bytes: bytes) -> PDFExtraction:
    document = None
    try:
        document = pymupdf.open(stream=pdf_bytes, filetype="pdf")
        if document.needs_pass:
            raise InvalidPDFError("Password-protected PDFs are not supported.")

        pages: list[ExtractedPage] = []
        empty_pages: list[int] = []
        for page_number, page in enumerate(document, start=1):
            page_text = page.get_text()
            pages.append({"page_number": page_number, "text": page_text})
            if not page_text.strip():
                empty_pages.append(page_number)

        extracted_text = "\n".join(page["text"] for page in pages)
    except InvalidPDFError:
        raise
    except (pymupdf.FileDataError, pymupdf.EmptyFileError, RuntimeError, ValueError) as error:
        raise InvalidPDFError("The uploaded file is not a readable PDF.") from error
    finally:
        if document is not None:
            document.close()

    return {
        "page_count": len(pages),
        "character_count": sum(len(page["text"]) for page in pages),
        "text_preview": extracted_text[:PREVIEW_LENGTH],
        "pages": pages,
        "empty_pages": empty_pages,
    }
