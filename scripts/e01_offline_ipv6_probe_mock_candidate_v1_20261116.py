"""PURE MOCK ONLY: assess a scoped public capability override.

This simulator deliberately accepts exact mock dataclasses only. It never imports
socket or pip and is not an adapter capable of changing the real socket module.
"""
from dataclasses import dataclass


class MockConfigurationRefused(RuntimeError):
    pass


@dataclass(slots=True)
class MockSocketState:
    has_ipv6: bool = True


@dataclass(slots=True)
class MockVendorState:
    initialized: bool = False
    cached_ipv6: object = None
    scope_active: bool = False
    failed: bool = False


def initialize_probe_model(socket_state, vendor_state, audit):
    """Model the bound broad-catch shape; audit is a direct mock guard callback."""
    if type(socket_state) is not MockSocketState or type(vendor_state) is not MockVendorState:
        raise MockConfigurationRefused('MOCK_STATE_TYPE')
    value = False
    if socket_state.has_ipv6:
        try:
            audit('socket.__new__', ())
            audit('socket.bind', ())
            value = True
        except Exception:
            pass
    vendor_state.cached_ipv6 = value
    vendor_state.initialized = True
    return value


def scoped_mock_initialization(socket_state, vendor_state, initialize):
    """Temporarily suppress only the modeled initialization, then restore.

    A future real implementation would need separate methods/production review,
    exact bound module/origin/state checks and the original network guards.
    """
    if type(socket_state) is not MockSocketState or type(vendor_state) is not MockVendorState:
        raise MockConfigurationRefused('MOCK_STATE_TYPE')
    if type(socket_state.has_ipv6) is not bool or socket_state.has_ipv6 is not True:
        raise MockConfigurationRefused('MOCK_ORIGINAL_NOT_TRUE')
    if (vendor_state.initialized is not False or vendor_state.cached_ipv6 is not None
            or vendor_state.scope_active is not False or vendor_state.failed is not False):
        raise MockConfigurationRefused('MOCK_VENDOR_NOT_FRESH')
    if not callable(initialize): raise MockConfigurationRefused('MOCK_INITIALIZER_TYPE')
    original = socket_state.has_ipv6
    vendor_state.scope_active = True
    socket_state.has_ipv6 = False
    primary_error = None
    try:
        initialize(socket_state, vendor_state)
        if socket_state.has_ipv6 is not False or vendor_state.scope_active is not True:
            raise MockConfigurationRefused('MOCK_SCOPE_DRIFT')
        if (vendor_state.initialized is not True or vendor_state.cached_ipv6 is not False
                or vendor_state.failed is not False):
            raise MockConfigurationRefused('MOCK_INITIALIZATION_RESULT')
    except BaseException as exc:
        primary_error = exc
        vendor_state.failed = True
        raise
    finally:
        # Mock fields only; never actual socket or pip globals.
        socket_state.has_ipv6 = original
        vendor_state.scope_active = False
        if socket_state.has_ipv6 is not original and primary_error is None:
            vendor_state.failed = True
            raise MockConfigurationRefused('MOCK_RESTORE_FAILED')
    return {'mode': 'PURE_MOCK_SCOPED_IPV6_INITIALIZATION',
            'original_has_ipv6': original, 'temporary_has_ipv6': False,
            'restored_has_ipv6': socket_state.has_ipv6,
            'vendor_cached_ipv6': vendor_state.cached_ipv6,
            'network_permissions_changed': False}
