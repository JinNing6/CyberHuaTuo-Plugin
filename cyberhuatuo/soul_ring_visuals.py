"""Generate shareable Soul Ring PNG and GIF artifacts without external image dependencies."""

from __future__ import annotations

import math
import re
import struct
import zlib
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path

from .achievements import (
    _candidate_first_install_copy_lines,
    calculate_soul_rings,
    get_alchemy_profile,
    get_cultivation_profile,
    get_direction_for_framework,
    get_next_soul_ring_progress,
)

DEFAULT_WIDTH = 640
DEFAULT_HEIGHT = 360
DEFAULT_FRAMES = 24
DEFAULT_FRAME_DURATION_MS = 90

PALETTE: list[tuple[int, int, int]] = [
    (7, 10, 22),
    (10, 16, 34),
    (14, 27, 45),
    (24, 49, 74),
    (36, 78, 104),
    (0, 208, 156),
    (65, 255, 214),
    (229, 244, 255),
    (255, 245, 180),
    (255, 204, 63),
    (172, 111, 255),
    (86, 54, 143),
    (22, 24, 36),
    (248, 83, 83),
    (255, 185, 92),
    (105, 157, 255),
]

RING_COLORS = (7, 9, 10, 12, 13, 14, 9, 13, 14)

RING_COUNT_LABELS = {
    0: "No Ring",
    1: "First Ring",
    2: "Second Ring",
    3: "Third Ring",
    4: "Fourth Ring",
    5: "Fifth Ring",
    6: "Sixth Ring",
    7: "Seventh Ring",
    8: "Eighth Ring",
    9: "Nine Ring Supreme",
}

NEXT_RING_LABELS_BY_THRESHOLD = {
    1: "White Ring",
    2: "Yellow Ring",
    4: "Twin Rings",
    7: "Triple Rings",
    11: "Four Rings",
    16: "Five Rings",
    26: "Six Rings",
    41: "Seven Rings",
    61: "Eight Rings",
    81: "Nine Ring Supreme",
}


FONT_5X7 = {
    " ": ("00000", "00000", "00000", "00000", "00000", "00000", "00000"),
    "-": ("00000", "00000", "00000", "11110", "00000", "00000", "00000"),
    "_": ("00000", "00000", "00000", "00000", "00000", "00000", "11111"),
    ".": ("00000", "00000", "00000", "00000", "00000", "01100", "01100"),
    "/": ("00001", "00010", "00100", "01000", "10000", "00000", "00000"),
    ":": ("00000", "01100", "01100", "00000", "01100", "01100", "00000"),
    "@": ("01110", "10001", "10111", "10101", "10111", "10000", "01110"),
    "#": ("01010", "11111", "01010", "01010", "11111", "01010", "00000"),
    "0": ("01110", "10001", "10011", "10101", "11001", "10001", "01110"),
    "1": ("00100", "01100", "00100", "00100", "00100", "00100", "01110"),
    "2": ("01110", "10001", "00001", "00010", "00100", "01000", "11111"),
    "3": ("11110", "00001", "00001", "01110", "00001", "00001", "11110"),
    "4": ("00010", "00110", "01010", "10010", "11111", "00010", "00010"),
    "5": ("11111", "10000", "10000", "11110", "00001", "00001", "11110"),
    "6": ("00110", "01000", "10000", "11110", "10001", "10001", "01110"),
    "7": ("11111", "00001", "00010", "00100", "01000", "01000", "01000"),
    "8": ("01110", "10001", "10001", "01110", "10001", "10001", "01110"),
    "9": ("01110", "10001", "10001", "01111", "00001", "00010", "11100"),
    "A": ("01110", "10001", "10001", "11111", "10001", "10001", "10001"),
    "B": ("11110", "10001", "10001", "11110", "10001", "10001", "11110"),
    "C": ("01110", "10001", "10000", "10000", "10000", "10001", "01110"),
    "D": ("11110", "10001", "10001", "10001", "10001", "10001", "11110"),
    "E": ("11111", "10000", "10000", "11110", "10000", "10000", "11111"),
    "F": ("11111", "10000", "10000", "11110", "10000", "10000", "10000"),
    "G": ("01110", "10001", "10000", "10111", "10001", "10001", "01111"),
    "H": ("10001", "10001", "10001", "11111", "10001", "10001", "10001"),
    "I": ("01110", "00100", "00100", "00100", "00100", "00100", "01110"),
    "J": ("00111", "00010", "00010", "00010", "10010", "10010", "01100"),
    "K": ("10001", "10010", "10100", "11000", "10100", "10010", "10001"),
    "L": ("10000", "10000", "10000", "10000", "10000", "10000", "11111"),
    "M": ("10001", "11011", "10101", "10101", "10001", "10001", "10001"),
    "N": ("10001", "11001", "10101", "10011", "10001", "10001", "10001"),
    "O": ("01110", "10001", "10001", "10001", "10001", "10001", "01110"),
    "P": ("11110", "10001", "10001", "11110", "10000", "10000", "10000"),
    "Q": ("01110", "10001", "10001", "10001", "10101", "10010", "01101"),
    "R": ("11110", "10001", "10001", "11110", "10100", "10010", "10001"),
    "S": ("01111", "10000", "10000", "01110", "00001", "00001", "11110"),
    "T": ("11111", "00100", "00100", "00100", "00100", "00100", "00100"),
    "U": ("10001", "10001", "10001", "10001", "10001", "10001", "01110"),
    "V": ("10001", "10001", "10001", "10001", "10001", "01010", "00100"),
    "W": ("10001", "10001", "10001", "10101", "10101", "10101", "01010"),
    "X": ("10001", "10001", "01010", "00100", "01010", "10001", "10001"),
    "Y": ("10001", "10001", "01010", "00100", "00100", "00100", "00100"),
    "Z": ("11111", "00001", "00010", "00100", "01000", "10000", "11111"),
}


@dataclass(frozen=True)
class SoulRingVisualSnapshot:
    username: str
    framework: str
    direction_key: str
    direction_name: str
    total_prescriptions: int
    direction_prescriptions: int
    ring_name: str
    ring_count: int
    current_rings: str
    next_ring_name: str
    needed: int
    title: str
    global_rank: int
    global_total: int
    provenance: str


@dataclass(frozen=True)
class SoulRingVisualArtifact:
    snapshot: SoulRingVisualSnapshot
    png_path: Path
    gif_path: Path
    width: int
    height: int
    frames: int


def _clamp(value: int, minimum: int, maximum: int) -> int:
    return max(minimum, min(maximum, int(value)))


def _safe_ascii(value: str, fallback: str = "UNKNOWN") -> str:
    cleaned = re.sub(r"[^A-Za-z0-9_.@/#:-]+", "-", value.strip())
    cleaned = cleaned.strip("-")
    return cleaned[:48] or fallback


def _safe_filename(value: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9_.-]+", "-", value.strip().lower())
    cleaned = cleaned.strip(".-")
    return cleaned[:80] or "soul-ring"


def _current_ring_label(ring_count: int) -> str:
    if ring_count in RING_COUNT_LABELS:
        return RING_COUNT_LABELS[ring_count]
    if ring_count > 0:
        return f"{ring_count} Rings"
    return "No Ring"


def _next_ring_label(progress: dict) -> str:
    try:
        threshold = int(progress.get("next_min_count", 0))
    except (TypeError, ValueError):
        threshold = 0
    return NEXT_RING_LABELS_BY_THRESHOLD.get(threshold, "Next Ring")


def _default_output_dir() -> Path:
    return Path.home() / ".cyberhuatuo" / "visuals"


def build_soul_ring_visual_snapshot(
    github_username: str,
    framework: str = "langchain",
) -> SoulRingVisualSnapshot:
    username = github_username.strip().lstrip("@") or "your-github-username"
    framework_key = framework.strip() or "langchain"
    direction_key = get_direction_for_framework(framework_key)
    cultivation = get_cultivation_profile(username)
    alchemy = get_alchemy_profile(username)

    target_direction = next(
        (direction for direction in alchemy.get("directions", []) if direction.get("key") == direction_key),
        None,
    )
    if target_direction is None:
        target_direction = alchemy.get("primary")

    if target_direction is None:
        direction_count = 0
        direction_name = direction_key.replace("-", " ").title()
        current_rings, ring_name, ring_count = calculate_soul_rings(direction_count)
        progress = get_next_soul_ring_progress(direction_count)
    else:
        direction_count = int(target_direction.get("count", 0))
        direction_name = _safe_ascii(str(target_direction.get("name_en") or direction_key), direction_key.upper())
        current_rings = str(target_direction.get("rings", ""))
        ring_count = int(target_direction.get("ring_count", 0))
        ring_name = str(target_direction.get("ring_name", _current_ring_label(ring_count)))
        progress = target_direction.get("next_ring") or get_next_soul_ring_progress(direction_count)

    title = _safe_ascii(str(cultivation.get("title_en", "Intern Apprentice")), "Intern Apprentice")
    return SoulRingVisualSnapshot(
        username=username,
        framework=framework_key,
        direction_key=direction_key,
        direction_name=direction_name,
        total_prescriptions=int(cultivation.get("contribution_count", 0)),
        direction_prescriptions=direction_count,
        ring_name=_safe_ascii(str(ring_name), _current_ring_label(ring_count)),
        ring_count=ring_count,
        current_rings=current_rings,
        next_ring_name=_safe_ascii(str(progress.get("next_ring_name", "")), _next_ring_label(progress)),
        needed=max(0, int(progress.get("needed", 0))),
        title=title,
        global_rank=int(cultivation.get("global_rank", 0)),
        global_total=int(cultivation.get("global_total", 0)),
        provenance="current local CyberHuaTuo contribution snapshot",
    )


class IndexedCanvas:
    def __init__(self, width: int, height: int, fill: int = 0) -> None:
        self.width = width
        self.height = height
        self.pixels = bytearray([fill] * (width * height))

    def set(self, x: int, y: int, color: int) -> None:
        if 0 <= x < self.width and 0 <= y < self.height:
            self.pixels[y * self.width + x] = color

    def rect(self, x0: int, y0: int, x1: int, y1: int, color: int) -> None:
        x0, x1 = sorted((_clamp(x0, 0, self.width - 1), _clamp(x1, 0, self.width - 1)))
        y0, y1 = sorted((_clamp(y0, 0, self.height - 1), _clamp(y1, 0, self.height - 1)))
        for y in range(y0, y1 + 1):
            row = y * self.width
            for x in range(x0, x1 + 1):
                self.pixels[row + x] = color

    def line(self, x0: int, y0: int, x1: int, y1: int, color: int) -> None:
        dx = abs(x1 - x0)
        sx = 1 if x0 < x1 else -1
        dy = -abs(y1 - y0)
        sy = 1 if y0 < y1 else -1
        err = dx + dy
        while True:
            self.set(x0, y0, color)
            if x0 == x1 and y0 == y1:
                break
            e2 = 2 * err
            if e2 >= dy:
                err += dy
                x0 += sx
            if e2 <= dx:
                err += dx
                y0 += sy

    def ellipse_points(
        self,
        cx: float,
        cy: float,
        rx: float,
        ry: float,
        rotation: float,
        color: int,
        thickness: int = 1,
        step_count: int = 420,
    ) -> None:
        cos_r = math.cos(rotation)
        sin_r = math.sin(rotation)
        for i in range(step_count):
            t = 2.0 * math.pi * i / step_count
            x = math.cos(t) * rx
            y = math.sin(t) * ry
            px = int(cx + x * cos_r - y * sin_r)
            py = int(cy + x * sin_r + y * cos_r)
            for ox in range(-thickness, thickness + 1):
                for oy in range(-thickness, thickness + 1):
                    if ox * ox + oy * oy <= thickness * thickness:
                        self.set(px + ox, py + oy, color)

    def text(self, x: int, y: int, text: str, color: int, scale: int = 2) -> None:
        cursor = x
        for char in text.upper():
            glyph = FONT_5X7.get(char, FONT_5X7[" "])
            for gy, row in enumerate(glyph):
                for gx, bit in enumerate(row):
                    if bit == "1":
                        self.rect(
                            cursor + gx * scale,
                            y + gy * scale,
                            cursor + (gx + 1) * scale - 1,
                            y + (gy + 1) * scale - 1,
                            color,
                        )
            cursor += 6 * scale

    def to_rgb_bytes(self) -> bytes:
        out = bytearray()
        for index in self.pixels:
            out.extend(PALETTE[index])
        return bytes(out)


def _draw_background(canvas: IndexedCanvas, frame_index: int, frame_count: int) -> None:
    width, height = canvas.width, canvas.height
    phase = frame_index / max(frame_count, 1)
    for y in range(height):
        for x in range(width):
            wave = math.sin((x / width) * math.pi * 2 + phase * math.pi * 2)
            if y < height * 0.18:
                color = 2 if wave > 0.4 else 1
            elif x < width * 0.57:
                color = 1 if (x + y + frame_index) % 37 else 4
            else:
                color = 2 if (x * 3 + y * 2) % 41 else 4
            canvas.set(x, y, color)

    for y in range(0, height, max(18, height // 14)):
        canvas.line(0, y, width - 1, y, 3)
    for x in range(0, width, max(24, width // 18)):
        canvas.line(x, 0, x, height - 1, 3)


def _draw_progress(canvas: IndexedCanvas, snapshot: SoulRingVisualSnapshot) -> None:
    width, height = canvas.width, canvas.height
    x0 = int(width * 0.58)
    y0 = int(height * 0.72)
    bar_w = int(width * 0.34)
    bar_h = max(8, int(height * 0.035))
    threshold = max(snapshot.direction_prescriptions + snapshot.needed, 1)
    fill_w = int(bar_w * min(1.0, snapshot.direction_prescriptions / threshold))
    canvas.rect(x0, y0, x0 + bar_w, y0 + bar_h, 3)
    canvas.rect(x0 + 2, y0 + 2, x0 + max(2, fill_w), y0 + bar_h - 2, 5)
    canvas.text(x0, y0 + bar_h + 10, f"NEXT {snapshot.next_ring_name[:16]} NEED {snapshot.needed}", 8, 1)


def _draw_ring_scene(
    canvas: IndexedCanvas,
    snapshot: SoulRingVisualSnapshot,
    frame_index: int,
    frame_count: int,
) -> None:
    width, height = canvas.width, canvas.height
    cx = width * 0.31
    cy = height * 0.54
    base_rx = width * 0.19
    base_ry = height * 0.13
    phase = 2.0 * math.pi * frame_index / max(frame_count, 1)
    ring_total = max(1, min(9, snapshot.ring_count or 1))

    for i in range(ring_total):
        color = RING_COLORS[i % len(RING_COLORS)] if snapshot.ring_count else 4
        rx = base_rx + i * width * 0.012
        ry = base_ry + i * height * 0.007
        rotation = -0.34 + phase * (0.22 + i * 0.015)
        canvas.ellipse_points(cx, cy, rx + 5, ry + 4, rotation, 3, thickness=2)
        canvas.ellipse_points(cx, cy, rx, ry, rotation, color, thickness=2)
        shine_t = phase * (1.6 + i * 0.11) + i
        sx = int(cx + math.cos(shine_t) * rx)
        sy = int(cy + math.sin(shine_t) * ry)
        canvas.rect(sx - 2, sy - 2, sx + 2, sy + 2, 7)

    for i in range(18):
        t = phase + i * 0.77
        px = int(cx + math.cos(t) * (base_rx + 34 + (i % 4) * 4))
        py = int(cy + math.sin(t * 1.2) * (base_ry + 26 + (i % 3) * 3))
        canvas.set(px, py, 6 if i % 3 else 9)
        canvas.set(px + 1, py, 7)


def _draw_text_panel(canvas: IndexedCanvas, snapshot: SoulRingVisualSnapshot) -> None:
    width, height = canvas.width, canvas.height
    scale = max(1, width // 420)
    panel_x = int(width * 0.56)
    canvas.text(int(width * 0.05), int(height * 0.07), "CYBERHUATUO", 6, scale)
    canvas.text(int(width * 0.05), int(height * 0.14), "SOUL RING VISUAL", 8, 1)
    canvas.text(panel_x, int(height * 0.20), f"@{_safe_ascii(snapshot.username)}"[:24], 7, scale)
    canvas.text(panel_x, int(height * 0.32), snapshot.title[:24], 6, 1)
    canvas.text(panel_x, int(height * 0.42), f"DIR {snapshot.direction_name[:18]}", 8, 1)
    canvas.text(panel_x, int(height * 0.50), f"RING {snapshot.ring_count} / {snapshot.ring_name[:16]}", 9, 1)
    canvas.text(panel_x, int(height * 0.58), f"RX {snapshot.direction_prescriptions} TOTAL {snapshot.total_prescriptions}", 7, 1)
    rank = "UNRANKED" if snapshot.global_rank <= 0 else f"RANK {snapshot.global_rank}/{snapshot.global_total}"
    canvas.text(panel_x, int(height * 0.65), rank, 15, 1)


def render_soul_ring_frame(
    snapshot: SoulRingVisualSnapshot,
    width: int,
    height: int,
    frame_index: int,
    frame_count: int,
) -> IndexedCanvas:
    canvas = IndexedCanvas(width, height)
    _draw_background(canvas, frame_index, frame_count)
    _draw_ring_scene(canvas, snapshot, frame_index, frame_count)
    _draw_text_panel(canvas, snapshot)
    _draw_progress(canvas, snapshot)
    return canvas


def _png_chunk(chunk_type: bytes, data: bytes) -> bytes:
    return (
        struct.pack(">I", len(data))
        + chunk_type
        + data
        + struct.pack(">I", zlib.crc32(chunk_type + data) & 0xFFFFFFFF)
    )


def write_png(path: Path, canvas: IndexedCanvas) -> None:
    width, height = canvas.width, canvas.height
    raw = bytearray()
    rgb = canvas.to_rgb_bytes()
    stride = width * 3
    for y in range(height):
        raw.append(0)
        raw.extend(rgb[y * stride : (y + 1) * stride])
    payload = b"".join(
        [
            b"\x89PNG\r\n\x1a\n",
            _png_chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)),
            _png_chunk(b"IDAT", zlib.compress(bytes(raw), 9)),
            _png_chunk(b"IEND", b""),
        ]
    )
    path.write_bytes(payload)


class _BitPacker:
    def __init__(self) -> None:
        self.data = bytearray()
        self.accumulator = 0
        self.bit_count = 0

    def write(self, code: int, size: int) -> None:
        self.accumulator |= code << self.bit_count
        self.bit_count += size
        while self.bit_count >= 8:
            self.data.append(self.accumulator & 0xFF)
            self.accumulator >>= 8
            self.bit_count -= 8

    def finish(self) -> bytes:
        if self.bit_count:
            self.data.append(self.accumulator & 0xFF)
        return bytes(self.data)


def _lzw_encode(indices: bytes, min_code_size: int = 4) -> bytes:
    clear = 1 << min_code_size
    end = clear + 1
    next_code = end + 1
    code_size = min_code_size + 1
    dictionary = {(i,): i for i in range(clear)}
    packer = _BitPacker()
    packer.write(clear, code_size)
    if not indices:
        packer.write(end, code_size)
        return packer.finish()

    w = (indices[0],)
    for value in indices[1:]:
        wk = w + (value,)
        if wk in dictionary:
            w = wk
            continue
        packer.write(dictionary[w], code_size)
        if next_code < 4096:
            dictionary[wk] = next_code
            next_code += 1
            if next_code > (1 << code_size) and code_size < 12:
                code_size += 1
        else:
            packer.write(clear, code_size)
            dictionary = {(i,): i for i in range(clear)}
            next_code = end + 1
            code_size = min_code_size + 1
        w = (value,)
    packer.write(dictionary[w], code_size)
    packer.write(end, code_size)
    return packer.finish()


def _sub_blocks(data: bytes) -> bytes:
    chunks = bytearray()
    for offset in range(0, len(data), 255):
        block = data[offset : offset + 255]
        chunks.append(len(block))
        chunks.extend(block)
    chunks.append(0)
    return bytes(chunks)


def write_gif(
    path: Path,
    frames: Iterable[IndexedCanvas],
    duration_ms: int = DEFAULT_FRAME_DURATION_MS,
) -> None:
    frame_list = list(frames)
    if not frame_list:
        raise ValueError("at least one frame is required")
    width, height = frame_list[0].width, frame_list[0].height
    palette_bytes = bytearray()
    for rgb in PALETTE:
        palette_bytes.extend(rgb)
    palette_bytes.extend(b"\x00\x00\x00" * (16 - len(PALETTE)))

    payload = bytearray()
    payload.extend(b"GIF89a")
    payload.extend(struct.pack("<HH", width, height))
    payload.extend(bytes([0b10000011, 0, 0]))
    payload.extend(palette_bytes)
    payload.extend(b"\x21\xff\x0bNETSCAPE2.0\x03\x01\x00\x00\x00")
    delay_cs = max(2, int(duration_ms / 10))
    for frame in frame_list:
        if frame.width != width or frame.height != height:
            raise ValueError("all GIF frames must share one size")
        payload.extend(b"\x21\xf9\x04")
        payload.extend(bytes([0b00000100]))
        payload.extend(struct.pack("<H", delay_cs))
        payload.extend(b"\x00\x00")
        payload.extend(b"\x2c")
        payload.extend(struct.pack("<HHHH", 0, 0, width, height))
        payload.append(0)
        payload.append(4)
        payload.extend(_sub_blocks(_lzw_encode(bytes(frame.pixels), min_code_size=4)))
    payload.extend(b"\x3b")
    path.write_bytes(bytes(payload))


def create_soul_ring_visual_artifact(
    github_username: str,
    framework: str = "langchain",
    output_dir: str | Path | None = None,
    frames: int = DEFAULT_FRAMES,
    width: int = DEFAULT_WIDTH,
    height: int = DEFAULT_HEIGHT,
) -> SoulRingVisualArtifact:
    snapshot = build_soul_ring_visual_snapshot(github_username, framework)
    safe_user = _safe_filename(snapshot.username)
    safe_framework = _safe_filename(snapshot.framework)
    target_dir = Path(output_dir) if output_dir else _default_output_dir()
    target_dir.mkdir(parents=True, exist_ok=True)
    frame_count = _clamp(frames, 6, 72)
    image_width = _clamp(width, 320, 960)
    image_height = _clamp(height, 180, 540)
    base_name = f"cyberhuatuo-soul-ring-{safe_user}-{safe_framework}"
    png_path = (target_dir / f"{base_name}.png").resolve()
    gif_path = (target_dir / f"{base_name}.gif").resolve()

    rendered_frames = [
        render_soul_ring_frame(snapshot, image_width, image_height, index, frame_count)
        for index in range(frame_count)
    ]
    write_png(png_path, rendered_frames[0])
    write_gif(gif_path, rendered_frames, duration_ms=DEFAULT_FRAME_DURATION_MS)
    return SoulRingVisualArtifact(
        snapshot=snapshot,
        png_path=png_path,
        gif_path=gif_path,
        width=image_width,
        height=image_height,
        frames=frame_count,
    )


def format_soul_ring_visual_artifact(
    github_username: str,
    framework: str = "langchain",
    output_dir: str | Path | None = None,
    frames: int = DEFAULT_FRAMES,
    width: int = DEFAULT_WIDTH,
    height: int = DEFAULT_HEIGHT,
) -> str:
    artifact = create_soul_ring_visual_artifact(
        github_username=github_username,
        framework=framework,
        output_dir=output_dir,
        frames=frames,
        width=width,
        height=height,
    )
    snapshot = artifact.snapshot
    install_lines = _candidate_first_install_copy_lines()
    return "\n".join(
        [
            "# Soul Ring Visual Artifact",
            "",
            f"- GitHub: @{snapshot.username}",
            f"- Framework: `{snapshot.framework}`",
            f"- Direction: {snapshot.direction_name} (`{snapshot.direction_key}`)",
            f"- Current ring: {snapshot.ring_count} / {snapshot.ring_name}",
            f"- Direction prescriptions: {snapshot.direction_prescriptions}",
            f"- Total prescriptions: {snapshot.total_prescriptions}",
            f"- Next ring: {snapshot.next_ring_name}; needed: {snapshot.needed}",
            f"- Provenance: {snapshot.provenance}",
            f"- PNG cover: `{artifact.png_path}`",
            f"- GIF animation: `{artifact.gif_path}`",
            f"- Size: {artifact.width}x{artifact.height}; frames: {artifact.frames}",
            "",
            "## Chat Preview",
            f"![CyberHuaTuo Soul Ring GIF]({artifact.gif_path.as_posix()})",
            "",
            "## Static Fallback",
            f"![CyberHuaTuo Soul Ring PNG]({artifact.png_path.as_posix()})",
            "",
            "## Share Copy",
            "```text",
            (
                f"@{snapshot.username} lit a CyberHuaTuo Soul Ring in {snapshot.direction_name}: "
                f"{snapshot.direction_prescriptions} real prescription(s), next ring "
                f"{snapshot.next_ring_name} needs {snapshot.needed}."
            ),
            *install_lines,
            f"Visual: {artifact.gif_path.as_posix()}",
            (
                "Record share attribution: cyberhuatuo record-share "
                f"--username {snapshot.username} --framework {snapshot.framework} --share-url <https-url>"
            ),
            "#CyberHuaTuo #SoulRing #AIAgents",
            "```",
            "",
            "Rule: this visual binds only current real CyberHuaTuo contribution data; it does not invent ranks, downloads, retention, referrals, or rewards.",
        ]
    )
