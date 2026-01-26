"""
Unit tests for file_processor.py - File text extraction and translation.
"""
import os
import sys
import tempfile
import pytest
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.core.file_processor import FileProcessor


class TestTextExtraction:
    """Tests for text extraction methods."""

    def test_extract_txt_utf8(self, sample_txt_file):
        """Test extracting text from UTF-8 .txt file."""
        mock_api = MagicMock()
        processor = FileProcessor(mock_api)

        text = processor.extract_text(sample_txt_file)

        assert "Hello World" in text
        assert "This is a test file" in text

    def test_extract_txt_with_encoding_detection(self):
        """Test text extraction with encoding detection."""
        # Create file with different encoding
        content = "こんにちは世界"  # Japanese text
        with tempfile.NamedTemporaryFile(mode='wb', suffix='.txt', delete=False) as f:
            f.write(content.encode('utf-8'))
            temp_path = f.name

        try:
            mock_api = MagicMock()
            processor = FileProcessor(mock_api)

            text = processor.extract_text(temp_path)
            assert "こんにちは世界" in text
        finally:
            os.unlink(temp_path)

    def test_extract_srt_preserves_structure(self, sample_srt_file):
        """Test that SRT extraction preserves subtitle structure."""
        mock_api = MagicMock()
        processor = FileProcessor(mock_api)

        text = processor.extract_text(sample_srt_file)

        # Should contain subtitle text
        assert "subtitle one" in text
        assert "subtitle two" in text

    def test_extract_unsupported_format_raises(self):
        """Test that unsupported format raises ValueError."""
        with tempfile.NamedTemporaryFile(suffix='.xyz', delete=False) as f:
            temp_path = f.name

        try:
            mock_api = MagicMock()
            processor = FileProcessor(mock_api)

            with pytest.raises(ValueError) as exc:
                processor.extract_text(temp_path)

            assert "Unsupported file format" in str(exc.value)
        finally:
            os.unlink(temp_path)

    def test_extract_missing_file_raises(self):
        """Test that missing file raises FileNotFoundError."""
        mock_api = MagicMock()
        processor = FileProcessor(mock_api)

        with pytest.raises(FileNotFoundError):
            processor.extract_text('/nonexistent/file.txt')

    @patch('src.core.file_processor.docx')
    def test_extract_docx(self, mock_docx):
        """Test DOCX extraction."""
        # Create temp file
        with tempfile.NamedTemporaryFile(suffix='.docx', delete=False) as f:
            temp_path = f.name

        try:
            # Mock docx module
            mock_doc = MagicMock()
            mock_para1 = MagicMock()
            mock_para1.text = "First paragraph"
            mock_para2 = MagicMock()
            mock_para2.text = "Second paragraph"
            mock_doc.paragraphs = [mock_para1, mock_para2]
            mock_docx.Document.return_value = mock_doc

            mock_api = MagicMock()
            processor = FileProcessor(mock_api)

            text = processor.extract_text(temp_path)

            assert "First paragraph" in text
            assert "Second paragraph" in text
        finally:
            os.unlink(temp_path)


class TestTextChunking:
    """Tests for text chunking logic."""

    def test_chunk_small_text(self):
        """Test that small text stays in one chunk."""
        mock_api = MagicMock()
        processor = FileProcessor(mock_api)

        text = "Small text here"
        chunks = processor._chunk_text(text)

        assert len(chunks) == 1
        assert "Small text" in chunks[0]

    def test_chunk_large_text(self):
        """Test that large text is split into chunks."""
        mock_api = MagicMock()
        processor = FileProcessor(mock_api)

        # Create text larger than MAX_CHUNK_SIZE
        large_text = "Line of text.\n" * 500  # Each line ~15 chars
        chunks = processor._chunk_text(large_text)

        assert len(chunks) > 1
        # All chunks should be under max size (with some tolerance for boundaries)
        for chunk in chunks:
            assert len(chunk) <= processor.MAX_CHUNK_SIZE + 100

    def test_chunk_preserves_line_structure(self):
        """Test that chunking preserves line boundaries."""
        mock_api = MagicMock()
        processor = FileProcessor(mock_api)

        text = "Line 1\nLine 2\nLine 3\n"
        chunks = processor._chunk_text(text)

        # Reassembled should roughly match original
        reassembled = ''.join(chunks)
        assert "Line 1" in reassembled
        assert "Line 2" in reassembled
        assert "Line 3" in reassembled


class TestFileTranslation:
    """Tests for file translation."""

    def test_translate_file_calls_api(self, sample_txt_file):
        """Test that translate_file calls API for each chunk."""
        mock_api = MagicMock()
        mock_api.translate.return_value = "Translated text"
        processor = FileProcessor(mock_api)

        result = processor.translate_file(sample_txt_file, "Vietnamese")

        assert mock_api.translate.called
        assert "Translated text" in result

    def test_translate_file_progress_callback(self, sample_txt_file):
        """Test that progress callback is called."""
        mock_api = MagicMock()
        mock_api.translate.return_value = "OK"
        processor = FileProcessor(mock_api)

        callback = MagicMock()

        processor.translate_file(sample_txt_file, "English", progress_callback=callback)

        # Callback should be called at least once
        assert callback.called

    def test_translate_file_handles_error(self, sample_txt_file):
        """Test that translation errors are captured."""
        mock_api = MagicMock()
        mock_api.translate.side_effect = Exception("API Error")
        processor = FileProcessor(mock_api)

        result = processor.translate_file(sample_txt_file, "English")

        assert "Translation Error" in result

    def test_translate_empty_file(self):
        """Test translating empty file returns empty string."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write("")
            temp_path = f.name

        try:
            mock_api = MagicMock()
            processor = FileProcessor(mock_api)

            result = processor.translate_file(temp_path, "English")

            assert result == ""
            # API should not be called for empty file
            mock_api.translate.assert_not_called()
        finally:
            os.unlink(temp_path)


class TestEdgeCases:
    """Tests for edge cases."""

    def test_file_with_special_characters(self):
        """Test file with special characters."""
        content = "Special chars: @#$%^&*()_+{}|:<>?~`-=[]\\;',./\n日本語\nТекст"
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, encoding='utf-8') as f:
            f.write(content)
            temp_path = f.name

        try:
            mock_api = MagicMock()
            processor = FileProcessor(mock_api)

            text = processor.extract_text(temp_path)

            assert "@#$%^&*()" in text
            assert "日本語" in text
            assert "Текст" in text
        finally:
            os.unlink(temp_path)

    def test_very_long_single_line(self):
        """Test file with very long single line."""
        long_line = "A" * 10000  # 10K character line
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write(long_line)
            temp_path = f.name

        try:
            mock_api = MagicMock()
            processor = FileProcessor(mock_api)

            chunks = processor._chunk_text(long_line)

            # Should be split into multiple chunks
            assert len(chunks) > 1
        finally:
            os.unlink(temp_path)

    def test_windows_line_endings(self):
        """Test file with Windows line endings (CRLF)."""
        content = "Line 1\r\nLine 2\r\nLine 3"
        with tempfile.NamedTemporaryFile(mode='wb', suffix='.txt', delete=False) as f:
            f.write(content.encode('utf-8'))
            temp_path = f.name

        try:
            mock_api = MagicMock()
            processor = FileProcessor(mock_api)

            text = processor.extract_text(temp_path)

            # Should handle CRLF
            assert "Line 1" in text
            assert "Line 2" in text
        finally:
            os.unlink(temp_path)
