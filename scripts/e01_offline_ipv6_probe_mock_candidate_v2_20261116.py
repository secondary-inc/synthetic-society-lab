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
class _MockScopeFailure:
    poisoned: bool = False


@dataclass(slots=True)
class MockVendorState:
    initialized: bool = False
    cached_ipv6: object = None
    scope_active: bool = False
    failed: bool = False
    _active_failure: object = None


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
    Postcallback drift checks see only exit state: transient drift restored before
    that check is not observed. Detected reentry is separately sticky. Neither
    mechanism provides continuous or hostile-callback tamper protection.
    """
    if type(socket_state) is not MockSocketState or type(vendor_state) is not MockVendorState:
        raise MockConfigurationRefused('MOCK_STATE_TYPE')
    # Recognize the outer owner before testing its temporary False flag.
    # The local token stays poisoned even if a callback clears public failed.
    active_failure = vendor_state._active_failure
    if vendor_state.scope_active is not False or active_failure is not None:
        vendor_state.failed = True
        if type(active_failure) is _MockScopeFailure:
            active_failure.poisoned = True
        raise MockConfigurationRefused('MOCK_REENTRY')
    if type(socket_state.has_ipv6) is not bool or socket_state.has_ipv6 is not True:
        raise MockConfigurationRefused('MOCK_ORIGINAL_NOT_TRUE')
    if (vendor_state.initialized is not False or vendor_state.cached_ipv6 is not None
            or vendor_state.scope_active is not False or vendor_state.failed is not False):
        raise MockConfigurationRefused('MOCK_VENDOR_NOT_FRESH')
    if not callable(initialize): raise MockConfigurationRefused('MOCK_INITIALIZER_TYPE')
    original = socket_state.has_ipv6
    active_failure = _MockScopeFailure()
    vendor_state._active_failure = active_failure
    vendor_state.scope_active = True
    socket_state.has_ipv6 = False
    primary_error = None
    try:
        initialize(socket_state, vendor_state)
        if active_failure.poisoned is not False or vendor_state.failed is not False:
            raise MockConfigurationRefused('MOCK_STICKY_FAILURE')
        if vendor_state._active_failure is not active_failure:
            raise MockConfigurationRefused('MOCK_SCOPE_DRIFT')
        if socket_state.has_ipv6 is not False or vendor_state.scope_active is not True:
            raise MockConfigurationRefused('MOCK_SCOPE_DRIFT')
        if (vendor_state.initialized is not True or vendor_state.cached_ipv6 is not False
                or vendor_state.failed is not False):
            raise MockConfigurationRefused('MOCK_INITIALIZATION_RESULT')
    except BaseException as exc:
        primary_error = exc
        active_failure.poisoned = True
        vendor_state.failed = True
        raise
    finally:
        # Mock fields only; never actual socket or pip globals.
        socket_state.has_ipv6 = original
        vendor_state.scope_active = False
        vendor_state._active_failure = None
        if socket_state.has_ipv6 is not original and primary_error is None:
            vendor_state.failed = True
            raise MockConfigurationRefused('MOCK_RESTORE_FAILED')
    return {'mode': 'PURE_MOCK_SCOPED_IPV6_INITIALIZATION_V2',
            'original_has_ipv6': original, 'temporary_has_ipv6': False,
            'restored_has_ipv6': socket_state.has_ipv6,
            'vendor_cached_ipv6': vendor_state.cached_ipv6,
            'network_permissions_changed': False}
