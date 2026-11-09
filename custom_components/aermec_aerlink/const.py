"""Constants and Modbus register map for the Aermec AerLink.

All addresses are 0-based, Modbus unit id 1. Zone ``i`` (0…63) is at
``BASE + i``. Temperatures are in tenths of a degree Celsius.
See docs/MODBUS_MAP.md for how each value was verified.
"""
from __future__ import annotations

DOMAIN = "aermec_aerlink"

CONF_ZONES = "zones"
CONF_MIN_TEMP = "min_temp"
CONF_MAX_TEMP = "max_temp"

DEFAULT_PORT = 502
DEFAULT_SCAN_INTERVAL = 30
DEFAULT_MIN_TEMP = 15.0
DEFAULT_MAX_TEMP = 26.0
MAX_ZONES = 64

# Holding registers (read)
REG_ROOM_TEMP = 222      # room temperature measured by the thermostat
REG_EFFECTIVE_SP = 286   # effective setpoint = base setpoint + thermostat knob offset (read only)
REG_FAN_OUTPUT = 350     # fan / valve output, %
REG_FAN_STATE = 414      # fan speed currently applied (read only), see FAN_CODES
REG_WATER_TEMP = 478     # water temperature in the fan coil
REG_PLANT_DEMAND = 1300  # number of zones calling the heat pump

# Holding registers (write)
REG_FAN_COMMAND = 606    # write a FAN_CODES value; the AerLink applies it and resets to 0
REG_BASE_SP = 734        # base (heating) setpoint, read/write

# Coils
COIL_ZONE_ON = 8         # zone on/off (read/write)
COIL_DEMAND = 102        # zone is calling for heat (read)

# Fan speed codes (REG_FAN_STATE / REG_FAN_COMMAND)
FAN_CODE_OFF = 1
FAN_CODES: dict[int, str] = {
    2: "auto",
    3: "low",
    4: "medium",
    5: "high",
    6: "aux",
}
FAN_MODES_TO_CODE = {mode: code for code, mode in FAN_CODES.items()}

# After a setpoint write the effective setpoint updates with ~30 s delay:
# during this window the stored knob offset is reused.
SETTLE_SECONDS = 90
