#!/usr/bin/python3

import socket
import binascii
import libscrc
import configparser
import argparse
import time

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
    """Create standard Modbus RTU frame for writing a single register"""
    frame = bytearray()
    
    # Slave address
    frame.append(0x01)
    
    # Function code (16 = 0x10 for writing multiple registers)
    frame.append(0x10)
    
    # Register address (high byte, low byte)
    frame.extend(register.to_bytes(2, byteorder='big'))
    
    # Number of registers to write (1)
    frame.extend((1).to_bytes(2, byteorder='big'))
    
    # Byte count (2 bytes per register)
    frame.append(2)
    
    # Value to write
    frame.extend(value.to_bytes(2, byteorder='big'))
    
    # Calculate CRC
    crc = libscrc.modbus(frame)
    frame.extend(crc.to_bytes(2, byteorder='little'))  # Modbus uses little-endian CRC
    
    if verbose:
        print(f'Modbus write request: Register {hex(register)} = {value}')
        print(f'Frame to send: {frame.hex()}')
    
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
        
        # Check if response is valid (should be 8 bytes for a write response)
        if len(data) == 8:
            response_reg = int.from_bytes(data[2:4], byteorder='big')
            if verbose:
                print(f"Write confirmed for register {hex(response_reg)}")
            return data
        return None

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
    
    # Create standard Modbus frame
    write_frame = create_write_frame(args.register, args.value, args.verbose)
    
    # Send the frame
    response = send_frame(config['inverter_ip'], config['inverter_port'], 
                         write_frame, args.verbose)
    
    if response:
        print(f"\nWrite command confirmed. Please verify the change by reading register {hex(args.register)}")
    else:
        print("\nWrite command failed")

if __name__ == "__main__":
    main()
