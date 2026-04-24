import re
import pytest
from src.version import VERSION


@pytest.mark.unit
def test_version_constant_value():
    # Arrange / Act / Assert
    assert VERSION == "1.7.0"


@pytest.mark.unit
def test_version_constant_matches_semver():
    # Arrange
    semver_pattern = r"^\d+\.\d+\.\d+$"

    # Act / Assert
    assert re.match(semver_pattern, VERSION), (
        f"VERSION '{VERSION}' does not match semver pattern MAJOR.MINOR.PATCH"
    )
