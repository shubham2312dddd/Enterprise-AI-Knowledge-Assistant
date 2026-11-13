import unittest

from backend.services.text_chunker import chunk_pages


class TextChunkerTests(unittest.TestCase):
    def test_chunks_keep_page_numbers_and_configured_overlap(self) -> None:
        text = "0123456789" * 3 + "01234"
        chunks = chunk_pages(
            [{"page_number": 7, "text": text}],
            chunk_size=20,
            chunk_overlap=5,
        )

        self.assertEqual([chunk["page_number"] for chunk in chunks], [7, 7])
        self.assertEqual(chunks[0]["text"][-5:], chunks[1]["text"][:5])
        self.assertEqual([chunk["chunk_index"] for chunk in chunks], [0, 1])

    def test_empty_pages_and_duplicate_chunks_are_skipped(self) -> None:
        chunks = chunk_pages(
            [
                {"page_number": 1, "text": " \n "},
                {"page_number": 2, "text": "a" * 40},
            ],
            chunk_size=20,
            chunk_overlap=10,
        )

        self.assertEqual(len(chunks), 1)
        self.assertEqual(chunks[0]["page_number"], 2)

    def test_invalid_overlap_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            chunk_pages([{"page_number": 1, "text": "text"}], 10, 10)


if __name__ == "__main__":
    unittest.main()
