# WTH UMR2 Regulator for Home Assistant

This custom Home Assistant integration monitors a WTH UMR2 heating regulator over
the local network. It is not affiliated with WTH and currently provides read-only
sensor entities; it does not send commands to the regulator.

## Requirements

- Home Assistant 2025.1.0 or newer
- A WTH UMR2 reachable from the Home Assistant host
- The regulator's IP address or resolvable hostname

The integration uses plain HTTP and has no external Python requirements.

## Installation

### HACS

Add this repository as a custom repository in HACS, choose **Integration**, and
install **WTH UMR2 Regulator**. Restart Home Assistant afterwards.

### Manual

Copy [`custom_components/wth_umr2`](custom_components/wth_umr2) into the
`custom_components` directory of the Home Assistant configuration directory,
then restart Home Assistant.

## Configuration

1. Open **Settings > Devices & services**.
2. Select **Add integration** and search for **WTH UMR2 Regulator**.
3. Enter the regulator's IP address or hostname.
4. Submit the form.

The config flow validates the device before creating the entry and prevents the
same host from being configured more than once.

## Entities

One device is created for each configured regulator. The integration polls
`http://<host>/get.json?f=$.status.*` every 30 seconds and creates 64 sensors:

- Main state, operating mode, display, LED status, and heat/cool/PWM factors
- Heater, cooler, and pump output percentages
- Eight thermostat states and eight thermostat temperatures
- Ten valve positions
- Maximum, return, and condensate inputs
- Ten temperature inputs
- Fanlink, RF, Modbus, Bluetooth, and Ethernet status
- Ten Fanlink device diagnostics

Communication and connected-device entities are marked as diagnostic. Entity
availability follows the coordinator's last successful update.

## API expectations

The regulator must return HTTP 200 from the endpoint above with a JSON object
containing a `status` object. HTTP errors, timeouts, connection failures, and
responses without `status` are reported as update failures. The integration
does not provide authentication, TLS, writes, or service actions.

## Troubleshooting

- Confirm the host is reachable from the machine running Home Assistant.
- Check **Settings > System > Logs** for `wth_umr2` errors.
- Confirm the endpoint returns JSON with a top-level `status` key:
  `http://<host>/get.json?f=$.status.*`
- If the device was previously configured, remove the existing config entry
  before attempting to add the same host again.

## Project status

This project is being cleaned up and reworked. The current implementation is
small and intentionally documents only behavior present in the code. Historical
notes and superseded release documents are kept in [`legacy docs`](legacy%20docs)
for reference and are not part of the active documentation.

## License

The license file is not currently present in this working tree.
