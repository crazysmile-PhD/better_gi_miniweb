from pathlib import Path


def test_python_version_range_is_documented():
    pyproject = Path('pyproject.toml').read_text(encoding='utf-8')

    assert 'requires-python = ">=3.12,<3.15"' in pyproject
