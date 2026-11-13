import unittest

import pymupdf

from backend.services.pdf_processor import extract_pdf_information


def create_pdf(page_texts: list[str]) -> bytes:
    document = pymupdf.open()
    for text in page_texts:
        page = document.new_page()
        if text:
            page.insert_text((72, 72), text)
    pdf_bytes = document.tobytes()
    document.close()
    return pdf_bytes


class PDFExtractionTests(unittest.TestCase):
    def test_extracts_every_page_and_preserves_page_numbers(self) -> None:
        source_texts = [f"Page {page_number} has its own text." for page_number in range(1, 12)]
        result = extract_pdf_information(create_pdf(source_texts))

        self.assertEqual(result["page_count"], 11)
        self.assertEqual(
            [page["page_number"] for page in result["pages"]],
            list(range(1, 12)),
        )
        self.assertEqual(len(result["pages"]), 11)
        self.assertIn("Page 11 has its own text.", result["pages"][10]["text"])
        self.assertEqual(
            result["character_count"],
            sum(len(page["text"]) for page in result["pages"]),
        )

    def test_reports_empty_pages_without_dropping_them(self) -> None:
        result = extract_pdf_information(create_pdf(["First page.", "", "Third page."]))

        self.assertEqual(result["page_count"], 3)
        self.assertEqual(result["empty_pages"], [2])
        self.assertEqual([page["page_number"] for page in result["pages"]], [1, 2, 3])
        self.assertEqual(result["pages"][1]["text"], "")


if __name__ == "__main__":
    unittest.main()
