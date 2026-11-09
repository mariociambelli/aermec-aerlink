# Aermec AerLink for Home Assistant

Local control of Aermec fan coil systems through the **AerLink** gateway
(the module used by the *AerPlants* app), without the cloud.

> Unofficial integration, not affiliated with or endorsed by Aermec.
> The Modbus map was found by observation; use it at your own risk.

## Features

For every zone (wall thermostat, e.g. VMF-E19):

| Entity | What it does |
|---|---|
| Climate | Room temperature, setpoint, zone on/off, **fan speed** (Auto, 1, 2, 3, Aux) |
| Sensor: Coil water temperature | Water temperature in the fan coil |
| Sensor: Fan output | Fan/valve output, % |
| Sensor: Fan speed | Fan speed currently applied (also when changed on the thermostat) |
| Binary sensor: Demand | The zone is calling for heat |

Plus one **Plant demand** binary sensor (at least one zone is calling the heat pump).

The setpoint shown and set is the **effective** one: the thermostat knob adds
an offset to the base setpoint, and the integration compensates for it, so if
you ask for 21 °C the plant really aims at 21 °C.

Everything runs locally over Modbus TCP (port 502). Polling every 30 s by default.

## Requirements

- An Aermec AerLink reachable on your LAN (give it a fixed IP in your router).
- Home Assistant 2025.1 or newer.

## Installation

### HACS (recommended)
1. HACS → ⋮ → **Custom repositories** → add `https://github.com/mariociambelli/aermec-aerlink`, category **Integration**.
2. Install **Aermec AerLink** and restart Home Assistant.

### Manual
Copy `custom_components/aermec_aerlink` into your `config/custom_components/` folder and restart.

## Setup

Settings → Devices & services → **Add integration** → *Aermec AerLink*.

- **Host**: IP address of the AerLink.
- **Zone names**: in the same order as in the AerPlants app (zone 1 first),
  separated by commas or one per line.

Options (polling interval, min/max setpoint) are under **Configure**.

## Known limitations

- Tested on one installation with 6 VMF-E19 thermostats, during the **heating** season.
  Cooling setpoint and summer mode are not verified yet: the setpoint written is
  the heating one. Feedback from summer use is welcome.
- The fan code `2` is assumed to be **Auto** (accepted by the gateway, not yet
  confirmed on the thermostat display).
- The AerLink is a small device, often on Wi-Fi: avoid other software polling it
  at the same time and do not port-scan it (it may reboot).
- The AerLink firmware sends a wrong length in Modbus TCP responses. Standard
  Modbus clients (including Home Assistant's Modbus integration) time out;
  this integration ships its own tolerant client.

## Modbus map

See [docs/MODBUS_MAP.md](docs/MODBUS_MAP.md). Corrections and additions are welcome:
open an issue with your thermostat model and what you observed.

## License

MIT
