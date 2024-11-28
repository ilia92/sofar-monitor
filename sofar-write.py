#!/usr/bin/python3

import socket
import binascii
import libscrc
import configparser
import argparse
import time

def padhex(s):
    return '0x' + s[2:].zfill(4)

def hex_zfill(intval):
    hexvalue = hex(intval)
    return '0x' + str(hexvalue)[2:].zfill(4)

def load_config(config_path='./config.cfg'):
    """Load configuration from file"""
    configParser = configparser.RawConfigParser()
    configParser.read(config_path)
    
    return {
        'inverter_ip': configParser.get('SofarInverter', 'inverter_ip'),
        'inverter_port': int(configParser.get('SofarInverter', 'inverter_port')),
        'inverter_sn': int(configParser.get('SofarInverter', 'inverter_sn')),
        'verbose': configParser.get('SofarInverter', 'verbose')
    }

def create_write_frame(register, value, verbose=False):
    """Create Modbus frame for writing according to Sofar HYD protocol"""
    # Frame structure according to HYD protocol
    frame = bytearray.fromhex('88 13 10')  # Start + length + function code
    
    # Convert register to hex and add to frame
    reg_hex = hex(register)[2:].zfill(4)
    frame.extend(bytearray.fromhex(reg_hex))
    
    # Add fixed length of 1
    frame.extend(bytearray.fromhex('0001'))
    
    # Convert value to hex and add to frame
    value_hex = hex(value)[2:].zfill(4)
    frame.extend(bytearray.fromhex(value_hex))
    
    # Add the standard trailer for HYD protocol
    frame.extend(bytearray.fromhex('005509C40A5A0014012C012CFFFFFFFF00000000000000000000000000000000'))
    
    # Calculate CRC16
    crc = libscrc.modbus(frame[2:])  # Calculate CRC from function code onwards
    frame.extend(bytearray.fromhex(f'{crc:04x}'))
    
    if verbose:
        print(f"Write request: Register {hex(register)} = {value} ({value_hex})")
        print(f"Frame to send: {frame.hex()}")
    
    return frame

def send_frame(ip, port, frame, verbose=False):
    """Send a frame to the inverter and get response"""
    try:
        clientSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        clientSocket.settimeout(15)
        clientSocket.connect((ip, port))
        
        if verbose:
            print(f"Sending to {ip}:{port}")
        
        clientSocket.sendall(frame)
        time.sleep(0.5)
        
        data = clientSocket.recv(1024)
        
        if not data:
            print("No response received")
            return None

        if verbose:
            print("Response received:", data.hex())

        clientSocket.close()
        return data

    except Exception as e:
        print(f"Error: {e}")
        return None

def main():
    parser = argparse.ArgumentParser(description="Send write commands to Sofar HYD inverter.")
    parser.add_argument("--register", type=lambda x: int(x, 0), required=True,
                      help="Register to write to (in hex, e.g., 0x800)")
    parser.add_argument("--value", type=int, required=True,
                      help="Value to write to the register")
    parser.add_argument("--verbose", action="store_true",
                      help="Enable verbose output")
    args = parser.parse_args()

    config = load_config()
    
    print(f"Writing value {args.value} to register {hex(args.register)}...")
    write_frame = create_write_frame(args.register, args.value, args.verbose)
    response = send_frame(config['inverter_ip'], config['inverter_port'], 
                         write_frame, args.verbose)
    
    if response:
        print(f"\nWrite command sent. Please verify the change by reading register {hex(args.register)}")
    else:
        print("\nWrite command failed")

if __name__ == "__main__":
    main()
