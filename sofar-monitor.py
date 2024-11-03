#!/usr/bin/python3

import sys
import socket
import binascii
import re
import libscrc
import json
import os
import configparser
import argparse
from datetime import datetime

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

def create_frame(inverter_sn, start_register, num_registers, verbose=False):
    """Create the Modbus frame for communication"""
    start = binascii.unhexlify('A5')
    length = binascii.unhexlify('1700')
    controlcode = binascii.unhexlify('1045')
    serial = binascii.unhexlify('0000')
    datafield = binascii.unhexlify('020000000000000000000000000000')

    pos_ini = str(hex_zfill(start_register)[2:])
    pos_fin = str(hex_zfill(num_registers)[2:])
    businessfield = binascii.unhexlify('0003' + pos_ini + pos_fin)
    
    if verbose:
        print(f'Modbus request: 0103 {pos_ini} {pos_fin} {str(padhex(hex(libscrc.modbus(businessfield)))[4:6])}{str(padhex(hex(libscrc.modbus(businessfield)))[2:4])}')
    
    crc = binascii.unhexlify(str(padhex(hex(libscrc.modbus(businessfield)))[4:6]) + str(padhex(hex(libscrc.modbus(businessfield)))[2:4]))
    checksum = binascii.unhexlify('00')
    endCode = binascii.unhexlify('15')

    inverter_sn2 = bytearray.fromhex(hex(inverter_sn)[8:10] + hex(inverter_sn)[6:8] + hex(inverter_sn)[4:6] + hex(inverter_sn)[2:4])
    frame = bytearray(start + length + controlcode + serial + inverter_sn2 + datafield + businessfield + crc + checksum + endCode)

    checksum = 0
    frame_bytes = bytearray(frame)
    for i in range(1, len(frame_bytes) - 2, 1):
        checksum += frame_bytes[i] & 255
    frame_bytes[len(frame_bytes) - 2] = int((checksum & 255))

    if verbose:
        print(f"Frame to send: {frame_bytes.hex()}")

    return frame_bytes

def query_registers(ip, port, frame, verbose=False):
    """Query inverter registers"""
    try:
        clientSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        clientSocket.settimeout(15)
        clientSocket.connect((ip, port))
        
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

def process_response(data, start_register, num_registers, verbose=False):
    """Process response from inverter"""
    if not data:
        return {}
    
    response = str(''.join(hex(ord(chr(x)))[2:].zfill(2) for x in bytearray(data)))
    register_values = {}
    
    for i in range(num_registers + 1):
        p1 = 56 + (i * 4)
        p2 = 60 + (i * 4)
        responsereg = response[p1:p2]
        hexpos = str("0x") + str(hex(i+start_register)[2:].zfill(4)).upper()
        
        register_values[hexpos] = responsereg
        
        if verbose:
            print(f"Register: {hexpos} , value: hex:{str(responsereg)}")
    
    return register_values

def get_register(values, reg, scale=1.0, signed=False):
    """Get scaled register value"""
    try:
        if reg not in values:
            return None
        val = int(values[reg], 16)
        if signed and val > 32767:
            val -= 65536
        return val * scale
    except:
        return None

def get_32bit_register(values, high_reg, low_reg, scale=1.0):
    """Get 32-bit register value"""
    try:
        if high_reg not in values or low_reg not in values:
            return None
        high_val = int(values[high_reg], 16)
        low_val = int(values[low_reg], 16)
        val = (high_val << 16) + low_val
        return val * scale
    except:
        return None

def interpret_fault_codes(values):
    """Capture fault codes as both decimal integers and descriptions."""
    faults = []
    fault_definitions = {
        '0x0405': {
            0: "No error",
            1: "ID01 Grid Over Voltage Protection",
            2: "ID02 Grid Under Voltage Protection",
            4: "ID03 Grid Over Frequency Protection",
            8: "ID04 Grid Under Frequency Protection",
            16: "ID05 Leakage current fault",
            32: "ID06 High penetration error",
            64: "ID07 Low penetration error",
            128: "ID08 Islanding error",
            256: "ID09 Grid voltage transient overvoltage 1",
            512: "ID10 Grid voltage transient overvoltage 2",
            1024: "ID11 Grid line voltage error",
            2048: "ID12 Inverter voltage error",
            4096: "ID13 Anti-backflow overload",
        },
        '0x0406': {
            0: "No error",
            1: "ID17 Grid current sampling error",
            2: "ID18 Grid current DC component sampling error (AC side)",
            4: "ID19 Grid voltage sampling error (DC side)",
            8: "ID20 Grid voltage sampling error (AC side)",
            16: "ID21 Leakage current sampling error (DC side)",
            32: "ID22 Leakage current sampling error (AC side)",
            64: "ID23 Load voltage DC component sampling error",
            128: "ID24 DC input current sampling error",
            256: "ID25 DC component sampling error of grid current",
            512: "ID26 DC input branch current sampling error",
            4096: "ID29 Leakage current consistency error",
            8192: "ID30 Grid voltage consistency error",
            16384: "ID31 DCI consistency error",
        }
    }
    
    for reg, fault_map in fault_definitions.items():
        if reg in values:
            fault_value = int(values[reg], 16)
            for code, description in fault_map.items():
                if code != 0 and (fault_value & code):
                    faults.append({"code": code, "description": description})
                    
    return faults

def get_battery_metrics(values):
    """Get metrics for both batteries"""
    batteries = {}
    
    # Battery 1: 0x0604 - 0x060A
    # Battery 2: 0x060B - 0x0611
    for bat_num in range(2):
        base_addr = 0x0604 + (bat_num * 7)
        
        battery_data = {
            'voltage': get_register(values, f'0x{base_addr:04X}', 0.1),
            'current': get_register(values, f'0x{base_addr+1:04X}', 0.01, True),
            'power': get_register(values, f'0x{base_addr+2:04X}', 10, True),
            'temperature': get_register(values, f'0x{base_addr+3:04X}', 1, True),
            'soc': get_register(values, f'0x{base_addr+4:04X}', 1),
            'soh': get_register(values, f'0x{base_addr+5:04X}', 1),
            'cycles': get_register(values, f'0x{base_addr+6:04X}', 1),
        }
        
        if any(v is not None for v in battery_data.values()):
            batteries[f'battery_{bat_num + 1}'] = battery_data
    
    # Battery settings
    batteries['settings'] = {
        'dod': get_register(values, '0x104D', 1),
        'eod': get_register(values, '0x104E', 1),
        'eps_buffer': get_register(values, '0x1052', 1)
    }
    
    return batteries

def format_data(values):
    """Format all data into structured dictionary with fault codes as both decimals and descriptions."""
    status_map = {
        0: 'Waiting', 1: 'Checking', 2: 'Normal', 3: 'Fault',
        4: 'Permanent Fault', 5: 'Updating', 6: 'EPS Check',
        7: 'EPS Mode', 8: 'Self Test', 9: 'Idle'
    }

    def format_value(value, precision):
        return round(value, precision) if value is not None else None

    status_val = get_register(values, '0x0404')
    fault_descriptions = interpret_fault_codes(values) or []  # Ensure it's a list, even if empty

    return {
        'timestamp': datetime.now().isoformat(),
        'status': {
            'state': status_map.get(status_val) if status_val is not None else None,
            'state_decimal': int(status_val) if status_val is not None else None,
            'generation_time_minutes': int(get_register(values, '0x0426')),
            'ambient_temp': format_value(get_register(values, '0x0418'), 1),
            'module_temp': format_value(get_register(values, '0x0420'), 1),
            'heatsink_temp': format_value(get_register(values, '0x041A'), 1)
        },
        'faults': [fault['code'] for fault in fault_descriptions],  # List of just fault codes
        'pv1': {
            'voltage': format_value(get_register(values, '0x0584', 0.1), 1),
            'current': format_value(get_register(values, '0x0585', 0.01), 2),
            'power': format_value(get_register(values, '0x0586', 0.01), 2)  # back to kW
        },
        'pv2': {
            'voltage': format_value(get_register(values, '0x0587', 0.1), 1),
            'current': format_value(get_register(values, '0x0588', 0.01), 2),
            'power': format_value(get_register(values, '0x0589', 0.01), 2)  # back to kW
        },
        'grid': {
            'frequency': format_value(get_register(values, '0x0484', 0.01), 2),
            'voltage': {
                'phase_r': format_value(get_register(values, '0x048D', 0.1), 1),
                'phase_s': format_value(get_register(values, '0x0498', 0.1), 1),
                'phase_t': format_value(get_register(values, '0x04A3', 0.1), 1)
            },
            'generation': {
                'total': {
                    'active': format_value(get_register(values, '0x0485', 0.01, True), 2),  # back to kW
                    'reactive': format_value(get_register(values, '0x0486', 0.01, True), 2),
                    'apparent': format_value(get_register(values, '0x0487', 0.01, True), 2)
                },
                'phase_r': {
                    'current': format_value(get_register(values, '0x048E', 0.01), 2),
                    'active_power': format_value(get_register(values, '0x048F', 0.01, True), 2),  # back to kW
                    'reactive_power': format_value(get_register(values, '0x0490', 0.01, True), 2),
                    'power_factor': format_value(get_register(values, '0x0491', 0.001, True), 3)
                },
                'phase_s': {
                    'current': format_value(get_register(values, '0x0499', 0.01), 2),
                    'active_power': format_value(get_register(values, '0x049A', 0.01, True), 2),  # back to kW
                    'reactive_power': format_value(get_register(values, '0x049B', 0.01, True), 2),
                    'power_factor': format_value(get_register(values, '0x049C', 0.001, True), 3)
                },
                'phase_t': {
                    'current': format_value(get_register(values, '0x04A4', 0.01), 2),
                    'active_power': format_value(get_register(values, '0x04A5', 0.01, True), 2),  # back to kW
                    'reactive_power': format_value(get_register(values, '0x04A6', 0.01, True), 2),
                    'power_factor': format_value(get_register(values, '0x04A7', 0.001, True), 3)
                }
            },

            'pcc': {
                'total': {
                    'active': format_value(get_register(values, '0x0488', 0.01, True), 2),  # back to kW
                    'reactive': format_value(get_register(values, '0x0489', 0.01, True), 2),
                    'apparent': format_value(get_register(values, '0x048A', 0.01, True), 2)
                },
                'phase_r': {
                    'current': format_value(get_register(values, '0x0492', 0.01), 2),
                    'active_power': format_value(get_register(values, '0x0493', 0.01, True), 2),  # back to kW
                    'reactive_power': format_value(get_register(values, '0x0494', 0.01, True), 2),
                    'power_factor': format_value(get_register(values, '0x0495', 0.001, True), 3)
                },
                'phase_s': {
                    'current': format_value(get_register(values, '0x049D', 0.01), 2),
                    'active_power': format_value(get_register(values, '0x049E', 0.01, True), 2),  # back to kW
                    'reactive_power': format_value(get_register(values, '0x049F', 0.01, True), 2),
                    'power_factor': format_value(get_register(values, '0x04A0', 0.001, True), 3)
                },
                'phase_t': {
                    'current': format_value(get_register(values, '0x04A8', 0.01), 2),
                    'active_power': format_value(get_register(values, '0x04A9', 0.01, True), 2),  # back to kW
                    'reactive_power': format_value(get_register(values, '0x04AA', 0.01, True), 2),
                    'power_factor': format_value(get_register(values, '0x04AB', 0.001, True), 3)
                }
            }
        },
        'off_grid': {
            'frequency': format_value(get_register(values, '0x0507', 0.01), 2),
            'total': {
                'active': format_value(get_register(values, '0x0504', 0.01, True), 2),  # back to kW
                'reactive': format_value(get_register(values, '0x0505', 0.01, True), 2),
                'apparent': format_value(get_register(values, '0x0506', 0.01, True), 2)
            },
            'phase_r': {
                'voltage': format_value(get_register(values, '0x050A', 0.1), 1),
                'current': format_value(get_register(values, '0x050B', 0.01), 2),
                'active_power': format_value(get_register(values, '0x050C', 0.01, True), 2),  # back to kW
                'reactive_power': format_value(get_register(values, '0x050D', 0.01, True), 2),
                'apparent_power': format_value(get_register(values, '0x050E', 0.01, True), 2)
            },
            'phase_s': {
                'voltage': format_value(get_register(values, '0x0512', 0.1), 1),
                'current': format_value(get_register(values, '0x0513', 0.01), 2),
                'active_power': format_value(get_register(values, '0x0514', 0.01, True), 2),  # back to kW
                'reactive_power': format_value(get_register(values, '0x0515', 0.01, True), 2),
                'apparent_power': format_value(get_register(values, '0x0516', 0.01, True), 2)
            },
            'phase_t': {
                'voltage': format_value(get_register(values, '0x051A', 0.1), 1),
                'current': format_value(get_register(values, '0x051B', 0.01), 2),
                'active_power': format_value(get_register(values, '0x051C', 0.01, True), 2),  # back to kW
                'reactive_power': format_value(get_register(values, '0x051D', 0.01, True), 2),
                'apparent_power': format_value(get_register(values, '0x051E', 0.01, True), 2)
            }
        },
        'generation': {
            'daily': format_value(get_32bit_register(values, '0x0684', '0x0685', 0.01), 2),  # kWh values
            'total': format_value(get_32bit_register(values, '0x0686', '0x0687', 0.1), 1),  # kWh values
            'load_daily': format_value(get_32bit_register(values, '0x0688', '0x0689', 0.01), 2),  # kWh values
            'load_total': format_value(get_32bit_register(values, '0x068A', '0x068B', 0.1), 1),  # kWh values
            'bought_daily': format_value(get_32bit_register(values, '0x068C', '0x068D', 0.01), 2),  # kWh values
            'bought_total': format_value(get_32bit_register(values, '0x068E', '0x068F', 0.1), 1),  # kWh values
            'sold_daily': format_value(get_32bit_register(values, '0x0690', '0x0691', 0.01), 2),  # kWh values
            'sold_total': format_value(get_32bit_register(values, '0x0692', '0x0693', 0.1), 1),  # kWh values
            'battery_charge_daily': format_value(get_32bit_register(values, '0x0694', '0x0695', 0.01), 2),  # kWh values
            'battery_charge_total': format_value(get_32bit_register(values, '0x0696', '0x0697', 0.1), 1),  # kWh values
            'battery_discharge_daily': format_value(get_32bit_register(values, '0x0698', '0x0699', 0.01), 2),  # kWh values
            'battery_discharge_total': format_value(get_32bit_register(values, '0x069A', '0x069B', 0.1), 1)  # kWh values
        },
        'faults': interpret_fault_codes(values),
        'batteries': get_battery_metrics(values)
    }

def print_data(data):
    """Print formatted data to console"""
    print("\n=== Inverter Status ===")
    print(f"Status: {data['status']['state']}")
    if data['status']['generation_time_minutes']:
        minutes = data['status']['generation_time_minutes']
        hours = minutes // 60
        mins = minutes % 60
        print(f"Generation Time Today: {hours}h {mins}m")
    print(f"Ambient Temp: {data['status']['ambient_temp']}°C")
    print(f"Module Temp: {data['status']['module_temp']}°C")
    print(f"Heatsink Temp: {data['status']['heatsink_temp']}°C")

    if 'faults' in data:
        print("\n=== Fault Status ===")
        if data['faults']:
            print("Active Faults:")
            for fault in data['faults']:
                print(f"  - {fault}")
        else:
            print("No active faults")

    print("\n=== PV Input Values ===")
    pv1 = data['pv1']
    pv2 = data['pv2']
    if any(v is not None for v in pv1.values()):
        print("PV1:", end=" ")
        if pv1['voltage'] is not None:
            print(f"{pv1['voltage']:.1f}V", end=", ")
        if pv1['current'] is not None:
            print(f"{pv1['current']:.2f}A", end=", ")
        if pv1['power'] is not None:
            print(f"{pv1['power']:.2f}kW")
    
    if any(v is not None for v in pv2.values()):
        print("PV2:", end=" ")
        if pv2['voltage'] is not None:
            print(f"{pv2['voltage']:.1f}V", end=", ")
        if pv2['current'] is not None:
            print(f"{pv2['current']:.2f}A", end=", ")
        if pv2['power'] is not None:
            print(f"{pv2['power']:.2f}kW")

    print("\n=== Grid Values ===")
    grid = data['grid']
    if grid['frequency'] is not None:
        print(f"Grid Frequency: {grid['frequency']:.2f}Hz")


    print("\nGenerated Power:")
    gen = grid['generation']
    print("Total:", end=" ")
    if gen['total']['active'] is not None and gen['total']['reactive'] is not None:
        print(f"{gen['total']['active']:.2f}kW")
    else:
        print("No data")
    
    for phase in ['phase_r', 'phase_s', 'phase_t']:
        p = gen[phase]
        phase_letter = phase[-1].upper()
        voltage = grid['voltage'][f'phase_{phase[-1]}']
        print(f"Phase {phase_letter}: ", end="")
        if all(v is not None for v in [voltage, p['current'], p['active_power'], p['power_factor']]):
            print(f"{voltage:.1f}V, {p['current']:.2f}A, {p['active_power']:.2f}kW, PF: {p['power_factor']:.3f}")
        else:
            print("No data")

    print("\nGrid Exchange (PCC):")
    pcc = grid['pcc']
    print("Total:", end=" ")
    if pcc['total']['active'] is not None and pcc['total']['reactive'] is not None:
        print(f"{pcc['total']['active']:.2f}kW")
    else:
        print("No data")
    
    for phase in ['phase_r', 'phase_s', 'phase_t']:
        p = pcc[phase]
        phase_letter = phase[-1].upper()
        voltage = grid['voltage'][f'phase_{phase[-1]}']
        print(f"Phase {phase_letter}: ", end="")
        if all(v is not None for v in [voltage, p['current'], p['active_power'], p['power_factor']]):
            print(f"{voltage:.1f}V, {p['current']:.2f}A, {p['active_power']:.2f}kW, PF: {p['power_factor']:.3f}")
        else:
            print("No data")

    if 'off_grid' in data:
        print("\n=== Off-grid Values ===")
        off_grid = data['off_grid']

    # Frequency
    if off_grid['frequency'] is not None:
        print(f"Frequency: {off_grid['frequency']:.2f}Hz")

    # Total Power
    print("Total:", end=" ")
    if off_grid['total']['active'] is not None and off_grid['total']['reactive'] is not None:
        print(f"{off_grid['total']['active']:.2f}kW")
    else:
        print("No data")

    # Per-phase details without power factor
    for phase in ['phase_r', 'phase_s', 'phase_t']:
        p = off_grid[phase]
        phase_letter = phase[-1].upper()
        voltage = p.get('voltage')
        print(f"Phase {phase_letter}: ", end="")
        if all(v is not None for v in [voltage, p.get('current'), p.get('active_power')]):
            print(f"{voltage:.1f}V, {p['current']:.2f}A, {p['active_power']:.2f}kW")
        else:
            print("No data")

    print("\n=== Generation Statistics ===")
    gen = data['generation']
    if gen['daily'] is not None:
        print(f"Daily Generation: {gen['daily']:.2f}kWh")
    if gen['total'] is not None:
        print(f"Total Generation: {gen['total']:.1f}kWh")
    if gen['load_daily'] is not None:
        print(f"Daily Load: {gen['load_daily']:.2f}kWh")
    if gen['load_total'] is not None:
        print(f"Total Load: {gen['load_total']:.1f}kWh")
    if gen['bought_daily'] is not None:
        print(f"Daily Energy Bought: {gen['bought_daily']:.2f}kWh")
    if gen['bought_total'] is not None:
        print(f"Total Energy Bought: {gen['bought_total']:.1f}kWh")
    if gen['sold_daily'] is not None:
        print(f"Daily Energy Sold: {gen['sold_daily']:.2f}kWh")
    if gen['sold_total'] is not None:
        print(f"Total Energy Sold: {gen['sold_total']:.1f}kWh")
    if gen['battery_charge_daily'] is not None:
        print(f"Daily Battery Charge: {gen['battery_charge_daily']:.2f}kWh")
    if gen['battery_charge_total'] is not None:
        print(f"Total Battery Charge: {gen['battery_charge_total']:.1f}kWh")
    if gen['battery_discharge_daily'] is not None:
        print(f"Daily Battery Discharge: {gen['battery_discharge_daily']:.2f}kWh")
    if gen['battery_discharge_total'] is not None:
        print(f"Total Battery Discharge: {gen['battery_discharge_total']:.1f}kWh")

    if 'batteries' in data:
        print("\n=== Battery Status ===")
        batteries = data['batteries']
        for bat_num in range(2):
            bat_key = f'battery_{bat_num + 1}'
            if bat_key in batteries:
                bat = batteries[bat_key]
                if any(v is not None for v in bat.values()):
                    # Print Battery Header
                    print(f"Battery{bat_num + 1}: ", end="")

                    # Format each value or display "NA" if the value is None
                    voltage = f"{bat['voltage']:.1f}V" if bat['voltage'] is not None else "NA"
                    current = f"{bat['current']:.2f}A" if bat['current'] is not None else "NA"
                    power = f"{bat['power']:.0f}W" if bat['power'] is not None else "NA"
                    temperature = f"{bat['temperature']:.1f}°C" if bat['temperature'] is not None else "NA"
                    soc = f"{bat['soc']:.1f}%" if bat['soc'] is not None else "NA"
                    soh = f"{bat['soh']:.1f}%" if bat['soh'] is not None else "NA"
                    cycles = f"{bat['cycles']}" if bat['cycles'] is not None else "NA"

                    # Print all values in one line
                    print(f"{voltage}, {current}, {power}, {temperature}, {soc}, {soh}, {cycles}")



        if 'settings' in batteries:
            settings = batteries['settings']
            if any(v is not None for v in settings.values()):
                print("\nBattery Settings:")
                if settings['dod'] is not None:
                    print(f"  Depth of Discharge: {settings['dod']}%")
                if settings['eod'] is not None:
                    print(f"  End of Discharge: {settings['eod']}%")
                if settings['eps_buffer'] is not None:
                    print(f"  EPS Buffer: {settings['eps_buffer']}%")
def format_prometheus(data, inverter_name="inverter"):
    """Format data as Prometheus metrics following consistent labeling convention."""
    metrics = []

    metrics.append(f'{inverter_name}{{stats="state"}} {data["status"]["state_decimal"]}')
    metrics.append(f'{inverter_name}{{stats="generation_time"}} {data["status"].get("generation_time_minutes", 0)}')

    metrics.append(f'{inverter_name}{{stats="temp",sensor="ambient"}} {data["status"]["ambient_temp"]}')
    metrics.append(f'{inverter_name}{{stats="temp",sensor="module"}} {data["status"]["module_temp"]}')
    metrics.append(f'{inverter_name}{{stats="temp",sensor="heatsink"}} {data["status"]["heatsink_temp"]}')

    # Fault metrics
    metrics.append(f'{inverter_name}{{stats="fault_count"}} {len(data["faults"])}')
    for code in data['faults']:
        metrics.append(f'{inverter_name}{{stats="fault",code="{code}"}} 1')

    # AC metrics
    metrics.append(f'{inverter_name}{{ac="frequency"}} {data["grid"].get("frequency", 0)}')
    
    # Map phase names to consistent labels
    phase_mapping = {
        "phase_r": "A",
        "phase_s": "B",
        "phase_t": "C"
    }

    # Grid/Load/Generated metrics per phase
    for old_phase, new_phase in phase_mapping.items():
        # Grid voltage
        metrics.append(f'{inverter_name}{{ac="voltage",phase="{new_phase}"}} {data["grid"]["voltage"].get(old_phase, 0)}')
        
        # Grid power (* 1000 for watts)
#        grid_power = data["grid"].get("power", {}).get(old_phase, 0) * -1000
#        metrics.append(f'{inverter_name}{{ac="grid_power",phase="{new_phase}"}} {grid_power}')
        
        # Generated power metrics (* 1000 for watts)
        gen_data = data["grid"]["generation"].get(old_phase, {})
        gen_power = gen_data.get("active_power", 0) * 1000
        metrics.append(f'{inverter_name}{{ac="generated_power",phase="{new_phase}"}} {gen_power}')
        
        # Load power (calculated from grid exchange) (* 1000 for watts)
        pcc_data = data["grid"]["pcc"].get(old_phase, {})
        load_power = pcc_data.get("active_power", 0) * -1000
        metrics.append(f'{inverter_name}{{ac="grid_power",phase="{new_phase}"}} {load_power}')

    # Total power metrics (* 1000 for watts)
    total_grid = data["grid"]["pcc"]["total"].get("active", 0) * -1000
    total_generated = data["grid"]["generation"]["total"].get("active", 0) * 1000
    metrics.append(f'{inverter_name}{{ac="total_grid_power"}} {total_grid}')
    metrics.append(f'{inverter_name}{{ac="total_generated_power"}} {total_generated}')
    
    # DC (Solar PV) metrics
    for i in range(1, 3):
        mppt = f"mppt{i}"
        pv_data = data[f'pv{i}']
        metrics.append(f'{inverter_name}{{dc="pv_voltage",string="{mppt}"}} {pv_data["voltage"] or 0}')
        metrics.append(f'{inverter_name}{{dc="pv_current",string="{mppt}"}} {pv_data["current"] or 0}')
        # PV power (* 1000 for watts)
        pv_power = (pv_data["power"] or 0) * 1000
        metrics.append(f'{inverter_name}{{dc="pv_power",string="{mppt}"}} {pv_power}')

    # Battery metrics - handle both batteries
    for bat_num in range(1, 3):
        bat_key = f'battery_{bat_num}'
        bat_data = data['batteries'].get(bat_key, {})
        if bat_data:
            metrics.append(f'{inverter_name}{{batt="voltage",battery_num="{bat_num}"}} {bat_data.get("voltage", 0)}')
            metrics.append(f'{inverter_name}{{batt="out_current",battery_num="{bat_num}"}} {bat_data.get("current", 0)}')
            # Battery power (* 1000 for watts)
            bat_power = bat_data.get("power", 0) * 1000
            metrics.append(f'{inverter_name}{{batt="out_power",battery_num="{bat_num}"}} {bat_power}')
            metrics.append(f'{inverter_name}{{batt="batt_temp",battery_num="{bat_num}"}} {bat_data.get("temperature", 0)}')
            metrics.append(f'{inverter_name}{{batt="batt_soc",battery_num="{bat_num}"}} {bat_data.get("soc", 0)}')
            metrics.append(f'{inverter_name}{{batt="health",battery_num="{bat_num}"}} {bat_data.get("soh", 0)}')
            metrics.append(f'{inverter_name}{{batt="cycles",battery_num="{bat_num}"}} {bat_data.get("cycles", 0)}')

    # Energy totals (kWh values - not multiplied by 1000)
    metrics.append(f'{inverter_name}{{energy="total_from_pv"}} {data["generation"].get("total", 0)}')
    metrics.append(f'{inverter_name}{{energy="total_from_grid"}} {data["generation"].get("bought_total", 0)}')
    metrics.append(f'{inverter_name}{{energy="total_to_load"}} {data["generation"].get("load_total", 0)}')
    metrics.append(f'{inverter_name}{{energy="total_to_grid"}} {data["generation"].get("sold_total", 0)}')
    metrics.append(f'{inverter_name}{{energy="total_battery_charge"}} {data["generation"].get("battery_charge_total", 0)}')
    metrics.append(f'{inverter_name}{{energy="total_battery_discharge"}} {data["generation"].get("battery_discharge_total", 0)}')

    # Daily energy metrics (kWh values - not multiplied by 1000)
    metrics.append(f'{inverter_name}{{energy="daily_from_pv"}} {data["generation"].get("daily", 0)}')
    metrics.append(f'{inverter_name}{{energy="daily_from_grid"}} {data["generation"].get("bought_daily", 0)}')
    metrics.append(f'{inverter_name}{{energy="daily_to_load"}} {data["generation"].get("load_daily", 0)}')
    metrics.append(f'{inverter_name}{{energy="daily_to_grid"}} {data["generation"].get("sold_daily", 0)}')
    metrics.append(f'{inverter_name}{{energy="daily_battery_charge"}} {data["generation"].get("battery_charge_daily", 0)}')
    metrics.append(f'{inverter_name}{{energy="daily_battery_discharge"}} {data["generation"].get("battery_discharge_daily", 0)}')

    # Additional CALCULATED metrics
    generation_total = data["grid"]["generation"]["total"].get("active", 0)  # Make positive
    pcc_total = abs(data["grid"]["pcc"]["total"].get("active", 0))
    total_load_power = round((generation_total + pcc_total) * 1000)  # Convert to watts
    metrics.append(f'{inverter_name}{{ac="total_load_power"}} {total_load_power}')
    # Grid/Load/Generated metrics per phase
    for old_phase, new_phase in phase_mapping.items():

        # Generated and PCC power for load calculation
        gen_data = data["grid"]["generation"].get(old_phase, {})
        generation_power = gen_data.get("active_power", 0)
        
        pcc_data = data["grid"]["pcc"].get(old_phase, {})
        pcc_power = abs(pcc_data.get("active_power", 0))
        
        # Calculate load power for this phase
        phase_load_power = round((generation_power + pcc_power) * 1000)
        # Output all power metrics (* 1000 for watts)
        metrics.append(f'{inverter_name}{{ac="load_power",phase="{new_phase}"}} {phase_load_power}')


    return "\n".join(metrics)


def main():
    """Main function"""
    # Set up argument parsing
    parser = argparse.ArgumentParser(description="Monitor and log data from the Sofar inverter.")
    parser.add_argument("--format", choices=["json", "prometheus"], help="Output format: json or prometheus.")
    args = parser.parse_args()

    # Change to script directory
    os.chdir(os.path.dirname(sys.argv[0]))
    
    # Load configuration
    config = load_config()
    
    # Define register ranges
    register_ranges = [
        ('0x0400', '0x0432'),  # Inverter status, temperatures
        ('0x0445', '0x0465'),  # Serial number, versions
        ('0x0480', '0x04BC'),  # Grid metrics
        ('0x0504', '0x051F'),  # Off-grid
        ('0x0580', '0x0589'),  # PV inputs
        ('0x0600', '0x0611'),  # Battery 1
        ('0x0684', '0x069B'),  # Generation data
        ('0x104D', '0x104E'),  # Battery DOD and EOD
        ('0x1052', '0x1052'),  # Battery EPS buffer
    ]

    # Store all register values
    all_values = {}

    # Query each register range
    for start, end in register_ranges:
        pini = int(start, 0)
        pfin = int(end, 0)
        
        frame = create_frame(config['inverter_sn'], pini, pfin - pini + 1, config['verbose'] == "1")
        response = query_registers(config['inverter_ip'], config['inverter_port'], frame, config['verbose'] == "1")
        
        if response:
            values = process_response(response, pini, pfin - pini + 1, config['verbose'] == "1")
            all_values.update(values)

    # Format the collected data
    if all_values:
        data = format_data(all_values)
        
        # Save to JSON file
#        with open('inverter_data.json', 'w') as f:
#            json.dump(data, f, indent=2)
        
        # Check output format
        if args.format == "json":
            print(json.dumps(data, indent=2))
        elif args.format == "prometheus":
            print(format_prometheus(data,inverter_name="sofar"))
        else:
            # Default: Print formatted text output
            print_data(data)
    else:
        print("No data received from inverter")

if __name__ == "__main__":
    main()