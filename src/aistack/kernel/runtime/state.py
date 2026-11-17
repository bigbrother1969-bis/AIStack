from enum import Enum

class RuntimeState(str, Enum):
    BOOTING = "BOOTING"
    READY = "READY"
