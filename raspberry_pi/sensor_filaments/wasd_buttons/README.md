# WASD buttons

Upload `wasd_buttons.ino` to the Arduino. Connect four normally-open buttons
between these pins and GND:

| Pin | Key / VRPN button |
| --- | --- |
| 2 | W / 0 |
| 3 | A / 1 |
| 4 | S / 2 |
| 5 | D / 3 |

The Arduino uses USB serial at `115200` baud and sends a line only when a
button changes state, for example `W 1` on press and `W 0` on release. Have the
VRPN bridge publish these as four momentary buttons named `W`, `A`, `S`, and
`D` (or map button indices 0--3 to those keys in the Mac program).
