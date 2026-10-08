#!/usr/bin/env python3
"""SEGGER SystemView <-> ST-Link koprusu.

SystemView canli kaydi icin normalde J-Link ister: J-Link, hedef calisirken
RAM'deki RTT tamponunu (_SEGGER_RTT) okur. Bu betik ayni isi ST-Link ile
pyOCD uzerinden yapar ve veriyi SystemView'in "IP Recorder" arayuzune
(TCP 19111) sunar:

    STM32 (RTT "SysView" kanali) --SWD/ST-Link--> bu betik --TCP:19111--> SystemView

IP Recorder protokolu (SEGGER_SYSVIEW_COMM_IP_embOS_emNet.c ile ayni):
  1. SystemView 32 baytlik "hello" gonderir, hedef 32 baytlik
     "SEGGER SystemView Vx.yy.zz" ile cevap verir.
  2. PC -> hedef: [uzunluk (1 bayt)][komut baytlari] cerceveleri
     -> RTT "SysView" down tamponuna yazilir (Start/Stop/...).
  3. Hedef -> PC: RTT "SysView" up tamponundaki ham olay akisi.

Kullanim:
    tools/.venv/Scripts/python tools/sysview_stlink.py
    SystemView: Target > Recorder Configuration > IP > 127.0.0.1 : 19111
"""

from __future__ import annotations

import argparse
import logging
import select
import socket
import struct
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_ELF = ROOT / "build" / "Debug" / "Hafta-01.elf"

# STM32L476RG: SRAM1 96 KB @ 0x20000000 (_SEGGER_RTT burada)
RAM_START = 0x20000000
RAM_SIZE = 96 * 1024

RTT_ID = b"SEGGER RTT\0"
RTT_HDR_SIZE = 24            # acID[16] + MaxNumUpBuffers + MaxNumDownBuffers
RTT_DESC_SIZE = 24           # sName, pBuffer, SizeOfBuffer, WrOff, RdOff, Flags
SYSVIEW_CHANNEL_NAME = "SysView"

HELLO_SIZE = 32
# Firmware'deki SEGGER_SYSVIEW_MAJOR/MINOR/REV ile ayni (3.32.00)
TARGET_HELLO = b"SEGGER SystemView V3.32.00".ljust(HELLO_SIZE, b"\0")

SYSVIEW_CMD_STOP = 2

log = logging.getLogger("sysview")


class RttError(Exception):
    pass


class RttChannel:
    """Hedef RAM'indeki tek bir RTT tampon tanimlayicisi."""

    def __init__(self, target, desc_addr: int):
        self.t = target
        self.desc = desc_addr
        _name, self.buf, self.size, _wr, _rd, _flags = struct.unpack(
            "<6I", bytes(target.read_memory_block8(desc_addr, RTT_DESC_SIZE)))
        if self.size == 0 or not (RAM_START <= self.buf < RAM_START + RAM_SIZE):
            raise RttError(f"gecersiz RTT tamponu @0x{desc_addr:08X}")

    def _offsets(self) -> tuple[int, int]:
        wr, rd = struct.unpack("<2I", bytes(self.t.read_memory_block8(self.desc + 12, 8)))
        if wr >= self.size or rd >= self.size:
            raise RttError("RTT ofsetleri bozuk (hedef resetlendi mi?)")
        return wr, rd

    # ---- up: hedef -> PC ----
    def read(self) -> bytes:
        wr, rd = self._offsets()
        self.peak_fill = max(getattr(self, "peak_fill", 0), (wr - rd) % self.size)
        if wr == rd:
            return b""
        if wr > rd:
            data = bytes(self.t.read_memory_block8(self.buf + rd, wr - rd))
        else:
            data = bytes(self.t.read_memory_block8(self.buf + rd, self.size - rd))
            if wr:
                data += bytes(self.t.read_memory_block8(self.buf, wr))
        self.t.write32(self.desc + 16, wr)          # RdOff
        return data

    def discard(self) -> None:
        wr, _rd = self._offsets()
        self.t.write32(self.desc + 16, wr)

    # ---- down: PC -> hedef ----
    def write(self, data: bytes) -> int:
        wr, rd = self._offsets()
        free = (rd - wr - 1) % self.size
        n = min(free, len(data))
        if n == 0:
            return 0
        first = min(n, self.size - wr)
        self.t.write_memory_block8(self.buf + wr, list(data[:first]))
        if n > first:
            self.t.write_memory_block8(self.buf, list(data[first:n]))
        self.t.write32(self.desc + 12, (wr + n) % self.size)   # WrOff
        return n


class Rtt:
    def __init__(self, target, elf: Path | None):
        self.t = target
        self.elf = elf
        self.cb = None
        self.up: RttChannel | None = None
        self.down: RttChannel | None = None

    def _elf_address(self) -> int | None:
        if not self.elf or not self.elf.is_file():
            return None
        from elftools.elf.elffile import ELFFile
        with self.elf.open("rb") as f:
            symtab = ELFFile(f).get_section_by_name(".symtab")
            syms = symtab.get_symbol_by_name("_SEGGER_RTT") if symtab else None
        return syms[0]["st_value"] if syms else None

    def _has_id(self, addr: int) -> bool:
        return bytes(self.t.read_memory_block8(addr, len(RTT_ID))) == RTT_ID

    def _scan(self) -> int | None:
        chunk = 4096
        prev_tail = b""
        for base in range(RAM_START, RAM_START + RAM_SIZE, chunk):
            data = prev_tail + bytes(self.t.read_memory_block8(base, chunk))
            i = data.find(RTT_ID)
            if i >= 0:
                return base - len(prev_tail) + i
            prev_tail = data[-(len(RTT_ID) - 1):]
        return None

    def _name(self, ptr: int) -> str:
        if not ptr:
            return ""
        raw = bytes(self.t.read_memory_block8(ptr, 16))
        return raw.split(b"\0", 1)[0].decode("ascii", "replace")

    def attach(self) -> None:
        addr = self._elf_address()
        if addr is not None and self._has_id(addr):
            log.info("RTT kontrol blogu (ELF): 0x%08X", addr)
        else:
            if addr is not None:
                log.info("ELF adresinde (0x%08X) RTT yok, RAM taraniyor...", addr)
            addr = self._scan()
            if addr is None:
                raise RttError("RAM'de 'SEGGER RTT' bulunamadi (firmware SystemView'li mi, calisiyor mu?)")
            log.info("RTT kontrol blogu (tarama): 0x%08X", addr)

        n_up, n_down = struct.unpack("<2i", bytes(self.t.read_memory_block8(addr + 16, 8)))
        if not (0 < n_up <= 16 and 0 < n_down <= 16):
            raise RttError(f"RTT basligi bozuk (up={n_up}, down={n_down})")
        up_base = addr + RTT_HDR_SIZE
        down_base = up_base + n_up * RTT_DESC_SIZE

        def find(base: int, count: int) -> int | None:
            for i in range(count):
                name_ptr = self.t.read32(base + i * RTT_DESC_SIZE)
                if self._name(name_ptr) == SYSVIEW_CHANNEL_NAME:
                    return i
            return None

        iu, idn = find(up_base, n_up), find(down_base, n_down)
        if iu is None or idn is None:
            raise RttError("'SysView' RTT kanali yok (SEGGER_SYSVIEW_Conf() cagrildi mi?)")
        self.cb = addr
        self.up = RttChannel(self.t, up_base + iu * RTT_DESC_SIZE)
        self.down = RttChannel(self.t, down_base + idn * RTT_DESC_SIZE)
        log.info("SysView kanali: up #%d (%d B), down #%d (%d B)",
                 iu, self.up.size, idn, self.down.size)

    def still_valid(self) -> bool:
        try:
            return self.cb is not None and self._has_id(self.cb)
        except Exception:
            return False


def recv_exact(sock: socket.socket, n: int, timeout: float) -> bytes:
    sock.settimeout(timeout)
    buf = b""
    while len(buf) < n:
        part = sock.recv(n - len(buf))
        if not part:
            raise ConnectionError("SystemView baglantiyi kapatti")
        buf += part
    sock.settimeout(None)
    return buf


def serve_client(conn: socket.socket, rtt: Rtt, poll_s: float) -> None:
    hello = recv_exact(conn, HELLO_SIZE, timeout=5.0)
    log.info("SystemView hello: %r", hello.rstrip(b"\0").decode("ascii", "replace"))
    conn.sendall(TARGET_HELLO)

    rtt.up.discard()                    # onceki oturumdan kalan eski veri
    conn.setblocking(False)
    rx = b""                            # PC'den gelen, cozulmemis cerceveler
    pending_down = b""                  # down tamponuna sigmayan komutlar
    total = 0
    t_stat = time.monotonic()
    bytes_stat = 0

    try:
        while True:
            readable, _, _ = select.select([conn], [], [], 0)
            if readable:
                part = conn.recv(256)
                if not part:
                    log.info("SystemView kaydi durdurdu / baglanti kapandi.")
                    return
                rx += part
                # [len][payload] cercevelerini ac
                while rx and len(rx) >= 1 + rx[0]:
                    n = rx[0]
                    pending_down += rx[1:1 + n]
                    rx = rx[1 + n:]

            if pending_down:
                pending_down = pending_down[rtt.down.write(pending_down):]

            data = rtt.up.read()
            if data:
                conn.setblocking(True)
                conn.sendall(data)
                conn.setblocking(False)
                total += len(data)
                bytes_stat += len(data)
            else:
                time.sleep(poll_s)

            now = time.monotonic()
            if now - t_stat >= 5.0:
                # Doluluk %100'e yaklasirsa hedef olay atar (SystemView'da "Overflow")
                log.info("  %.1f KB/s, toplam %.1f KB, tampon tepe dolulugu %%%d",
                         bytes_stat / (now - t_stat) / 1024, total / 1024,
                         100 * rtt.up.peak_fill // rtt.up.size)
                t_stat, bytes_stat, rtt.up.peak_fill = now, 0, 0
    finally:
        try:                            # hedef kaydi bossa yere surdurmesin
            rtt.down.write(bytes([SYSVIEW_CMD_STOP]))
        except Exception:
            pass


def open_session(args):
    from pyocd.core.helpers import ConnectHelper
    options = {
        "connect_mode": "attach",       # hedefi durdurma / resetleme
        "frequency": args.freq,
        "target_override": args.target,
        "resume_on_disconnect": True,
    }
    session = ConnectHelper.session_with_chosen_probe(
        unique_id=args.probe, blocking=False, options=options)
    if session is None:
        return None
    session.open()
    return session


def main() -> int:
    ap = argparse.ArgumentParser(description="SystemView IP Recorder <-> ST-Link (pyOCD) koprusu")
    ap.add_argument("--elf", type=Path, default=DEFAULT_ELF, help="_SEGGER_RTT adresi icin ELF")
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=19111)
    ap.add_argument("--probe", default=None, help="ST-Link seri no (birden fazla probe varsa)")
    ap.add_argument("--target", default="stm32l475xg",
                    help="pyOCD hedefi (L476RG ile ayni bellek haritasi)")
    ap.add_argument("--freq", type=int, default=4_000_000, help="SWD saati (Hz)")
    ap.add_argument("--poll-ms", type=float, default=1.0, help="veri yokken bekleme")
    ap.add_argument("-v", "--verbose", action="store_true")
    args = ap.parse_args()

    logging.basicConfig(level=logging.DEBUG if args.verbose else logging.INFO,
                        format="%(asctime)s %(message)s", datefmt="%H:%M:%S")
    for noisy in ("pyocd", "pyocd.board", "pyocd.target", "pyocd.coresight"):
        logging.getLogger(noisy).setLevel(logging.WARNING)

    srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    try:
        srv.bind((args.host, args.port))
    except OSError as e:
        log.error("%s:%d dinlenemiyor (%s). Kopru zaten calisiyor olabilir.", args.host, args.port, e)
        return 1
    srv.listen(1)

    session = None
    try:
        while True:
            # --- ST-Link + RTT ---
            if session is None:
                session = open_session(args)
                if session is None:
                    log.warning("ST-Link bulunamadi; 2 sn sonra tekrar (kart takili mi, debug oturumu acik mi?)")
                    time.sleep(2)
                    continue
                log.info("ST-Link baglandi: %s", session.probe.unique_id)
            rtt = Rtt(session.board.target, args.elf)
            try:
                rtt.attach()
            except RttError as e:
                log.warning("%s; 2 sn sonra tekrar", e)
                time.sleep(2)
                continue

            # --- SystemView ---
            log.info("SystemView bekleniyor: Target > Start Recording (IP %s:%d)", args.host, args.port)
            srv.settimeout(1.0)
            conn = None
            while conn is None:
                try:
                    conn, peer = srv.accept()
                except socket.timeout:
                    if not rtt.still_valid():
                        break
            if conn is None:
                log.warning("Hedef resetlendi / yeniden yuklendi; RTT tekrar araniyor")
                continue
            conn.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
            log.info("SystemView baglandi: %s:%d", *peer)
            try:
                serve_client(conn, rtt, args.poll_ms / 1000.0)
            except (ConnectionError, OSError, socket.timeout) as e:
                log.info("Baglanti sonlandi: %s", e)
            except RttError as e:
                log.warning("%s", e)
            except Exception as e:      # ST-Link USB hatasi vb.
                log.error("ST-Link hatasi: %s; yeniden baglaniliyor", e)
                try:
                    session.close()
                except Exception:
                    pass
                session = None
            finally:
                conn.close()
    except KeyboardInterrupt:
        log.info("Cikiliyor.")
    finally:
        srv.close()
        if session is not None:
            session.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
