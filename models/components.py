from typing import Dict, List, Optional
from dataclasses import dataclass, field

class NetworkComponent:
    """Base class for network components"""
    def __init__(self, id: str, label: str):
        self.id: str = id
        self.label: str = label
        self.connections_to: List[str] = []
        self.connections_from: List[str] = []
        self.level: int = -1  # Hierarchy level
        self.attributes: Dict = {}

    @property
    def component_type(self) -> str:
        """Determine component type from ID prefix"""
        if self.id.startswith('MC'):
            return 'canal'
        elif self.id.startswith('DP'):
            return 'distribution_point'
        elif self.id.startswith('SW'):
            return 'smart_water'
        elif self.id.startswith('ZT'):
            return 'gate'
        elif self.id.startswith('F'):
            return 'field'
        return 'unknown'

    def add_connection_to(self, target_id: str):
        """Add outgoing connection"""
        if target_id not in self.connections_to:
            self.connections_to.append(target_id)

    def add_connection_from(self, source_id: str):
        """Add incoming connection"""
        if source_id not in self.connections_from:
            self.connections_from.append(source_id)

    def set_level(self, level: int):
        """Set hierarchy level"""
        self.level = level

    def __repr__(self):
        return f"{self.id} ({self.component_type}): Level {self.level}"