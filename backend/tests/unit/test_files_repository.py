import pytest
from src.repositories.files import FilesRepository


class ConcreteFiles(FilesRepository):
    pass


def make_repo(input_dir):
    repo = ConcreteFiles.__new__(ConcreteFiles)
    repo.input_dir = str(input_dir)
    repo.output_dir = str(input_dir)
    return repo


@pytest.mark.unit
def test_list_input_files_returns_files(tmp_path):
    # Arrange
    (tmp_path / "receipt.jpg").touch()
    (tmp_path / "other.pdf").touch()
    repo = make_repo(tmp_path)

    # Act
    result = repo.list_input_files()

    # Assert
    assert set(result) == {"receipt.jpg", "other.pdf"}


@pytest.mark.unit
def test_list_input_files_empty_dir(tmp_path):
    # Arrange
    repo = make_repo(tmp_path)

    # Act
    result = repo.list_input_files()

    # Assert
    assert result == []


@pytest.mark.unit
def test_list_input_files_excludes_directories(tmp_path):
    # Arrange
    (tmp_path / "receipt.jpg").touch()
    (tmp_path / "subdir").mkdir()
    repo = make_repo(tmp_path)

    # Act
    result = repo.list_input_files()

    # Assert
    assert result == ["receipt.jpg"]
