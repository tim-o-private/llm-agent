import os
import tempfile

import pytest
import yaml

from utils.config_loader import ConfigLoader


@pytest.fixture
def temp_settings_file():
    data = {
        'llm': {'model': 'gemini-pro', 'temperature': 0.7},
        'app': {'name': 'TestApp'}
    }
    with tempfile.NamedTemporaryFile('w+', delete=False) as f:
        yaml.dump(data, f)
        f.flush()
        yield f.name
    os.remove(f.name)

@pytest.fixture
def temp_env_file():
    with tempfile.NamedTemporaryFile('w+', delete=False) as f:
        f.write('LLM_MODEL=env-model\n')
        f.write('APP_NAME=EnvApp\n')
        f.flush()
        yield f.name
    os.remove(f.name)

def test_loads_yaml_and_env(temp_settings_file, temp_env_file, monkeypatch):
    loader = ConfigLoader(settings_rel_path=temp_settings_file, dotenv_rel_path=temp_env_file)
    # Should get env var first
    assert loader.get('llm.model') == 'env-model'
    assert loader.get('app.name') == 'EnvApp'
    # Should get YAML if env var not set
    assert loader.get('llm.temperature') == 0.7
    # Should return default if not found
    assert loader.get('llm.unknown', default='x') == 'x'

def test_missing_yaml(monkeypatch, temp_env_file):
    loader = ConfigLoader(settings_rel_path='nonexistent.yaml', dotenv_rel_path=temp_env_file)
    # Should not error, just use env or default
    assert loader.get('llm.model', default='foo') == 'foo' or loader.get('llm.model') == 'env-model'

def test_missing_env_and_yaml(monkeypatch):
    monkeypatch.delenv('LLM_MODEL', raising=False)
    monkeypatch.delenv('APP_NAME', raising=False)
    loader = ConfigLoader(settings_rel_path='nonexistent.yaml', dotenv_rel_path='nonexistent.env')
    assert loader.get('llm.model', default='bar') == 'bar'
