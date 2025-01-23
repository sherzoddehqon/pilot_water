from enum import Enum

class ComponentType(Enum):
    """Core component types in the irrigation network"""
    DISTRIBUTION_POINT = "distribution_point"
    CANAL = "canal" 
    GATE = "gate"
    SMART_WATER = "smart_water"
    FIELD = "field"

    def __str__(self) -> str:
        return self.value

    @property
    def description(self) -> str:
        descriptions = {
            ComponentType.DISTRIBUTION_POINT: "Water distribution control point",
            ComponentType.CANAL: "Water transport channel",
            ComponentType.GATE: "Flow control gate",
            ComponentType.SMART_WATER: "Smart water metering device",
            ComponentType.FIELD: "Irrigated field area"
        }
        return descriptions[self]