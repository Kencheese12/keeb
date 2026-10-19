# File: fix_schematic.py
import os
import re
import shutil
import sys
import time

SCH_NAME = "focuspad.kicad_sch"

SPECS = {}
for n in range(1, 15):
    SPECS["SW%d" % n] = {"Footprint": "focuspad:SW_Choc_V2_Hotswap", "LCSC": "C5333465", "hand": False}
for n in range(1, 17):
    SPECS["D%d" % n] = {"Footprint": "Diode_SMD:D_SOD-123", "LCSC": "C81598", "hand": False}
SPECS["SW15"] = {"Footprint": "focuspad:SW_TS-1187A", "LCSC": "C318884", "hand": False}
SPECS["RE1"] = {"Footprint": "focuspad:EC11_Switch_Vertical", "LCSC": "", "hand": True}
SPECS["RE2"] = {"Footprint": "focuspad:EC11_Switch_Vertical", "LCSC": "", "hand": True}
SPECS["U1"] = {"Footprint": "focuspad:KB2040_ConThrough", "LCSC": None, "hand": True}

GLOBAL_REPLACEMENTS = [
    ("Rotary_Encoder:RotaryEncoder_Alps_EC11E-Switch_Vertical_H20mm", "focuspad:EC11_Switch_Vertical"),
    ("Button_Switch_SMD:SW_Push_1P1T_XKB_TS-1187A", "focuspad:SW_TS-1187A"),
    ('"LCSC" "C278348"', '"LCSC" ""'),
]


def candidate_dirs():
    args = getattr(sys, "argv", [])
    if len(args) > 1 and args[1]:
        yield args[1]
    try:
        yield os.path.dirname(os.path.abspath(__file__))
    except NameError:
        pass
    try:
        import pcbnew
        yield os.path.dirname(pcbnew.GetBoard().GetFileName())
    except Exception:
        pass
    yield os.getcwd()


def find_schematic():
    for folder in candidate_dirs():
        path = os.path.join(folder, SCH_NAME)
        if os.path.isfile(path):
            return path
    return None


def find_block_end(text, start):
    depth = 0
    in_string = False
    escaped = False
    for i in range(start, len(text)):
        c = text[i]
        if in_string:
            if escaped:
                escaped = False
            elif c == "\\":
                escaped = True
            elif c == '"':
                in_string = False
            continue
        if c == '"':
            in_string = True
        elif c == "(":
            depth += 1
        elif c == ")":
            depth -= 1
            if depth == 0:
                return i + 1
    raise ValueError("括弧の対応が取れません")


def symbol_blocks(text):
    blocks = []
    for m in re.finditer(r"\(symbol\s+\(lib_id\s", text):
        start = m.start()
        blocks.append((start, find_block_end(text, start)))
    return blocks


def set_property(block, name, value):
    pattern = re.compile(r'(\(property\s+"%s"\s+)"(?:[^"\\]|\\.)*"' % re.escape(name))
    new_block, count = pattern.subn(lambda m: m.group(1) + '"' + value + '"', block, count=1)
    return new_block, count > 0


def set_flag(block, name, value):
    pattern = re.compile(r"\(%s\s+(?:yes|no)\)" % name)
    if pattern.search(block):
        return pattern.sub("(%s %s)" % (name, value), block, count=1)
    anchor = re.search(r"\((?:on_board|in_bom)\s+(?:yes|no)\)", block)
    if anchor is None:
        return block
    pos = anchor.end()
    return block[:pos] + " (%s %s)" % (name, value) + block[pos:]


def apply_spec(block, warnings):
    m = re.search(r'\(property\s+"Reference"\s+"([^"]*)"', block)
    if m is None:
        return block, None
    ref = m.group(1)
    spec = SPECS.get(ref)
    if spec is None:
        return block, None
    block, ok = set_property(block, "Footprint", spec["Footprint"])
    if not ok:
        warnings.append("%s: Footprint 欄が見つかりません" % ref)
    if spec["LCSC"] is not None:
        block, ok = set_property(block, "LCSC", spec["LCSC"])
        if not ok and spec["LCSC"]:
            warnings.append("%s: LCSC 欄がありません（シンボルフィールド表で追加してください）" % ref)
    if spec["hand"]:
        block = set_flag(block, "in_bom", "no")
        block = set_flag(block, "dnp", "yes")
    else:
        block = set_flag(block, "in_bom", "yes")
        block = set_flag(block, "dnp", "no")
    return block, ref


def main():
    path = find_schematic()
    if path is None:
        print("%s が見つかりません。プロジェクトフォルダに置いて実行してください。" % SCH_NAME)
        return

    with open(path, encoding="utf-8", newline="") as f:
        original = f.read()

    text = original
    for old, new in GLOBAL_REPLACEMENTS:
        text = text.replace(old, new)

    warnings = []
    found = set()
    for start, end in reversed(symbol_blocks(text)):
        new_block, ref = apply_spec(text[start:end], warnings)
        if ref is not None:
            found.add(ref)
            text = text[:start] + new_block + text[end:]

    missing = sorted(set(SPECS) - found)

    if text == original:
        print("変更はありません（修正済みです）。")
    else:
        backup = path + time.strftime(".%Y%m%d-%H%M%S.bak")
        shutil.copy2(path, backup)
        with open(path, "w", encoding="utf-8", newline="") as f:
            f.write(text)
        print("回路図を修正しました:", path)
        print("バックアップ:", backup)

    print("処理した部品: %d 個" % len(found))
    if missing:
        print("見つからなかった部品番号:", ", ".join(missing))
    for w in warnings:
        print("注意:", w)


main()