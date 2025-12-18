#!/usr/bin/env python3
import socket
import struct
import argparse

def send_artnet(ip: str, port: int, universe: int, value: int = 255):
    """Send Art-Net packet with all channels set to given value."""
    
    # Art-Net header
    header = b'Art-Net\x00'
    opcode = struct.pack('<H', 0x5000)  # ArtDMX opcode
    version = struct.pack('>H', 14)     # Protocol version 14
    sequence = struct.pack('B', 0)      # Sequence (0 = disabled)
    physical = struct.pack('B', 0)      # Physical port
    universe_bytes = struct.pack('<H', universe)  # Universe (little-endian)
    length = struct.pack('>H', 512)     # DMX length (big-endian)
    
    # DMX data - all 512 channels
    dmx_data = bytes([value] * 512)
    
    # Build packet
    packet = header + opcode + version + sequence + physical + universe_bytes + length + dmx_data
    
    # Send via UDP
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.sendto(packet, (ip, port))
    sock.close()
    
    print(f"Sent Art-Net to {ip}:{port}, universe {universe}, all channels = {value}")

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Send Art-Net DMX data')
    parser.add_argument('--ip', required=True, help='Target IP address')
    parser.add_argument('--port', type=int, default=6454, help='Art-Net port (default: 6454)')
    parser.add_argument('--universe', type=int, default=0, help='DMX universe (default: 0)')
    parser.add_argument('--value', type=int, default=255, help='Channel value 0-255 (default: 255)')
    
    args = parser.parse_args()
    send_artnet(args.ip, args.port, args.universe, args.value)