# KMK firmware for the 4x4 KB2040 macro pad (14 keys + 2 encoders).
# Copy this file to the CIRCUITPY drive as code.py, together with the kmk/ folder.

import board

from kmk.kmk_keyboard import KMKKeyboard
from kmk.keys import KC
from kmk.scanners import DiodeOrientation
from kmk.modules.encoder import EncoderHandler

keyboard = KMKKeyboard()

# Set to True to print key numbers to the serial console (useful for checking the matrix).
# keyboard.debug_enabled = True

# ---------------------------------------------------------------- matrix
# Rows: D4-D7, columns: D8, D9, D10, A0. Diode cathode faces the row (col -> row).
keyboard.row_pins = (board.D4, board.D5, board.D6, board.D7)
keyboard.col_pins = (board.D8, board.D9, board.D10, board.A0)
try:
    keyboard.diode_orientation = DiodeOrientation.COL2ROW
except AttributeError:  # older KMK versions
    keyboard.diode_orientation = DiodeOrientation.COLUMNS

# ---------------------------------------------------------------- encoders
# (pin_a, pin_b, pin_button, is_inverted). The push switches are part of the
# matrix (row 0, column 0 and column 3), so pin_button is None.
encoder_handler = EncoderHandler()
keyboard.modules.append(encoder_handler)
encoder_handler.pins = (
    (board.A1, board.A2, None, False),  # E1 (top left)
    (board.D2, board.D3, None, False),  # E2 (top right)
)
# (counter-clockwise, clockwise, press). Swap the first two if a knob turns the wrong way.
encoder_handler.map = [
    (
        (KC.VOLD, KC.VOLU, KC.NO),
        (KC.PGDN, KC.PGUP, KC.NO),
    ),
]

# ---------------------------------------------------------------- keymap
# Placeholder layout, row by row. Positions 0 and 3 are the encoder push switches.
keyboard.keymap = [
    [
        KC.MUTE, KC.F13, KC.F14, KC.MPLY,
        KC.F15, KC.F16, KC.F17, KC.F18,
        KC.LCTL(KC.C), KC.LCTL(KC.V), KC.LCTL(KC.X), KC.LCTL(KC.Z),
        KC.F19, KC.F20, KC.F21, KC.F22,
    ],
]

if __name__ == '__main__':
    keyboard.go()
