# Sofar Solar Inverter Monitoring for SOFAR HYD 5K...20KTL-3PH

This Python script monitors data from a Sofar solar inverter and outputs relevant metrics in JSON and Prometheus-ready formats. It collects metrics such as voltage, current, power generation, grid metrics, and fault codes, making it suitable for integration with monitoring tools like Prometheus and Grafana.

*Thanks to @Nedel124 https://github.com/Nedel124/Sofar_G3_LSW3

*Thanks to @MichaluxPL https://github.com/MichaluxPL/Sofar_LSW3 

From where I got the backbone 

## Configuration

Move config.cfg.example to config.cfg and edit - enter the following data:
```
[SofarInverter]
inverter_ip=X.X.X.X             # data logger IP
inverter_port=8899              # data logger port
inverter_sn=XXXXXXXXXX          # data logger S/N
verbose=0                       # Set to 1 for additional info to be presented (registers, binary packets etc.)
```

## Required python modules
To run, script requires following python modules:
```
libscrc
```

## Features

- **Data Collection**: Gathers inverter metrics, including PV voltage, current, active and reactive power, grid frequency, and off-grid values.
- **Fault Monitoring**: Tracks fault codes from the inverter, storing them as numeric values and providing a fault count for simplified monitoring.
- **Output Formats**:
  - **Human readable**: Outputs metrics in Human-readable format
  - **JSON**: Provides structured JSON output for detailed data analysis and logging.
  - **Prometheus**: Outputs metrics in Prometheus format for easy integration with monitoring systems.
- **Drawing Graphs (Using Grafana + Prometheus - requires fluent knowledge in both to setup)**:
  ![Grafana](https://github.com/ilia92/sofar-monitor/blob/main/exporter/grafana_screenshot.png?raw=true)

## Usage

Run the script with the following options or without an option:
- **`./sofar-monitor.py `**: Outputs metrics in Human-readable format
- **`./sofar-monitor.py --format=json`**: Outputs data in JSON format.
- **`./sofar-monitor.py --format=prometheus`**: Outputs data in a Prometheus-compatible format, including individual fault codes and metrics.

## Example Output

### Default:
```
$ ./sofar-monitor.py

=== Inverter Status ===
Status: Waiting

=== Fault Status ===
No active faults

=== PV Input Values ===
PV1: 5.6V, 0.00A, 0.00kW
PV2: 13.0V, 0.00A, 0.00kW

=== Grid Values ===
Grid Frequency: 49.99Hz

Generated Power:
Total: 0.00kW
Phase R: 239.2V, 0.02A, 0.00kW, PF: 0.000
Phase S: 235.7V, 0.02A, 0.00kW, PF: 0.000
Phase T: 235.1V, 0.02A, 0.00kW, PF: 0.000

Grid Exchange (PCC):
Total: -1.82kW
Phase R: 239.2V, 7.00A, -1.60kW, PF: 0.000
Phase S: 235.7V, 0.72A, -0.03kW, PF: 0.000
Phase T: 235.1V, 1.18A, -0.19kW, PF: 0.000

=== Off-grid Values ===
Frequency: 49.99Hz
Total: 0.00kW
Phase R: 2.8V, 0.23A, 0.00kW
Phase S: 0.8V, 0.21A, 0.00kW
Phase T: 1.0V, 0.22A, 0.00kW

=== Generation Statistics ===
Daily Generation: 0.00kWh
Total Generation: 83.8kWh
Daily Load: 4.97kWh
Total Load: 211.6kWh
Daily Energy Bought: 4.96kWh
Total Energy Bought: 132.6kWh
Daily Energy Sold: 0.00kWh
Total Energy Sold: 2.2kWh
Daily Battery Charge: 0.00kWh
Total Battery Charge: 0.0kWh
Daily Battery Discharge: 0.00kWh
Total Battery Discharge: 0.0kWh

=== Battery Status ===
Battery1: 0.0V, 0.00A, 0W, 0.0°C, 0.0%, 0.0%, 0
Battery2: 0.0V, 0.00A, 0W, 0.0°C, 0.0%, 0.0%, 0

Battery Settings:
  Depth of Discharge: 50%
  End of Discharge: 50%
  EPS Buffer: 5%

```

### JSON Output

```
$ ./sofar-monitor.py --format=json

{
    {
  "timestamp": "2024-11-03T02:41:31.635598",
  "status": {
    "state": "Waiting",
    "state_decimal": 0,
    "generation_time_minutes": 0
  },
  "faults": [],
  "pv1": {
    "voltage": 5.6,
    "current": 0.0,
    "power": 0.0
  },
  "pv2": {
    "voltage": 13.0,
    "current": 0.0,
    "power": 0.0
  },
  "grid": {
    "frequency": 49.99,
    "voltage": {
      "phase_r": 239.9,
      "phase_s": 235.0,
      "phase_t": 234.6
    },
    "generation": {
      "total": {
        "active": 0.0,
        "reactive": 0.0,
        "apparent": 0.0
      },
      "phase_r": {
        "current": 0.02,
        "active_power": 0.0,
        "reactive_power": 0.0,
        "power_factor": 0.0
      },
      "phase_s": {
        "current": 0.02,
        "active_power": 0.0,
        "reactive_power": 0.0,
        "power_factor": 0.0
      },
      "phase_t": {
        "current": 0.02,
        "active_power": 0.0,
        "reactive_power": 0.0,
        "power_factor": 0.0
      }
    },
    "pcc": {
      "total": {
        "active": -1.81,
        "reactive": 0.0,
        "apparent": 0.0
      },
      "phase_r": {
        "current": 7.0,
        "active_power": -1.6,
        "reactive_power": 0.0,
        "power_factor": 0.0
      },
      "phase_s": {
        "current": 0.72,
        "active_power": -0.03,
        "reactive_power": 0.0,
        "power_factor": 0.0
      },
      "phase_t": {
        "current": 1.18,
        "active_power": -0.18,
        "reactive_power": 0.0,
        "power_factor": 0.0
      }
    }
  },
  "off_grid": {
    "frequency": 49.99,
    "total": {
      "active": 0.0,
      "reactive": 0.0,
      "apparent": 0.0
    },
    "phase_r": {
      "voltage": 2.8,
      "current": 0.22,
      "active_power": 0.0,
      "reactive_power": 0.0,
      "apparent_power": 0.0
    },
    "phase_s": {
      "voltage": 0.8,
      "current": 0.21,
      "active_power": 0.0,
      "reactive_power": 0.0,
      "apparent_power": 0.0
    },
    "phase_t": {
      "voltage": 1.0,
      "current": 0.22,
      "active_power": 0.0,
      "reactive_power": 0.0,
      "apparent_power": 0.0
    }
  },
  "generation": {
    "daily": 0.0,
    "total": 83.8,
    "load_daily": 4.97,
    "load_total": 211.6,
    "bought_daily": 4.96,
    "bought_total": 132.6,
    "sold_daily": 0.0,
    "sold_total": 2.2,
    "battery_charge_daily": 0.0,
    "battery_charge_total": 0.0,
    "battery_discharge_daily": 0.0,
    "battery_discharge_total": 0.0
  },
  "batteries": {
    "battery_1": {
      "voltage": 0.0,
      "current": 0.0,
      "power": 0,
      "temperature": 0,
      "soc": 0,
      "soh": 0,
      "cycles": 0
    },
    "battery_2": {
      "voltage": 0.0,
      "current": 0.0,
      "power": 0,
      "temperature": 0,
      "soc": 0,
      "soh": 0,
      "cycles": 0
    },
    "settings": {
      "dod": 50,
      "eod": 50,
      "eps_buffer": 5
    }
  }
}

}
```

### Prometheus Output

```
$ ./sofar-monitor.py --format=prometheus

sofar{stats="state"} 2
sofar{stats="generation_time"} 202
sofar{stats="temp",sensor="ambient"} 36.0
sofar{stats="temp",sensor="module"} 31.0
sofar{stats="temp",sensor="heatsink"} 26.0
sofar{stats="fault_count"} 0
sofar{ac="frequency"} 49.99
sofar{ac="voltage",phase="A"} 232.6
sofar{ac="generated_power",phase="A"} 100.0
sofar{ac="grid_power",phase="A"} 1480.0
sofar{ac="voltage",phase="B"} 228.4
sofar{ac="generated_power",phase="B"} 180.0
sofar{ac="grid_power",phase="B"} 1480.0
sofar{ac="voltage",phase="C"} 225.0
sofar{ac="generated_power",phase="C"} 930.0
sofar{ac="grid_power",phase="C"} 1490.0
sofar{ac="total_grid_power"} 4450.0
sofar{ac="total_generated_power"} 1220.0
sofar{dc="pv_voltage",string="mppt1"} 796.1
sofar{dc="pv_current",string="mppt1"} 0.73
sofar{dc="pv_power",string="mppt1"} 580.0
sofar{dc="pv_voltage",string="mppt2"} 814.1
sofar{dc="pv_current",string="mppt2"} 0.91
sofar{dc="pv_power",string="mppt2"} 740.0
sofar{batt="voltage",battery_num="1"} 0.0
sofar{batt="out_current",battery_num="1"} 0.0
sofar{batt="out_power",battery_num="1"} 0
sofar{batt="batt_temp",battery_num="1"} 0
sofar{batt="batt_soc",battery_num="1"} 0
sofar{batt="health",battery_num="1"} 0
sofar{batt="cycles",battery_num="1"} 0
sofar{batt="voltage",battery_num="2"} 0.0
sofar{batt="out_current",battery_num="2"} 0.0
sofar{batt="out_power",battery_num="2"} 0
sofar{batt="batt_temp",battery_num="2"} 0
sofar{batt="batt_soc",battery_num="2"} 0
sofar{batt="health",battery_num="2"} 0
sofar{batt="cycles",battery_num="2"} 0
sofar{energy="total_from_pv"} 87.0
sofar{energy="total_from_grid"} 152.3
sofar{energy="total_to_load"} 234.2
sofar{energy="total_to_grid"} 2.2
sofar{energy="total_battery_charge"} 0.0
sofar{energy="total_battery_discharge"} 0.0
sofar{energy="daily_from_pv"} 3.2
sofar{energy="daily_from_grid"} 24.66
sofar{energy="daily_to_load"} 27.58
sofar{energy="daily_to_grid"} 0.0
sofar{energy="daily_battery_charge"} 0.0
sofar{energy="daily_battery_discharge"} 0.0
sofar{ac="total_load_power"} 5670
sofar{ac="load_power",phase="A"} 1580
sofar{ac="load_power",phase="B"} 1660
sofar{ac="load_power",phase="C"} 2420
```

## Requirements

- Python 3.x
- Prometheus server (optional for monitoring)
- Grafana (optional for visualization)

## Customization

- **Value Mapping in Grafana**: Map fault codes to human-readable descriptions using Grafana's Value Mapping feature to enhance fault code interpretation.

## License

This project is licensed under the MIT License. See `LICENSE` for details.
