#!/usr/bin/env python3
"""Find Samsung TVs on the local network and check that they can be reached.

Run this on a computer connected to the same network as the TV:

    python3 find_tv.py              # discover automatically
    python3 find_tv.py --ip 192.168.1.50   # check one known address

Needs only the Python standard library. It only reads information from the
TV; it does not send any remote-control commands.
"""

import argparse
import ipaddress
import json
import re
import socket
import sys
import urllib.request
from concurrent.futures import ThreadPoolExecutor

SSDP_ADDR = ("239.255.255.250", 1900)
INFO_PORT = 8001  # Samsung Tizen TVs (2016+) serve device info here
REMOTE_PORTS = {8002: "remote control (secure websocket)", 8001: "remote control (websocket)"}


def ssdp_discover(timeout=3.0):
    """Return the set of IP addresses that answered an SSDP search."""
    request = "\r\n".join([
        "M-SEARCH * HTTP/1.1",
        "HOST: 239.255.255.250:1900",
        'MAN: "ssdp:discover"',
        "MX: 2",
        "ST: ssdp:all",
        "", "",
    ]).encode()
    found = {}
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.settimeout(timeout)
    try:
        sock.sendto(request, SSDP_ADDR)
        sock.sendto(request, SSDP_ADDR)  # UDP is lossy; ask twice
        while True:
            try:
                data, (ip, _) = sock.recvfrom(65507)
            except socket.timeout:
                break
            text = data.decode("utf-8", "replace")
            found[ip] = found.get(ip, False) or bool(re.search("samsung", text, re.I))
    except OSError as exc:
        print(f"  SSDP search failed: {exc}")
    finally:
        sock.close()
    return found


def local_subnet():
    """Guess this computer's /24 network from its outbound address."""
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        sock.connect(("10.255.255.255", 1))  # no packet is sent
        ip = sock.getsockname()[0]
    except OSError:
        return None
    finally:
        sock.close()
    if ip.startswith("127."):
        return None
    return ipaddress.ip_network(f"{ip}/24", strict=False)


def port_open(ip, port, timeout=0.5):
    try:
        with socket.create_connection((str(ip), port), timeout=timeout):
            return True
    except OSError:
        return False


def scan_subnet(network):
    hosts = [str(h) for h in network.hosts()]
    with ThreadPoolExecutor(max_workers=64) as pool:
        hits = pool.map(lambda h: port_open(h, INFO_PORT), hosts)
    return [h for h, ok in zip(hosts, hits) if ok]


def fetch_info(ip, port=INFO_PORT, timeout=3.0):
    """Return the TV's device-info dict, or None if it is not a Samsung TV."""
    try:
        with urllib.request.urlopen(f"http://{ip}:{port}/api/v2/", timeout=timeout) as resp:
            info = json.load(resp)
    except (OSError, ValueError):
        return None
    return info if isinstance(info, dict) and "device" in info else None


def report(ip, info):
    dev = info.get("device", {})
    print(f"\nSamsung TV found at {ip}")
    for label, key in [
        ("Name", "name"), ("Model", "modelName"), ("OS", "OS"),
        ("Power state", "PowerState"), ("Network", "networkType"),
        ("MAC address", "wifiMac"), ("Needs pairing token", "TokenAuthSupport"),
        ("Frame TV", "FrameTVSupport"),
    ]:
        if key in dev:
            print(f"  {label + ':':21}{dev[key]}")
    for port, label in REMOTE_PORTS.items():
        state = "open" if port_open(ip, port, 1.5) else "closed"
        print(f"  Port {port} {state:7}{label}")


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--ip", help="check this address instead of searching")
    args = parser.parse_args()

    if args.ip:
        candidates = [args.ip]
    else:
        print("Searching the network (SSDP)...")
        answered = ssdp_discover()
        # Samsung devices first, then everything else that answered.
        candidates = sorted(answered, key=lambda ip: not answered[ip])
        print(f"  {len(candidates)} device(s) answered.")

    tvs = [(ip, info) for ip in candidates if (info := fetch_info(ip))]

    if not tvs and not args.ip:
        network = local_subnet()
        if network:
            print(f"No TV found that way; scanning {network} for port {INFO_PORT}...")
            tvs = [(ip, info) for ip in scan_subnet(network) if (info := fetch_info(ip))]

    if not tvs:
        print("\nNo Samsung TV found. Things to check:")
        print("  - The TV is switched on (not just in standby) and on the same network.")
        print("  - This computer is not on a guest Wi-Fi or VPN that isolates devices.")
        print("  - Find the TV's address under Settings > General > Network > Network Status")
        print("    and run:  python3 find_tv.py --ip <address>")
        return 1

    for ip, info in tvs:
        report(ip, info)
    return 0


if __name__ == "__main__":
    sys.exit(main())
