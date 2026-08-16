"""TIFF-format EXIF byte builder for controlled test fixtures.

Builds a minimal EXIF block (with optional GPSInfo IFD) entirely from bytes, so
tests can inject exact, known metadata values (including values Pillow's public
API cannot write, such as a nested GPS IFD).
"""

import struct
from typing import cast


def _ascii(value: str) -> bytes:
    return value.encode("ascii") + b"\x00"


def _short(value: int) -> bytes:
    return struct.pack("<H", value)


def _long(value: int) -> bytes:
    return struct.pack("<I", value)


def _rational(num: int, den: int) -> bytes:
    return struct.pack("<II", num, den)


# TIFF field types.
_ASCII = 2
_SHORT = 3
_LONG = 4
_RATIONAL = 5


def _build_ifd(
    entries: list[tuple[int, int, list[bytes]]], *, ifd_offset: int
) -> tuple[bytes, bytes]:
    """Return (ifd_block, data_block) for one IFD.

    ``entries``: (tag, type, value_payloads) where each payload is the raw packed
    value (for ASCII: NUL-terminated string; for RATIONAL: 8 bytes; etc.).
    """
    block = bytearray(struct.pack("<H", len(entries)))
    data = bytearray()

    def aligned(extra: bytes) -> int:
        data.extend(extra)
        while len(data) % 4:
            data.append(0)
        return len(data)

    base = ifd_offset + 2 + 12 * len(entries) + 4
    for tag, typ, values in entries:
        count = sum(len(v) for v in values) if typ == _ASCII else len(values)
        payload = b"".join(values)
        size = len(payload)
        if size <= 4:
            inline = payload.ljust(4, b"\x00")
            block.extend(struct.pack("<HHI", tag, typ, count))
            block.extend(inline)
        else:
            offset = base + len(data)
            block.extend(struct.pack("<HHII", tag, typ, count, offset))
            aligned(payload)

    block.extend(struct.pack("<I", 0))
    return bytes(block), bytes(data)


def build_exif_bytes(
    *,
    make: str | None = None,
    model: str | None = None,
    software: str | None = None,
    orientation: int | None = None,
    date_time: str | None = None,
    date_time_original: str | None = None,
    iso: int | None = None,
    gps: dict[str, object] | None = None,
) -> bytes:
    """Return a complete EXIF block prefixed with the ``Exif\\0\\0`` marker.

    ``gps`` accepts keys: lat_ref (str), lat (tuple[(num, den), ...]),
    lon_ref (str), lon (tuple[(num, den), ...]), altitude ((num, den)),
    date_stamp (str).
    """
    ifd0: list[tuple[int, int, list[bytes]]] = []
    if make is not None:
        ifd0.append((0x010F, _ASCII, [_ascii(make)]))
    if model is not None:
        ifd0.append((0x0110, _ASCII, [_ascii(model)]))
    if software is not None:
        ifd0.append((0x0131, _ASCII, [_ascii(software)]))
    if orientation is not None:
        ifd0.append((0x0112, _SHORT, [_short(orientation)]))
    if date_time is not None:
        ifd0.append((0x0132, _ASCII, [_ascii(date_time)]))
    if date_time_original is not None:
        ifd0.append((0x9003, _ASCII, [_ascii(date_time_original)]))
    if iso is not None:
        ifd0.append((0x8827, _SHORT, [_short(iso)]))

    gps_entries: list[tuple[int, int, list[bytes]]] = []
    if gps:
        if "lat_ref" in gps:
            gps_entries.append((0x0001, _ASCII, [_ascii(str(gps["lat_ref"]))]))
        if "lat" in gps:
            lat = cast(list[tuple[int, int]], gps["lat"])
            gps_entries.append((0x0002, _RATIONAL, [_rational(*pair) for pair in lat]))
        if "lon_ref" in gps:
            gps_entries.append((0x0003, _ASCII, [_ascii(str(gps["lon_ref"]))]))
        if "lon" in gps:
            lon = cast(list[tuple[int, int]], gps["lon"])
            gps_entries.append((0x0004, _RATIONAL, [_rational(*pair) for pair in lon]))
        if "altitude" in gps:
            num, den = cast(tuple[int, int], gps["altitude"])
            gps_entries.append((0x0006, _RATIONAL, [_rational(num, den)]))
        if "date_stamp" in gps:
            gps_entries.append((0x001D, _ASCII, [_ascii(str(gps["date_stamp"]))]))

    def build_ifd0(gps_offset: int | None) -> tuple[bytes, bytes]:
        entries = list(ifd0)
        if gps_offset is not None:
            entries.append((0x8825, _LONG, [_long(gps_offset)]))
        return _build_ifd(entries, ifd_offset=8)

    gps_ifd_offset: int | None = None
    if gps_entries:
        gps_ifd_offset = 8 + (2 + 12 * (len(ifd0) + 1) + 4) + len(build_ifd0(0)[1])
    ifd0_block, ifd0_data = build_ifd0(gps_ifd_offset)
    if gps_entries:
        assert gps_ifd_offset is not None
        gps_block, gps_data = _build_ifd(gps_entries, ifd_offset=gps_ifd_offset)
    else:
        gps_block, gps_data = b"", b""

    header = b"II" + struct.pack("<HI", 42, 8)
    return b"Exif\x00\x00" + header + ifd0_block + ifd0_data + gps_block + gps_data
