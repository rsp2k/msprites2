"""Test that all imports work correctly."""


def test_import_main_class():
    """Test that MontageSprites can be imported from the package."""
    from msprites2 import MontageSprites

    assert MontageSprites is not None


def test_import_settings():
    """Test that Settings can be imported."""
    from msprites2.settings import Settings

    assert Settings is not None


def test_import_montage_sprites_module():
    """Test that the montage_sprites module can be imported."""
    from msprites2 import montage_sprites

    assert montage_sprites is not None


def test_package_all():
    """Test that __all__ exports work correctly."""
    import msprites2

    # Should be able to access MontageSprites
    assert hasattr(msprites2, "MontageSprites")

    # Verify it's the correct class
    assert msprites2.MontageSprites.__name__ == "MontageSprites"
