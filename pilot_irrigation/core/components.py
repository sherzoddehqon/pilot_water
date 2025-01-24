from dataclasses import dataclass, field
from core.blocks.types import JointType
from core.blocks.blocks import Block, Joint
from core.types import ComponentType
from typing import Dict, List, Optional, Set

@dataclass
class NetworkComponent:
    id: str
    label: str
    component_type: ComponentType = field(init=False)
    manual_order: Optional[int] = None  # For manual order assignment
    connections_to: List[str] = field(default_factory=list)
    connections_from: List[str] = field(default_factory=list)
    block_id: Optional[str] = None  # Reference to containing block
    
    def __post_init__(self):
        prefix = ''.join(c for c in self.id if c.isalpha())
        type_map = {
            'DP': ComponentType.DISTRIBUTION_POINT,
            'MC': ComponentType.CANAL,
            'ZT': ComponentType.GATE,
            'SW': ComponentType.SMART_WATER,
            'F': ComponentType.FIELD
        }
        self.component_type = type_map.get(prefix, ComponentType.CANAL)

    def set_order(self, order: int):
        """Manually set component order"""
        self.manual_order = order

    def add_connection_to(self, target_id: str):
        if target_id not in self.connections_to:
            self.connections_to.append(target_id)

    def add_connection_from(self, source_id: str):
        if source_id not in self.connections_from:
            self.connections_from.append(source_id)