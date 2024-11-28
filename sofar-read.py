#!/usr/bin/python3

import socket
import binascii
import libscrc
import configparser
import argparse

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

def create_read_frame(inverter_sn, register, num_registers=1, verbose=False):
    """Create the Modbus frame for reading registers"""
    start = binascii.unhexlify('A5')
    length = binascii.unhexlify('1700')
    controlcode = binascii.unhexlify('1045')
    serial = binascii.unhexlify('0000')
    datafield = binascii.unhexlify('020000000000000000000000000000')

    # Convert register to hex format
    pos_ini = hex(register)[2:].zfill(4)
    pos_fin = hex(num_registers)[2:].zfill(4)
    businessfield = binascii.unhexlify('0003' + pos_ini + pos_fin)
    
    if verbose:
        print(f'Modbus request: 0103 {pos_ini} {pos_fin}')
    
    crc = binascii.unhexlify(str(padhex(hex(libscrc.modbus(businessfield)))[4:6]) + 
                            str(padhex(hex(libscrc.modbus(businessfield)))[2:4]))
    checksum = binascii.unhexlify('00')
    endCode = binascii.unhexlify('15')

    # Convert serial number to correct byte order
    inverter_sn2 = bytearray.fromhex(hex(inverter_sn)[8:10] + 
                                    hex(inverter_sn)[6:8] + 
                                    hex(inverter_sn)[4:6] + 
                                    hex(inverter_sn)[2:4])
    
    frame = bytearray(start + length + controlcode + serial + inverter_sn2 + 
                     datafield + businessfield + crc + checksum + endCode)

    # Calculate checksum
    checksum = 0
    frame_bytes = bytearray(frame)
    for i in range(1, len(frame_bytes) - 2, 1):
        checksum += frame_bytes[i] & 255
    frame_bytes[len(frame_bytes) - 2] = int((checksum & 255))

    if verbose:
        print(f"Frame to send: {frame_bytes.hex()}")

    return frame_bytes

def query_register(ip, port, frame, verbose=False):
    """Query inverter register"""
    try:
        clientSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        clientSocket.settimeout(15)
        clientSocket.connect((ip, port))
        
        if verbose:
            print(f"Connecting to {ip}:{port}")
        
        clientSocket.sendall(frame)
        data = clientSocket.recv(1024)
        
        if not data:
            print("No data received")
            return None

        if verbose:
            print("Raw data received:", data.hex())

        clientSocket.close()
        return data

    except socket.error as e:
        print(f"Socket error: {e}")
        return None
    except Exception as e:
        print(f"Error: {e}")
        return None

def process_response(data, verbose=False):
    """Process response from inverter"""
    if not data:
        return None
    
    # Extract the register value from the response
    # The register value is located at position 56-60 in the hex response
    response = str(''.join(hex(ord(chr(x)))[2:].zfill(2) for x in bytearray(data)))
    register_value = response[56:60]
    
    if verbose:
        print(f"Register value (hex): {register_value}")
    
    # Convert hex to decimal
    try:
        decimal_value = int(register_value, 16)
        return decimal_value
    except ValueError:
        print("Error converting response to decimal")
        return None

def main():
    parser = argparse.ArgumentParser(description="Read a specific register from Sofar inverter.")
    parser.add_argument("--register", type=lambda x: int(x, 0), required=True,
                      help="Register to read (in hex, e.g., 0x1062)")
    parser.add_argument("--verbose", action="store_true",
                      help="Enable verbose output")
    args = parser.parse_args()

    # Load configuration
    config = load_config()
    
    # Create read frame
    frame = create_read_frame(config['inverter_sn'], args.register, verbose=args.verbose)
    
    # Send the frame and get response
    response = query_register(config['inverter_ip'], config['inverter_port'], 
                            frame, args.verbose)
    
    if response:
        value = process_response(response, args.verbose)
        if value is not None:
            print(f"Register {hex(args.register)} value: {value} (0x{value:04x})")
    else:
        print("Failed to read from inverter")

if __name__ == "__main__":
    main()
