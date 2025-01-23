# core/components.py
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Set

class ComponentType(Enum):
    DISTRIBUTION_POINT = "distribution_point"
    CANAL = "canal"
    GATE = "gate"
    SMART_WATER = "smart_water"
    FIELD = "field"

class JointType(Enum):
    INTERNAL = "internal"     # Connection within same block
    CONFLUENCE = "confluence" # Connection between blocks/levels

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

@dataclass
class Joint:
    """Represents connection within a block"""
    id: str
    joint_type: JointType
    upstream_component: str   # ID of upstream component
    downstream_component: str # ID of downstream component
    attributes: Dict = field(default_factory=dict)

    @property
    def is_confluence(self) -> bool:
        return self.joint_type == JointType.CONFLUENCE

@dataclass
class Block:
    """Represents a network sub-basin"""
    id: str
    order: int  # Manual order assignment
    is_basin: bool = False
    distribution_canal: Optional[str] = None  # Main feeding canal ID
    components: Set[str] = field(default_factory=set)
    joints: Dict[str, Joint] = field(default_factory=dict)
    confluences: Dict[str, Joint] = field(default_factory=dict)
    parent_block: Optional[str] = None
    child_blocks: Set[str] = field(default_factory=set)

    def add_component(self, component_id: str) -> None:
        self.components.add(component_id)

    def add_joint(self, joint: Joint) -> None:
        if joint.is_confluence:
            self.confluences[joint.id] = joint
        else:
            self.joints[joint.id] = joint

    def set_distribution_canal(self, canal_id: str) -> None:
        if canal_id in self.components:
            self.distribution_canal = canal_id

    def add_child_block(self, block_id: str) -> None:
        self.child_blocks.add(block_id)

    def set_parent_block(self, block_id: str) -> None:
        self.parent_block = block_id