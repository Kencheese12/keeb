# File: place_focuspad.py
import math
import os

import pcbnew

ORIGIN_X = 100.0
ORIGIN_Y = 100.0
BOARD_W = 86.2
BOARD_H = 86.2
CORNER_R = 3.0
MARGIN = 5.0
PITCH = 19.05

KB_CENTER_X = 51.55
KB_PIN1_FROM_EDGE = 3.53
KB_PIN1_TO_CENTER = 13.97

RESET_POS = (43.1, 81.0)
HOLE_POS = [(3.2, 3.2), (83.0, 3.2), (3.2, 83.0), (83.0, 83.0)]

ENCODERS = {
    "RE1": (0, 0),
    "RE2": (3, 0),
}

SOCKETS = {
    "SW1": (1, 0, 180),
    "SW2": (2, 0, 90),
    "SW3": (0, 1, 0),
    "SW4": (1, 1, 180),
    "SW5": (2, 1, 90),
    "SW6": (3, 1, 0),
    "SW7": (0, 2, 0),
    "SW8": (1, 2, 0),
    "SW9": (2, 2, 0),
    "SW10": (3, 2, 0),
    "SW11": (0, 3, 0),
    "SW12": (1, 3, 0),
    "SW13": (2, 3, 0),
    "SW14": (3, 3, 0),
}

DIODES = {
    "D1": "RE1",
    "D2": "SW1",
    "D3": "SW2",
    "D4": "RE2",
    "D5": "SW3",
    "D6": "SW4",
    "D7": "SW5",
    "D8": "SW6",
    "D9": "SW7",
    "D10": "SW8",
    "D11": "SW9",
    "D12": "SW10",
    "D13": "SW11",
    "D14": "SW12",
    "D15": "SW13",
    "D16": "SW14",
}

SOCKET_PADS_TOP_VIEW = {
    "1": (-3.275, -5.95),
    "2": (8.275, -3.75),
}

CANDIDATES = [(1, 0), (-1, 0), (1, 180), (-1, 180)]


def mm(value):
    return pcbnew.FromMM(value)


def board_point(x, y):
    return pcbnew.VECTOR2I(mm(ORIGIN_X + x), mm(ORIGIN_Y + y))


def key_center(col, row):
    return (MARGIN + PITCH / 2 + col * PITCH, MARGIN + PITCH / 2 + row * PITCH)


def rotate_local(x, y, deg):
    a = math.radians(deg)
    return (x * math.cos(a) + y * math.sin(a), y * math.cos(a) - x * math.sin(a))


def diode_spec(owner):
    if owner.startswith("RE"):
        cx, cy = key_center(*ENCODERS[owner])
        return (cx, cy - 3.0, 180)
    col, row, deg = SOCKETS[owner]
    cx, cy = key_center(col, row)
    if deg == 0:
        return (cx, cy + 7.2, 180)
    if deg == 180:
        return (cx - 8.275, cy + 7.2, 0)
    return (cx + 4.0, cy, 270)


def flip_left_right(fp):
    pos = fp.GetPosition()
    direction = getattr(pcbnew, "FLIP_DIRECTION_LEFT_RIGHT", None)
    if direction is None:
        fp.Flip(pos, True)
    else:
        fp.Flip(pos, direction)


def place(fp, x, y, deg, bottom, sign, extra):
    if fp.IsFlipped():
        flip_left_right(fp)
    fp.SetOrientationDegrees(0)
    fp.SetPosition(board_point(x, y))
    angle = sign * deg
    if bottom:
        flip_left_right(fp)
        angle += extra
    if angle % 360:
        fp.Rotate(fp.GetPosition(), pcbnew.EDA_ANGLE(angle, pcbnew.DEGREES_T))


def find_pad(fp, number):
    finder = getattr(fp, "FindPadByNumber", None)
    if finder is None:
        finder = fp.FindPadByName
    return finder(number)


def place_all(footprints, sign, extra):
    for ref, (col, row) in ENCODERS.items():
        x, y = key_center(col, row)
        place(footprints[ref], x, y, 0, False, sign, extra)
    for ref, (col, row, deg) in SOCKETS.items():
        x, y = key_center(col, row)
        place(footprints[ref], x, y, deg, True, sign, extra)
    for ref, owner in DIODES.items():
        x, y, deg = diode_spec(owner)
        place(footprints[ref], x, y, deg, True, sign, extra)
    kb_y = KB_PIN1_FROM_EDGE + KB_PIN1_TO_CENTER
    place(footprints["U1"], KB_CENTER_X, kb_y, 0, False, sign, extra)
    place(footprints["SW15"], RESET_POS[0], RESET_POS[1], 0, True, sign, extra)


def socket_error(footprints):
    worst = 0.0
    for ref, (col, row, deg) in SOCKETS.items():
        fp = footprints[ref]
        cx, cy = key_center(col, row)
        for number, (lx, ly) in SOCKET_PADS_TOP_VIEW.items():
            pad = find_pad(fp, number)
            if pad is None or not pad.IsOnLayer(pcbnew.B_Cu):
                return 99.0
            ex, ey = rotate_local(lx, ly, deg)
            expected = board_point(cx + ex, cy + ey)
            got = pad.GetPosition()
            err = math.hypot(pcbnew.ToMM(got.x - expected.x), pcbnew.ToMM(got.y - expected.y))
            worst = max(worst, err)
    return worst


def add_edge_shape(board, shape_type, points):
    shape = pcbnew.PCB_SHAPE(board)
    shape.SetShape(shape_type)
    if shape_type == pcbnew.SHAPE_T_ARC:
        shape.SetArcGeometry(board_point(*points[0]), board_point(*points[1]), board_point(*points[2]))
    else:
        shape.SetStart(board_point(*points[0]))
        shape.SetEnd(board_point(*points[1]))
    shape.SetLayer(pcbnew.Edge_Cuts)
    shape.SetWidth(mm(0.1))
    board.Add(shape)


def draw_outline(board):
    for item in list(board.GetDrawings()):
        if item.GetLayer() == pcbnew.Edge_Cuts:
            board.Remove(item)
    w = BOARD_W
    h = BOARD_H
    r = CORNER_R
    d = r - r / math.sqrt(2)
    seg = pcbnew.SHAPE_T_SEGMENT
    arc = pcbnew.SHAPE_T_ARC
    add_edge_shape(board, seg, [(r, 0), (w - r, 0)])
    add_edge_shape(board, seg, [(w, r), (w, h - r)])
    add_edge_shape(board, seg, [(w - r, h), (r, h)])
    add_edge_shape(board, seg, [(0, h - r), (0, r)])
    add_edge_shape(board, arc, [(0, r), (d, d), (r, 0)])
    add_edge_shape(board, arc, [(w - r, 0), (w - d, d), (w, r)])
    add_edge_shape(board, arc, [(w, h - r), (w - d, h - d), (w - r, h)])
    add_edge_shape(board, arc, [(r, h), (d, h - d), (0, h - r)])


def add_mounting_holes(board):
    lib = os.path.join(os.path.dirname(board.GetFileName()), "focuspad.pretty")
    for index, (x, y) in enumerate(HOLE_POS, start=1):
        ref = "H%d" % index
        fp = board.FindFootprintByReference(ref)
        if fp is None:
            fp = pcbnew.FootprintLoad(lib, "MountingHole_M2")
            if fp is None:
                print("MountingHole_M2 を読み込めませんでした:", lib)
                return
            fp.SetReference(ref)
            board.Add(fp)
        fp.SetPosition(board_point(x, y))


def main():
    board = pcbnew.GetBoard()
    refs = list(ENCODERS) + list(SOCKETS) + list(DIODES) + ["U1", "SW15"]
    footprints = {}
    missing = []
    for ref in refs:
        fp = board.FindFootprintByReference(ref)
        if fp is None:
            missing.append(ref)
        else:
            footprints[ref] = fp
    if missing:
        print("見つからないフットプリント:", ", ".join(missing))
        print("先に「回路図からPCBを更新（F8）」を実行してください。")
        return

    chosen = None
    err = 99.0
    for sign, extra in CANDIDATES:
        place_all(footprints, sign, extra)
        err = socket_error(footprints)
        if err < 0.01:
            chosen = (sign, extra)
            break

    if chosen is None:
        print("警告: ソケットの向きを自動判定できませんでした（誤差 %.3f mm）。" % err)
        print("手順書の配置表を見て SW1〜SW14 の向きを手動で確認してください。")
    else:
        print("ソケットの向きを確認しました（sign=%d, extra=%d）。" % chosen)

    draw_outline(board)
    add_mounting_holes(board)
    pcbnew.Refresh()
    print("配置が完了しました。保存してください。")


main()