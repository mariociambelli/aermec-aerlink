# AerLink Modbus TCP map (observed)

Port 502, **unit id 1**, 0-based addresses. Zone `i` = 0…63 (zone 1 in the
AerPlants app is `i = 0`). Temperatures are tenths of °C (`205` = 20.5 °C).
FC3 and FC4 return the same values.

| Address | Type | R/W | Meaning | Status |
|---|---|---|---|---|
| 222 + i | holding | R | Room temperature | verified |
| 286 + i | holding | R | Effective setpoint = base setpoint + thermostat knob offset (write → exception 02) | verified |
| 350 + i | holding | R | Fan / valve output, % (0 = stopped) | verified |
| 414 + i | holding | R | Fan speed applied: 1 off, 2 auto(?), 3 speed 1, 4 speed 2, 5 speed 3, 6 aux (write → exception 02) | verified |
| 478 + i | holding | R | Water temperature in the fan coil | verified |
| 606 + i | holding | W | **Fan speed command**: write a code from 414; the gateway applies it within ~15 s and resets the register to 0 | verified (codes 2–6) |
| 734 + i | holding | R/W | **Base heating setpoint**; the effective setpoint (286) follows in ~30 s | verified |
| 798 + i | holding | R | Probably the cooling setpoint | not verified |
| 1300 | holding | R | Number of zones calling the heat pump | verified |
| coil 8 + i | coil | R/W | Zone on/off | verified |
| coil 102 + i | coil | R | Zone calling for heat | verified |

Other blocks exposed by the AerPlants cloud and still unknown: holding 0, 1, 5,
15, 24, 158–163, 542–547, 670–675, 862–867; coils 196–197.

## Firmware quirk

Responses carry an MBAP `length` equal to the real length **+ 12**
(e.g. reading one register declares 17 bytes, sends 5). Parse the response
from the PDU (function code + byte count) and ignore the declared length.

## How the map was found

Changing one value at a time in the AerPlants app or on the wall thermostat
while logging every register, then confirming writes locally with FC5/FC6 and
restoring the original value.
