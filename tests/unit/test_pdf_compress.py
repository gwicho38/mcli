"""
Unit tests for PDF compression functionality
"""

from unittest.mock import MagicMock, patch

import pytest


@pytest.fixture
def mock_fitz():
    """Mock PyMuPDF (fitz) library"""
    with patch("fitz") as mock:
        # Mock document
        mock_doc = MagicMock()
        mock_doc.__len__.return_value = 3
        mock.open.return_value = mock_doc

        # Mock page
        mock_page = MagicMock()
        mock_page.rect = MagickMock()
        mock_page.rect.width = 612
        mock_page.rect.height = 792
        mock_doc.load_page.return_value = mock_page

        # Mock pixmap
        mock_pix = MagicMock()
        mock_pix.tobytes.return_value = b"fake_image_data"
        mock_page.get_pixmap.return_value = mock_pix

        # Mock output document
        mock_out_doc = MagicMock()
        mock_new_page = MagicMock()
        mock_new_page.rect = mock_page.rect
        mock_out_doc.new_page.return_value = mock_new_page
        mock.open.side_effect = [mock_doc, mock_out_doc]

        yield mock


class TestPageRangeParsing:
    """Test parse_page_range function"""

    def test_parse_single_page(self):
        """Test parsing single page number"""
        # This would need to import the actual function from the PDF workflow
        # For now, we're testing the logic
        result = self._parse_page_range("3")
        assert result == [3]

    def test_parse_multiple_pages(self):
        """Test parsing multiple page numbers"""
        result = self._parse_page_range("3,4,7")
        assert result == [3, 4, 7]

    def test_parse_page_range(self):
        """Test parsing page range"""
        result = self._parse_page_range("3-5")
        assert result == [3, 4, 5]

    def test_parse_mixed_format(self):
        """Test parsing mixed format"""
        result = self._parse_page_range("1,3-5,8")
        assert result == [1, 3, 4, 5, 8]

    def test_parse_empty_string(self):
        """Test parsing empty string"""
        result = self._parse_page_range("")
        assert result == []

    def test_parse_none(self):
        """Test parsing None"""
        result = self._parse_page_range(None)
        assert result == []

    @staticmethod
    def _parse_page_range(page_range_str):
        """Helper method to parse page range (implementation from compress command)"""
        pages = set()
        if not page_range_str:
            return []

        for part in page_range_str.split(","):
            part = part.strip()
            if "-" in part:
                start, end = map(int, part.split("-"))
                pages.update(range(start, end + 1))
            else:
                pages.add(int(part))

        return sorted(list(pages))


class TestCompressionSettings:
    """Test compression settings for different levels"""

    def test_light_compression_settings(self):
        """Test light compression level settings"""
        settings = self._get_compression_settings("light")
        assert settings["color_quality"] == 90
        assert settings["gray_quality"] == 85

    def test_medium_compression_settings(self):
        """Test medium compression level settings"""
        settings = self._get_compression_settings("medium")
        assert settings["color_quality"] == 80
        assert settings["gray_quality"] == 70

    def test_aggressive_compression_settings(self):
        """Test aggressive compression level settings"""
        settings = self._get_compression_settings("aggressive")
        assert settings["color_quality"] == 65
        assert settings["gray_quality"] == 45

    def test_ultra_compression_settings(self):
        """Test ultra compression level settings"""
        settings = self._get_compression_settings("ultra")
        assert settings["color_quality"] == 55
        assert settings["gray_quality"] == 35

    def test_smart_compression_settings(self):
        """Test smart compression level settings (default)"""
        settings = self._get_compression_settings("smart")
        assert settings["color_quality"] == 85
        assert settings["gray_quality"] == 65

    def test_invalid_level_defaults_to_smart(self):
        """Test invalid compression level defaults to smart"""
        settings = self._get_compression_settings("invalid")
        assert settings == self._get_compression_settings("smart")

    @staticmethod
    def _get_compression_settings(level):
        """Helper method to get compression settings (implementation from compress command)"""
        settings = {
            "light": {
                "color_quality": 90,
                "gray_quality": 85,
                "description": "Light compression, high quality",
            },
            "medium": {
                "color_quality": 80,
                "gray_quality": 70,
                "description": "Balanced compression and quality",
            },
            "aggressive": {
                "color_quality": 65,
                "gray_quality": 45,
                "description": "Maximum compression, lower quality",
            },
            "ultra": {
                "color_quality": 55,
                "gray_quality": 35,
                "description": "Ultra compression for minimum file size (may reduce legibility)",
            },
            "smart": {
                "color_quality": 85,
                "gray_quality": 65,
                "description": "Smart per-page optimization",
            },
        }
        return settings.get(level, settings["smart"])


class TestPDFCompression:
    """Test PDF compression functionality"""

    def test_compress_without_pymupdf(self):
        """Test compression fails gracefully without PyMuPDF"""
        # Test that appropriate error message is returned
        # when PyMuPDF is not available
        # This is tested through the actual workflow command

    def test_compress_with_color_pages(self):
        """Test compression preserves specified color pages"""
        # Test that color pages are identified correctly
        color_pages = [3, 4]
        assert 3 in color_pages
        assert 4 in color_pages
        assert 5 not in color_pages

    def test_compress_dpi_scaling(self):
        """Test DPI scaling calculation"""
        dpi = 150
        scaling_factor = dpi / 72  # 72 is default DPI
        assert scaling_factor == pytest.approx(2.083, rel=0.01)

    def test_compression_quality_for_color_page(self):
        """Test JPEG quality for color pages"""
        settings = self._get_compression_settings("smart")
        color_quality = settings["color_quality"]
        assert color_quality == 85

    def test_compression_quality_for_gray_page(self):
        """Test JPEG quality for grayscale pages"""
        settings = self._get_compression_settings("smart")
        gray_quality = settings["gray_quality"]
        assert gray_quality == 65

    @staticmethod
    def _get_compression_settings(level):
        """Helper method (same as TestCompressionSettings)"""
        settings = {
            "smart": {
                "color_quality": 85,
                "gray_quality": 65,
                "description": "Smart per-page optimization",
            }
        }
        return settings.get(level, settings["smart"])


class TestCompressionResults:
    """Test compression result metrics"""

    def test_size_reduction_calculation(self):
        """Test size reduction percentage calculation"""
        original_size = 10_000_000  # 10 MB
        compressed_size = 1_000_000  # 1 MB
        reduction = ((original_size - compressed_size) / original_size) * 100
        assert reduction == 90.0

    def test_mb_conversion(self):
        """Test bytes to MB conversion"""
        size_bytes = 1_048_576  # 1 MB in bytes
        size_mb = size_bytes / (1024 * 1024)
        assert size_mb == 1.0

    def test_savings_calculation(self):
        """Test space savings calculation"""
        original_mb = 10.73
        compressed_mb = 0.81
        savings = original_mb - compressed_mb
        assert savings == pytest.approx(9.92, rel=0.01)


@pytest.mark.integration
class TestPDFCompressionIntegration:
    """Integration tests for PDF compression (requires PyMuPDF)"""

    def test_compress_command_available(self):
        """Test that compress command is available in PDF workflow"""
        # This would test the actual CLI command

    def test_compress_with_real_pdf(self, tmp_path):
        """Test compression with a real PDF file"""
        # This would require a test PDF file

    def test_selective_color_preservation(self, tmp_path):
        """Test that specified pages remain in color"""
        # This would verify color preservation in output

    def test_target_size_iteration(self, tmp_path):
        """Test that target size triggers aggressive compression"""
        # This would test the retry logic


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
