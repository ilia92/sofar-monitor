#!/usr/bin/python3

from flask import Flask, Response
import subprocess
import os

current_directory = os.path.dirname(os.path.abspath(__file__))
sofar_monitor_file = os.path.join(current_directory, "../sofar-monitor.py")

app = Flask(__name__)


@app.route('/metrics')
def metrics():
    # Run the `sofar-monitor.py` script with --format=prometheus and capture the output
    result = subprocess.run(
        [sofar_monitor_file, "--format=prometheus"],
        capture_output=True,
        text=True
    )
    # Return the output in Prometheus format
    return Response(result.stdout, mimetype='text/plain')

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=9092)
