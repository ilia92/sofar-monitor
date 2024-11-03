# Running Sofar Solar Exporter as a Service with systemd

This guide will help you set up your Sofar Solar exporter to run as a systemd service, allowing it to start automatically on boot and be managed with `systemctl` commands.

## Prerequisites

    ```bash
    pip3 install flask gunicorn
    ```

## Step 1: Create a systemd Service File

1. Open a new service file for editing:

   ```bash
   sudo nano /etc/systemd/system/sofar-solar-exporter.service
   ```

2. Add the following configuration to the file:

   ```ini
   [Unit]
   Description=Sofar Solar Exporter Service
   After=network.target

   [Service]
   User=your_username
   WorkingDirectory=/path/to/your/exporter
   ExecStart=/usr/bin/gunicorn -w 4 -b 0.0.0.0:9000 prometheus-exporter:app
   Restart=always

   [Install]
   WantedBy=multi-user.target
   ```

   Replace:
   - `your_username` with the username that should run the service.
   - `/path/to/your/exporter` with the path to the directory containing `prometheus-exporter.py`.

   This configuration:
   - Runs Gunicorn with 4 workers.
   - Binds to all interfaces on port `9000`.
   - Restarts the service automatically if it fails.

## Step 2: Reload systemd and Start the Service

1. Reload the systemd daemon to recognize the new service file:

   ```bash
   sudo systemctl daemon-reload
   ```

2. Start the Sofar Solar exporter service:

   ```bash
   sudo systemctl start sofar-solar-exporter
   ```

3. Enable it to start on boot:

   ```bash
   sudo systemctl enable sofar-solar-exporter
   ```

## Step 3: Manage the Service

- To check the status of the service:

  ```bash
  sudo systemctl status sofar-solar-exporter
  ```

- To stop the service:

  ```bash
  sudo systemctl stop sofar-solar-exporter
  ```

- To restart the service:

  ```bash
  sudo systemctl restart sofar-solar-exporter
  ```

## Summary

Your Sofar Solar exporter will now run as a managed service, automatically starting on boot and restarting if it encounters issues.
