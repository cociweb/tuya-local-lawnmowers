"""Tests for the config flow."""

from unittest.mock import ANY, AsyncMock, MagicMock, patch

import pytest
import voluptuous as vol
from homeassistant.const import CONF_HOST, CONF_NAME
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.tuya_local_lawnmowers import (
    async_migrate_entry,
    config_flow,
)
from custom_components.tuya_local_lawnmowers.const import (
    CONF_DEVICE_CID,
    CONF_DEVICE_ID,
    CONF_LOCAL_KEY,
    CONF_POLL_ONLY,
    CONF_PROTOCOL_VERSION,
    CONF_TYPE,
    DOMAIN,
)

# Designed to contain "special" characters that users constantly suspect.
TESTKEY = ")<jO<@)'P1|kR$Kd"


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    yield


@pytest.fixture(autouse=True)
def prevent_task_creation():
    with patch(
        "custom_components.tuya_local_lawnmowers.device.TuyaLocalDevice.register_entity",
    ):
        yield


@pytest.fixture
def bypass_setup():
    """Prevent actual setup of the integration after config flow."""
    with patch(
        "custom_components.tuya_local_lawnmowers.async_setup_entry",
        return_value=True,
    ):
        yield


@pytest.fixture
def bypass_data_fetch():
    """Prevent actual data fetching from the device."""
    with patch(
        "tinytuya.Device.status",
        return_value={"1": True},
    ):
        yield


@pytest.mark.asyncio
async def test_init_entry(hass):
    """Test initialisation of the config flow."""
    # Setup mock device
    mock_device = AsyncMock()
    mock_device.has_returned_state = True
    mock_device.async_refresh = AsyncMock()
    # Default state for moebot_s_mower
    mock_device.get_property.return_value = "STANDBY"

    # Setup mock config
    mock_config = MagicMock()
    mock_config.all_entities.return_value = [
        MagicMock(entity="lawn_mower", config_id="lawn_mower"),
        MagicMock(entity="sensor", config_id="sensor_battery"),
    ]

    # Mock the device setup and get_config
    with (
        patch(
            "custom_components.tuya_local_lawnmowers.setup_device",
            return_value=mock_device,
        ),
        patch("homeassistant.config_entries.ConfigEntries.async_forward_entry_setups"),
        patch("homeassistant.config_entries.ConfigEntry.add_update_listener"),
        patch(
            "custom_components.tuya_local_lawnmowers.helpers.device_config.get_config",
            return_value=mock_config,
        ),
        patch(
            "custom_components.tuya_local_lawnmowers.async_unload_entry",
            return_value=True,
        ),
    ):
        # Create a test config entry
        entry = MockConfigEntry(
            domain=DOMAIN,
            version=11,
            title="test",
            data={
                CONF_DEVICE_ID: "deviceid",
                CONF_HOST: "hostname",
                CONF_LOCAL_KEY: "1234567890abcdef",
                CONF_POLL_ONLY: False,
                CONF_PROTOCOL_VERSION: 3.3,
                CONF_TYPE: "moebot_s_mower",
                CONF_DEVICE_CID: "test_cid",
            },
            options={},
        )
        entry.add_to_hass(hass)

        # Setup the entry
        await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()


@pytest.mark.asyncio
@patch("custom_components.tuya_local_lawnmowers.setup_device")
async def test_migrate_entry(mock_setup, hass):
    """Test migration from old entry format."""
    mock_device = MagicMock()
    mock_device.async_inferred_type = AsyncMock(return_value="moebot_s_mower")
    mock_setup.return_value = mock_device

    entry = MockConfigEntry(
        domain=DOMAIN,
        version=1,
        title="test",
        data={
            CONF_DEVICE_ID: "deviceid",
            CONF_HOST: "hostname",
            CONF_LOCAL_KEY: "1234567890abcdef",
            CONF_TYPE: "auto",
            "lawn_mower": True,
        },
    )
    entry.add_to_hass(hass)
    assert await async_migrate_entry(hass, entry)

    mock_device.async_inferred_type = AsyncMock(return_value=None)
    mock_device.reset_mock()

    entry = MockConfigEntry(
        domain=DOMAIN,
        version=1,
        title="test2",
        data={
            CONF_DEVICE_ID: "deviceid",
            CONF_HOST: "hostname",
            CONF_LOCAL_KEY: "1234567890abcdef",
            CONF_TYPE: "unknown",
            "lawn_mower": False,
        },
    )
    entry.add_to_hass(hass)
    assert not await async_migrate_entry(hass, entry)
    mock_device.reset_mock()

    entry = MockConfigEntry(
        domain=DOMAIN,
        version=2,
        title="test3",
        data={
            CONF_DEVICE_ID: "deviceid",
            CONF_HOST: "hostname",
            CONF_LOCAL_KEY: "1234567890abcdef",
            CONF_TYPE: "auto",
        },
        options={
            "lawn_mower": False,
        },
    )
    entry.add_to_hass(hass)
    assert not await async_migrate_entry(hass, entry)

    mock_device.async_inferred_type = AsyncMock(return_value="moebot_s_mower")
    mock_device.reset_mock()

    entry = MockConfigEntry(
        domain=DOMAIN,
        version=3,
        title="test4",
        data={
            CONF_DEVICE_ID: "deviceid",
            CONF_HOST: "hostname",
            CONF_LOCAL_KEY: "1234567890abcdef",
            CONF_TYPE: "moebot_s_mower",
        },
        options={
            "lawn_mower": True,
        },
    )
    entry.add_to_hass(hass)
    assert await async_migrate_entry(hass, entry)


@pytest.mark.asyncio
async def test_flow_user_init(hass):
    """Test the initialisation of the form in the first page of the
    manual config flow path.
    """
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": "local"}
    )
    expected = {
        "data_schema": ANY,
        "description_placeholders": None,
        "errors": {},
        "flow_id": ANY,
        "handler": DOMAIN,
        "step_id": "local",
        "type": "form",
        "last_step": ANY,
        "preview": ANY,
    }
    assert expected == result
    # Check the schema.  Simple comparison does not work since they are not
    # the same object
    try:
        result["data_schema"](
            {CONF_DEVICE_ID: "test", CONF_LOCAL_KEY: TESTKEY, CONF_HOST: "test"}
        )
    except vol.MultipleInvalid:
        assert False
    try:
        result["data_schema"]({CONF_DEVICE_ID: "missing_some"})
        assert False
    except vol.MultipleInvalid:
        pass


@pytest.mark.asyncio
@patch("custom_components.tuya_local_lawnmowers.config_flow.TuyaLocalDevice")
async def test_async_test_connection_valid(mock_device, hass):
    """Test that device is returned when connection is valid."""
    mock_instance = AsyncMock()
    mock_instance.has_returned_state = True
    mock_instance.pause = MagicMock()
    mock_instance.resume = MagicMock()
    mock_device.return_value = mock_instance
    hass.data[DOMAIN] = {"deviceid": {"device": mock_instance}}

    device = await config_flow.async_test_connection(
        {
            CONF_DEVICE_ID: "deviceid",
            CONF_LOCAL_KEY: TESTKEY,
            CONF_HOST: "hostname",
            CONF_PROTOCOL_VERSION: "auto",
        },
        hass,
    )
    assert device == mock_instance
    mock_instance.pause.assert_called_once()
    mock_instance.resume.assert_called_once()


@pytest.mark.asyncio
@patch("custom_components.tuya_local_lawnmowers.config_flow.TuyaLocalDevice")
async def test_async_test_connection_for_subdevice_valid(mock_device, hass):
    """Test that subdevice is returned when connection is valid."""
    mock_instance = AsyncMock()
    mock_instance.has_returned_state = True
    mock_instance.pause = MagicMock()
    mock_instance.resume = MagicMock()
    mock_device.return_value = mock_instance
    hass.data[DOMAIN] = {"subdeviceid": {"device": mock_instance}}

    device = await config_flow.async_test_connection(
        {
            CONF_DEVICE_ID: "deviceid",
            CONF_LOCAL_KEY: TESTKEY,
            CONF_HOST: "hostname",
            CONF_PROTOCOL_VERSION: "auto",
            CONF_DEVICE_CID: "subdeviceid",
        },
        hass,
    )
    assert device == mock_instance
    mock_instance.pause.assert_called_once()
    mock_instance.resume.assert_called_once()


@pytest.mark.asyncio
@patch("custom_components.tuya_local_lawnmowers.config_flow.TuyaLocalDevice")
async def test_async_test_connection_invalid(mock_device, hass):
    """Test that None is returned when connection is invalid."""
    mock_instance = AsyncMock()
    mock_instance.has_returned_state = False
    mock_device.return_value = mock_instance
    device = await config_flow.async_test_connection(
        {
            CONF_DEVICE_ID: "deviceid",
            CONF_LOCAL_KEY: TESTKEY,
            CONF_HOST: "hostname",
            CONF_PROTOCOL_VERSION: "auto",
        },
        hass,
    )
    assert device is None


@pytest.mark.asyncio
@patch("custom_components.tuya_local_lawnmowers.config_flow.async_test_connection")
async def test_flow_user_init_invalid_config(mock_test, hass):
    """Test errors populated when config is invalid."""
    mock_test.return_value = None
    flow = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": "local"}
    )
    result = await hass.config_entries.flow.async_configure(
        flow["flow_id"],
        user_input={
            CONF_DEVICE_ID: "deviceid",
            CONF_HOST: "hostname",
            CONF_LOCAL_KEY: "badkey",
            CONF_PROTOCOL_VERSION: "auto",
            CONF_POLL_ONLY: False,
        },
    )
    assert {"base": "connection"} == result["errors"]


def setup_device_mock(mock, failure=False, type="test"):
    mock_type = MagicMock()
    mock_type.legacy_type = type
    mock_type.config_type = type
    mock_type.match_quality.return_value = 100
    mock.async_possible_types = AsyncMock(
        return_value=[mock_type] if not failure else []
    )


@pytest.mark.asyncio
@patch("custom_components.tuya_local_lawnmowers.config_flow.async_test_connection")
async def test_flow_user_init_data_valid(mock_test, hass):
    """Test we advance to the next step when connection config is valid."""
    mock_device = MagicMock()
    setup_device_mock(mock_device)
    mock_test.return_value = mock_device

    flow = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": "local"}
    )
    result = await hass.config_entries.flow.async_configure(
        flow["flow_id"],
        user_input={
            CONF_DEVICE_ID: "deviceid",
            CONF_HOST: "hostname",
            CONF_LOCAL_KEY: TESTKEY,
        },
    )
    assert "form" == result["type"]
    assert "select_type" == result["step_id"]


@pytest.mark.asyncio
@patch.object(config_flow.ConfigFlowHandler, "device")
async def test_flow_select_type_init(mock_device, hass):
    """Test the initialisation of the form in the 2nd step of the config flow."""
    setup_device_mock(mock_device)

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": "select_type"}
    )
    expected = {
        "data_schema": ANY,
        "description_placeholders": None,
        "errors": None,
        "flow_id": ANY,
        "handler": DOMAIN,
        "step_id": "select_type",
        "type": "form",
        "last_step": ANY,
        "preview": ANY,
    }
    assert expected == result
    # Check the schema.  Simple comparison does not work since they are not
    # the same object
    try:
        result["data_schema"]({CONF_TYPE: "test"})
    except vol.MultipleInvalid:
        assert False
    try:
        result["data_schema"]({CONF_TYPE: "not_test"})
        assert False
    except vol.MultipleInvalid:
        pass


@pytest.mark.asyncio
@patch.object(config_flow.ConfigFlowHandler, "device")
async def test_flow_select_type_aborts_when_no_match(mock_device, hass):
    """Test the flow aborts when an unsupported device is used."""
    setup_device_mock(mock_device, failure=True)

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": "select_type"}
    )

    assert result["type"] == "abort"
    assert result["reason"] == "not_supported"


@pytest.mark.asyncio
@patch.object(config_flow.ConfigFlowHandler, "device")
async def test_flow_select_type_data_valid(mock_device, hass):
    """Test the flow continues when valid data is supplied for moebot_s_mower."""
    setup_device_mock(mock_device, type="moebot_s_mower")

    # Start the flow at the select_type step
    flow = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": "select_type", "unique_id": "test_mower_123"}
    )

    # Submit the form with moebot_s_mower selected
    result = await hass.config_entries.flow.async_configure(
        flow["flow_id"],
        user_input={CONF_TYPE: "moebot_s_mower"},
    )

    # Should move to choose_entities step
    assert result["type"] == "form"
    assert result["step_id"] == "choose_entities"

    # Verify the schema contains the name field
    schema = result["data_schema"].schema
    assert isinstance(schema, dict), "Schema should be a dictionary"
    assert CONF_NAME in schema, f"Expected {CONF_NAME} in schema"

    # The schema should only contain the name field at this point
    assert len(schema) == 1, f"Schema should only contain the name field, got {schema}"


@pytest.mark.asyncio
async def test_flow_choose_entities_init(hass):
    """Test the initialisation of the form in the 3rd step of the
    config flow for moebot_s_mower.
    """
    # Setup the flow with moebot_s_mower type
    with patch.dict(config_flow.ConfigFlowHandler.data, {CONF_TYPE: "moebot_s_mower"}):
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": "choose_entities", "unique_id": "mower_test_123"}
        )

    assert result["type"] == "form"
    assert result["step_id"] == "choose_entities"

    # Verify the schema contains the name field
    schema = result["data_schema"].schema
    assert isinstance(schema, dict), "Schema should be a dictionary"
    assert CONF_NAME in schema, f"Expected {CONF_NAME} in schema"

    # The schema should only contain the name field
    assert len(schema) == 1, f"Schema should only contain the name field, got: {schema}"

    # Test submitting the form with just the name
    user_input = {CONF_NAME: "mower_test_123"}

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input=user_input,
    )

    # Should create the config entry
    assert result["type"] == "create_entry"
    assert result["title"] == "mower_test_123"
    assert result["data"][CONF_TYPE] == "moebot_s_mower"

    # Verify no entity-specific data is in the config
    assert "lawn_mower" not in result["data"]
    assert "sensor_battery" not in result["data"]
    assert "binary_sensor_problem" not in result["data"]
    assert "sensor_problem_state" not in result["data"]


@pytest.mark.asyncio
@patch("custom_components.tuya_local_lawnmowers.config_flow.async_test_connection")
async def test_flow_choose_entities_creates_config_entry(mock_test, hass, bypass_setup):
    """Test the flow ends with config entry creation for moebot_s_mower."""

    # Create mock device with proper type support
    class FakeType:
        def __init__(self, config_type):
            self.config_type = config_type

        def match_quality(self, *_):
            return 100

    fake_type = FakeType("moebot_s_mower")
    mock_device = MagicMock()
    mock_device.async_possible_types = AsyncMock(return_value=[fake_type])
    mock_device._get_cached_state = MagicMock(return_value={})
    mock_device._product_ids = []
    mock_test.return_value = mock_device

    # Patch setup to prevent actual setup
    with patch(
        "custom_components.tuya_local_lawnmowers.async_setup_entry",
        return_value=True,
    ):
        # Step 1: user
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": "user"}
        )
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            user_input={"setup_mode": "manual"},
        )
        # Step 2: local
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            user_input={
                CONF_DEVICE_ID: "mower_test_123",
                CONF_HOST: "mower.local",
                CONF_LOCAL_KEY: "0123456789abcdef",
                CONF_PROTOCOL_VERSION: 3.3,
                CONF_POLL_ONLY: False,
            },
        )
        # Step 3: select_type
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            user_input={CONF_TYPE: "moebot_s_mower"},
        )
        # Step 4: choose_entities
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            user_input={CONF_NAME: "mower_test_123"},
        )
    # Verify the config entry was created with correct data
    assert result["type"] == "create_entry"
    assert result["title"] == "mower_test_123"
    # Verify all required data is in the result
    assert "data" in result
    data = result["data"]
    assert data[CONF_DEVICE_ID] == "mower_test_123"
    assert data[CONF_HOST] == "mower.local"
    assert data[CONF_LOCAL_KEY] == "0123456789abcdef"
    assert data[CONF_PROTOCOL_VERSION] == 3.3
    assert data[CONF_TYPE] == "moebot_s_mower"

    # Verify no entity-specific data is in the config
    assert "lawn_mower" not in data
    assert "sensor_battery" not in data
    assert "binary_sensor_problem" not in data
    assert "sensor_problem_state" not in data


@pytest.mark.asyncio
async def test_options_flow_init(hass, bypass_data_fetch):
    """Test config flow options initialization for moebot_s_mower."""
    config_entry = MockConfigEntry(
        domain=DOMAIN,
        version=11,
        unique_id="mower_test_123",
        data={
            CONF_DEVICE_ID: "mower_test_123",
            CONF_HOST: "mower.local",
            CONF_LOCAL_KEY: "1234567890abcdef",
            CONF_PROTOCOL_VERSION: 3.3,
            CONF_TYPE: "moebot_s_mower",
        },
    )
    config_entry.add_to_hass(hass)

    # Setup the config entry
    await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()

    # Initialize options flow
    result = await hass.config_entries.options.async_init(config_entry.entry_id)

    # Verify the form is shown with the correct step_id
    assert result["type"] == "form"
    assert result["step_id"] == "user"

    # Verify the schema contains expected fields
    schema = result["data_schema"].schema
    assert CONF_HOST in schema
    assert CONF_LOCAL_KEY in schema
    assert CONF_PROTOCOL_VERSION in schema
    assert CONF_POLL_ONLY in schema

    expected_fields = [CONF_LOCAL_KEY, CONF_HOST, CONF_PROTOCOL_VERSION, CONF_POLL_ONLY]
    for field in expected_fields:
        assert field in schema, f"Expected {field} in options schema"

    # Verify the protocol version options (compare as sets to avoid order/type issues)
    version_selector = schema[CONF_PROTOCOL_VERSION]
    expected_versions = {"auto", 3.1, 3.2, 3.3, 3.4, 3.5, 3.22}
    assert set(version_selector.container) == expected_versions
    # Check default value for CONF_POLL_ONLY by instantiating the schema
    form_defaults = result["data_schema"]({})
    assert form_defaults[CONF_POLL_ONLY] is False


@pytest.mark.asyncio
@patch("custom_components.tuya_local_lawnmowers.config_flow.async_test_connection")
async def test_options_flow_modifies_config(mock_test, hass, bypass_setup):
    """Test that options flow can modify config for moebot_s_mower."""
    mock_device = MagicMock()
    mock_test.return_value = mock_device

    # Create a config entry for moebot_s_mower
    config_entry = MockConfigEntry(
        domain=DOMAIN,
        version=11,
        unique_id="mower_test_123",
        data={
            CONF_DEVICE_ID: "mower_test_123",
            CONF_HOST: "mower.local",
            CONF_LOCAL_KEY: "1234567890abcdef",
            CONF_PROTOCOL_VERSION: 3.3,
            CONF_TYPE: "moebot_s_mower",
        },
    )
    config_entry.add_to_hass(hass)

    # Setup the config entry
    await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()

    # Initialize options flow
    result = await hass.config_entries.options.async_init(config_entry.entry_id)

    # Submit updated config
    new_host = "new-mower.local"
    new_local_key = "new_test_key"
    new_protocol = 3.4  # Use float for protocol version
    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        user_input={
            CONF_HOST: new_host,
            CONF_LOCAL_KEY: new_local_key,
            CONF_PROTOCOL_VERSION: new_protocol,
            CONF_POLL_ONLY: True,
        },
    )

    # Verify the options were updated
    assert result["type"] == "create_entry"
    assert result["data"] == {
        CONF_HOST: new_host,
        CONF_LOCAL_KEY: new_local_key,
        CONF_PROTOCOL_VERSION: new_protocol,
        CONF_POLL_ONLY: True,
    }

    # Only .options should be updated, not .data
    assert config_entry.options[CONF_HOST] == new_host
    assert config_entry.options[CONF_LOCAL_KEY] == new_local_key
    assert config_entry.options[CONF_PROTOCOL_VERSION] == new_protocol
    assert config_entry.options[CONF_POLL_ONLY] is True
    # .data remains unchanged
    assert config_entry.data[CONF_DEVICE_ID] == "mower_test_123"
    assert config_entry.data[CONF_TYPE] == "moebot_s_mower"


@pytest.mark.asyncio
@patch("custom_components.tuya_local_lawnmowers.config_flow.async_test_connection")
async def test_options_flow_fails_when_connection_fails(
    mock_test, hass, bypass_data_fetch
):
    # Setup a mock device that will be returned by async_test_connection
    mock_device = MagicMock()
    mock_device.has_returned_state = False
    mock_test.return_value = None  # Simulate connection failure

    # Create a config entry with initial data
    config_entry = MockConfigEntry(
        domain=DOMAIN,
        version=13,
        unique_id="uniqueid",
        data={
            CONF_DEVICE_ID: "deviceid",
            CONF_HOST: "hostname",
            CONF_LOCAL_KEY: "1234567890abcdef",
            CONF_NAME: "test",
            CONF_POLL_ONLY: False,
            CONF_PROTOCOL_VERSION: 3.3,
            CONF_TYPE: "moebot_s_mower",
            CONF_DEVICE_CID: "",
        },
    )
    config_entry.add_to_hass(hass)

    # Mock the setup to succeed
    with patch(
        "custom_components.tuya_local_lawnmowers.async_setup_entry",
        return_value=True,
    ):
        assert await hass.config_entries.async_setup(config_entry.entry_id)
        await hass.async_block_till_done()

    # Show initial form
    result = await hass.config_entries.options.async_init(config_entry.entry_id)
    assert result["type"] == "form"

    # Submit updated config with connection failure
    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        user_input={
            CONF_HOST: "new_hostname",
            CONF_LOCAL_KEY: "new_key",
            CONF_PROTOCOL_VERSION: 3.3,  # Using a float value for protocol version
            CONF_POLL_ONLY: False,
        },
    )

    # Verify we stay on the form with connection error
    assert result["type"] == "form"
    assert result["step_id"] == "user"
    assert result["errors"] == {"base": "connection"}


@pytest.mark.asyncio
@patch("custom_components.tuya_local_lawnmowers.config_flow.async_test_connection")
async def test_options_flow_fails_when_config_is_missing(mock_test, hass):
    mock_device = MagicMock()
    mock_test.return_value = mock_device

    config_entry = MockConfigEntry(
        domain=DOMAIN,
        version=13,
        unique_id="uniqueid",
        data={
            CONF_DEVICE_ID: "deviceid",
            CONF_HOST: "hostname",
            CONF_LOCAL_KEY: "1234567890abcdef",
            CONF_NAME: "test",
            CONF_POLL_ONLY: False,
            CONF_PROTOCOL_VERSION: "auto",
            CONF_TYPE: "non_existing",
        },
    )
    config_entry.add_to_hass(hass)

    await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()
    # show initial form
    result = await hass.config_entries.options.async_init(config_entry.entry_id)
    assert result["type"] == "abort"
    assert result["reason"] == "not_supported"
