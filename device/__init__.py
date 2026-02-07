"""
Device management module for RHCSA Simulator v2.0.0

Provides automatic cleanup of practice resources between tasks.
"""

from device.device_manager import DeviceManager, get_device_manager, ResourceType
from device.cleanup_strategies import (
    CleanupStrategy,
    LVMCleanupStrategy,
    MountCleanupStrategy,
    SwapCleanupStrategy,
    UserCleanupStrategy,
    FstabCleanupStrategy,
)
from device.network_manager import NetworkStateManager, get_network_manager

__all__ = [
    'DeviceManager',
    'get_device_manager',
    'ResourceType',
    'CleanupStrategy',
    'LVMCleanupStrategy',
    'MountCleanupStrategy',
    'SwapCleanupStrategy',
    'UserCleanupStrategy',
    'FstabCleanupStrategy',
    'NetworkStateManager',
    'get_network_manager',
]
