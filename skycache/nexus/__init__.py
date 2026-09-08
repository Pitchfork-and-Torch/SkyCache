"""SkyCache Nexus - multi-node community knowledge & connectivity fabric.

Honest model: local mesh broadband *experience* + store-and-forward knowledge.
Never satellite uplink by default. Never commercial decryption.
Mesh RF only on unlicensed/ISM (Wi-Fi / regional LoRa) with operator compliance.
"""

from skycache.nexus.control_plane import ControlPlane
from skycache.nexus.fabric import ContentFabric
from skycache.nexus.gateway import GatewayManager
from skycache.nexus.mesh import MeshFabric
from skycache.nexus.sim import NexusSimulator

__all__ = [
    "ContentFabric",
    "ControlPlane",
    "GatewayManager",
    "MeshFabric",
    "NexusSimulator",
]
