"""Configure pytest for Home Assistant core tests."""
import asyncio
import functools
import os
from unittest.mock import patch, MagicMock

import pytest
import pytest_asyncio
from homeassistant.core import HomeAssistant
from homeassistant.setup import async_setup_component

# This needs to be set before the first import of homeassistant.config
os.environ["HASS_CONFIG"] = "/tmp"
os.environ["HASS_NO_SYSTEM_CONFIG"] = "1"

# Prevent tests from setting up the recorder
pytest_plugins = [
    "pytest_homeassistant_custom_component",
]

# Disable tests that require a real Home Assistant instance
collect_ignore_glob = []

# Set up the event loop for all tests
@pytest.fixture(autouse=True)
def event_loop():
    """Create an instance of the default event loop for each test case."""
    policy = asyncio.get_event_loop_policy()
    loop = policy.new_event_loop()
    yield loop
    loop.close()

# Mock the Home Assistant core
@pytest.fixture(autouse=True)
async def mock_hass():
    """Mock the Home Assistant core."""
    async def async_add_executor_job(f, *args, **kwargs):
        return await asyncio.get_event_loop().run_in_executor(
            None, lambda: f(*args, **kwargs)
        )
    
    with patch("homeassistant.core.HomeAssistant") as mock_hass:
        mock_hass.return_value.async_add_executor_job = async_add_executor_job
        yield mock_hass

# Mock the Tuya Sharing Manager
@pytest.fixture(autouse=True)
def mock_tuya_sharing():
    """Mock the Tuya Sharing Manager."""
    with patch("tuya_sharing.Manager") as mock_manager:
        mock_manager.return_value = MagicMock()
        yield mock_manager.return_value

# Mock the Tuya Local Device
@pytest.fixture(autouse=True)
def mock_tuya_device():
    """Mock the Tuya Local Device."""
    with patch(
        "custom_components.tuya_local_lawnmowers.device.TuyaLocalDevice"
    ) as mock_device:
        yield mock_device

# Mock the device config flow
@pytest.fixture(autouse=True)
def mock_config_flow():
    """Mock the config flow."""
    with patch("custom_components.tuya_local_lawnmowers.config_flow.ConfigFlowHandler") as mock_cf:
        yield mock_cf
