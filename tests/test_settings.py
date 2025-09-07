from msprites2.settings import Settings


class TestSettings:
    """Test the Settings configuration class."""

    def test_default_values(self):
        """Test that default values are set correctly."""
        assert Settings.IPS == 5
        assert Settings.WIDTH == 512
        assert Settings.HEIGHT == 288
        assert Settings.EXT == ".jpg"
        assert Settings.ROWS == 30
        assert Settings.COLS == 30
        assert Settings.FILENAME_FORMAT == "%04d{ext}"

    def test_load_with_all_parameters(self):
        """Test loading settings with all parameters."""
        original_values = {
            "ips": Settings.IPS,
            "width": Settings.WIDTH,
            "height": Settings.HEIGHT,
            "ext": Settings.EXT,
            "rows": Settings.ROWS,
            "cols": Settings.COLS,
        }

        Settings.load(width=640, height=360, ips=2, ext=".png", rows=20, cols=20)

        assert Settings.IPS == 2
        assert Settings.WIDTH == 640
        assert Settings.HEIGHT == 360
        assert Settings.EXT == ".png"
        assert Settings.ROWS == 20
        assert Settings.COLS == 20

        # Restore original values
        Settings.load(**original_values)

    def test_load_with_partial_parameters(self):
        """Test loading settings with only some parameters."""
        original_values = {
            "ips": Settings.IPS,
            "width": Settings.WIDTH,
            "height": Settings.HEIGHT,
            "ext": Settings.EXT,
            "rows": Settings.ROWS,
            "cols": Settings.COLS,
        }

        Settings.load(width=1024, ips=3)

        assert Settings.IPS == 3
        assert Settings.WIDTH == 1024
        # Other values should remain as they were before this test
        # (which might not be the defaults due to previous test)

        # Restore original values
        Settings.load(**original_values)

    def test_load_with_none_values(self):
        """Test that None values don't override existing values."""
        original_values = {
            "ips": Settings.IPS,
            "width": Settings.WIDTH,
            "height": Settings.HEIGHT,
            "ext": Settings.EXT,
            "rows": Settings.ROWS,
            "cols": Settings.COLS,
        }

        Settings.load(width=None, height=None, ips=None, ext=None, rows=None, cols=None)

        # Values should remain unchanged
        assert Settings.IPS == original_values["ips"]
        assert Settings.WIDTH == original_values["width"]
        assert Settings.HEIGHT == original_values["height"]
        assert Settings.EXT == original_values["ext"]
        assert Settings.ROWS == original_values["rows"]
        assert Settings.COLS == original_values["cols"]

    def test_spritefilename_default_ext(self):
        """Test sprite filename generation with default extension."""
        original_ext = Settings.EXT
        Settings.EXT = ".jpg"

        filename = Settings.spritefilename(1)
        assert filename == "0001.jpg"

        filename = Settings.spritefilename(99)
        assert filename == "0099.jpg"

        filename = Settings.spritefilename(1234)
        assert filename == "1234.jpg"

        Settings.EXT = original_ext

    def test_spritefilename_custom_ext(self):
        """Test sprite filename generation with custom extension."""
        original_ext = Settings.EXT
        Settings.EXT = ".png"

        filename = Settings.spritefilename(5)
        assert filename == "0005.png"

        Settings.EXT = original_ext

    def test_spritefilename_format_consistency(self):
        """Test that filename format is consistently applied."""
        original_ext = Settings.EXT
        Settings.EXT = ".webp"

        # Test various numbers to ensure padding works
        test_cases = [
            (0, "0000.webp"),
            (1, "0001.webp"),
            (10, "0010.webp"),
            (100, "0100.webp"),
            (9999, "9999.webp"),
        ]

        for number, expected in test_cases:
            assert Settings.spritefilename(number) == expected

        Settings.EXT = original_ext
