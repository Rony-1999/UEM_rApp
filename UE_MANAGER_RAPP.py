from flask import render_template_string

from flask import Flask, request, jsonify
from flask_cors import CORS
from influxdb_client.client.write_api import SYNCHRONOUS
from influxdb_client.client.exceptions import InfluxDBError
from influxdb_client import InfluxDBClient
import requests
import urllib3
import json
import time
from requests.exceptions import RequestException, Timeout

# Configuration
INFLUXDB_HOST = "10.33.42.45"
INFLUXDB_PORT = 8086
INFLUXDB_USERNAME = "admin"
INFLUXDB_PASSWORD = "mySuP3rS3cr3tT0keN"
INFLUXDB_ORG = "iosmcn"
INFLUXDB_BUCKET = "pm-logg-bucket"
HOST_IP = "10.33.42.120"
HOST_PORT = 5002
USAGE_THRESHOLD = 12
POLICY_MANAGER_URL = "http://10.33.42.120:5002/policies"

# Store successful policies
created_policies = []

# Global counter for policy type ID
policytype_counter = 0

# Initialize Flask
app = Flask(__name__)
CORS(app)

# Suppress SSL Warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Initialize InfluxDB Client (non-SSL)
client = InfluxDBClient(
    url=f"http://{INFLUXDB_HOST}:{INFLUXDB_PORT}",
    username=INFLUXDB_USERNAME,
    password=INFLUXDB_PASSWORD,
    org=INFLUXDB_ORG
)

def fetch_performance_data(query):
    try:
        query_api = client.query_api()
        result = query_api.query(query, org=INFLUXDB_ORG)

        if not result:
            print("[INFO] No data found.")
            return []

        data = []
        for table in result:
            for record in table.records:
                measurement = record.get_measurement()
                field = record.get_field()
                value = record.get_value()
                ric_id = measurement.split(",")[0].replace("ManagedElement=", "")

                data.append({
                    "measurement": measurement,
                    "field": field,
                    "value": value,
                    "ric_id": ric_id
                })

                if field == "DRB.MeanActiveUeDl" and isinstance(value, (int, float)) and value > USAGE_THRESHOLD:
                    print(f"[THRESHOLD] Exceeded: {measurement} - {field} = {value}")
                    trigger_policy_creation(ric_id, field, value)

        return data

    except Exception as e:
        print(f"[ERROR] InfluxDB query failed: {e}")
        return []

def trigger_policy_creation(ric_id, field, value):
    policy_id = f"policy_{ric_id}_{int(time.time())}"
    
    global policytype_counter
    current_policytype_id = policytype_counter
    policytype_counter += 1
    
    policy = {
        "ric_id": ric_id,
        "policy_id": policy_id,
        "service_id": "UE_MANAGEMENT",
        "policy_data": {
            "field": field,
            "value": value,
            "threshold": USAGE_THRESHOLD
        },
        "policytype_id": current_policytype_id
    }
    try:
        headers = {"Content-Type": "application/json"}
        print(f"[POST] Sending policy to: {POLICY_MANAGER_URL}")
        print(json.dumps(policy, indent=2))

        response = requests.post(POLICY_MANAGER_URL, json=policy, headers=headers, timeout=15, verify=False)

        print(f"[RESPONSE] {response.status_code} - {response.text}")
        if response.status_code == 200:
            created_policies.append(policy)
            return True
        else:
            print(f"[ERROR] Policy manager responded with status {response.status_code}")
            return False

    except Timeout:
        print("[ERROR] Request to policy manager timed out")
        return False
    except RequestException as e:
        print(f"[ERROR] Failed to create policy: {e}")
        return False

@app.route('/policies', methods=['GET','POST'])
def handle_policy():
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "No JSON data provided"}), 400

        ric_id = data.get("ric_id")
        policy_data = data.get("policy_data", {})
        field = policy_data.get("field")
        value = policy_data.get("value")

        if not all([ric_id, field, value]):
            return jsonify({"error": "Missing required fields"}), 400

        # Do NOT call trigger_policy_creation here to avoid loops.
        print(f"[INFO] Policy received: {json.dumps(data, indent=2)}")

        return jsonify({"status": "Policy received"}), 200

    except Exception as e:
        print(f"[ERROR] /policies endpoint: {e}")
        return jsonify({"error": "Internal server error"}), 500

@app.route('/metrics', methods=['GET'])
def metrics():
    query = '''
        from(bucket: "pm-logg-bucket")
        |> range(start: -30d)
        |> filter(fn: (r) => r["_field"] == "DRB.MeanActiveUeDl")
    '''
    data = fetch_performance_data(query)
    return jsonify(data) if data else (jsonify({"error": "No metrics found"}), 404)

@app.route('/rics', methods=['GET'])
def get_rics():
    try:
        resp = requests.get("https://10.33.42.14:8081/rics", timeout=10, verify=False)
        resp.raise_for_status()
        return jsonify(resp.json())
    except RequestException as e:
        print(f"[ERROR] Fetching RICs: {e}")
        return jsonify({"error": "Failed to fetch RICs"}), 500


@app.route('/policies/view', methods=['GET'])
def view_created_policies():
    html_template = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Created Policies</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            background-color: #f4f6f8;
            color: #333;
            padding: 20px;
        }

        h1 {
            color: #2c3e50;
            text-align: center;
        }

        table {
            margin: 20px auto;
            border-collapse: collapse;
            width: 90%;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            background-color: white;
        }

        th, td {
            border: 1px solid #ddd;
            padding: 12px 15px;
            text-align: left;
        }

        th {
            background-color: #3498db;
            color: white;
        }

        tr:nth-child(even) {
            background-color: #f2f2f2;
        }

        tr:hover {
            background-color: #e1f5fe;
        }

        p {
            text-align: center;
            font-size: 1.2em;
            color: #7f8c8d;
        }
    </style>
</head>
<body>
    <h1>Policies Creation</h1>
    {% if policies %}
    <table>
        <tr>
            <th>RIC ID</th>
            <th>Policy ID</th>
            <th>Service ID</th>
            <th>Field</th>
            <th>Value</th>
            <th>Threshold</th>
            <th>Policy Type ID</th>
        </tr>
        {% for policy in policies %}
        <tr>
            <td>{{ policy.ric_id }}</td>
            <td>{{ policy.policy_id }}</td>
            <td>{{ policy.service_id }}</td>
            <td>{{ policy.policy_data.field }}</td>
            <td>{{ policy.policy_data.value }}</td>
            <td>{{ policy.policy_data.threshold }}</td>
            <td>{{ policy.policytype_id }}</td>
        </tr>
        {% endfor %}
    </table>
    {% else %}
    <p>No policies created yet.</p>
    {% endif %}
</body>
</html>
"""
    return render_template_string(html_template, policies=created_policies)


if __name__ == '__main__':
    app.run(host=HOST_IP, port=HOST_PORT, debug=True)

