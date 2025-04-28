import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../src')))

import pytest
import tempfile
import yaml
from core.file_parser import read_markdown, read_yaml

# --- Test Data ---

MARKDOWN_CONTENT = "# Title\n\nThis is *markdown*."
YAML_CONTENT = "key: value\nlist:\n  - item1\n  - item2\ndict:\n  nested_key: nested_value"
YAML_DATA = {
    'key': 'value', 
    'list': ['item1', 'item2'], 
    'dict': {'nested_key': 'nested_value'}
}
INVALID_YAML_CONTENT = "key: value\nlist: [item1, item2"

# --- Fixtures ---

@pytest.fixture
def temp_md_file():
    with tempfile.NamedTemporaryFile('w', delete=False, suffix='.md', encoding='utf-8') as f:
        f.write(MARKDOWN_CONTENT)
        filepath = f.name
    yield filepath
    os.remove(filepath)

@pytest.fixture
def temp_yaml_file():
    with tempfile.NamedTemporaryFile('w', delete=False, suffix='.yaml', encoding='utf-8') as f:
        f.write(YAML_CONTENT)
        filepath = f.name
    yield filepath
    os.remove(filepath)

@pytest.fixture
def temp_invalid_yaml_file():
    with tempfile.NamedTemporaryFile('w', delete=False, suffix='.yaml', encoding='utf-8') as f:
        f.write(INVALID_YAML_CONTENT)
        filepath = f.name
    yield filepath
    os.remove(filepath)

@pytest.fixture
def temp_empty_yaml_file():
    with tempfile.NamedTemporaryFile('w', delete=False, suffix='.yaml', encoding='utf-8') as f:
        filepath = f.name
    yield filepath
    os.remove(filepath)

# --- Tests for read_markdown ---

def test_read_markdown_success(temp_md_file):
    content = read_markdown(temp_md_file)
    assert content == MARKDOWN_CONTENT

def test_read_markdown_not_found():
    with pytest.raises(FileNotFoundError):
        read_markdown("non_existent_file.md")

# --- Tests for read_yaml ---

def test_read_yaml_success(temp_yaml_file):
    data = read_yaml(temp_yaml_file)
    assert data == YAML_DATA

def test_read_yaml_not_found():
    with pytest.raises(FileNotFoundError):
        read_yaml("non_existent_file.yaml")

def test_read_yaml_invalid(temp_invalid_yaml_file):
    with pytest.raises(yaml.YAMLError):
        read_yaml(temp_invalid_yaml_file)

def test_read_yaml_empty(temp_empty_yaml_file):
    """Test that reading an empty YAML file returns an empty dict."""
    data = read_yaml(temp_empty_yaml_file)
    assert data == {} 