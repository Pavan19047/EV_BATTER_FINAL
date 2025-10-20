import requests
import json

auth = ('admin', 'admin')

dashboard = {
    'dashboard': {
        'title': 'EV Battery Digital Twin - Real-time Monitoring',
        'uid': 'ev-battery-monitoring',
        'tags': ['EV', 'Battery', 'Predictions'],
        'panels': [
            {
                'id': 1,
                'type': 'stat',
                'title': 'State of Charge (SoC)',
                'gridPos': {'x': 0, 'y': 0, 'w': 6, 'h': 4},
                'targets': [{
                    'datasource': {'type': 'postgres', 'uid': 'PCC52D03280B7034C'},
                    'rawSql': 'SELECT soc as "SoC" FROM telemetry ORDER BY ts DESC LIMIT 1',
                    'refId': 'A',
                    'format': 'table'
                }],
                'fieldConfig': {
                    'defaults': {
                        'unit': 'percent',
                        'color': {'mode': 'thresholds'},
                        'thresholds': {
                            'mode': 'absolute',
                            'steps': [
                                {'value': 0, 'color': 'red'},
                                {'value': 20, 'color': 'orange'},
                                {'value': 50, 'color': 'yellow'},
                                {'value': 80, 'color': 'green'}
                            ]
                        },
                        'max': 100,
                        'min': 0
                    }
                },
                'options': {'graphMode': 'area', 'colorMode': 'background'}
            },
            {
                'id': 2,
                'type': 'stat',
                'title': 'State of Health (SoH)',
                'gridPos': {'x': 6, 'y': 0, 'w': 6, 'h': 4},
                'targets': [{
                    'datasource': {'type': 'postgres', 'uid': 'PCC52D03280B7034C'},
                    'rawSql': 'SELECT soh as "SoH" FROM telemetry ORDER BY ts DESC LIMIT 1',
                    'refId': 'A',
                    'format': 'table'
                }],
                'fieldConfig': {
                    'defaults': {
                        'unit': 'percent',
                        'color': {'mode': 'thresholds'},
                        'thresholds': {
                            'mode': 'absolute',
                            'steps': [
                                {'value': 0, 'color': 'red'},
                                {'value': 70, 'color': 'orange'},
                                {'value': 85, 'color': 'yellow'},
                                {'value': 95, 'color': 'green'}
                            ]
                        },
                        'max': 100,
                        'min': 0
                    }
                },
                'options': {'graphMode': 'area', 'colorMode': 'background'}
            },
            {
                'id': 3,
                'type': 'stat',
                'title': 'Battery Voltage',
                'gridPos': {'x': 12, 'y': 0, 'w': 6, 'h': 4},
                'targets': [{
                    'datasource': {'type': 'postgres', 'uid': 'PCC52D03280B7034C'},
                    'rawSql': 'SELECT battery_voltage as "Voltage" FROM telemetry ORDER BY ts DESC LIMIT 1',
                    'refId': 'A',
                    'format': 'table'
                }],
                'fieldConfig': {
                    'defaults': {
                        'unit': 'volt',
                        'decimals': 1
                    }
                },
                'options': {'graphMode': 'area', 'colorMode': 'value'}
            },
            {
                'id': 4,
                'type': 'stat',
                'title': 'Battery Temperature',
                'gridPos': {'x': 18, 'y': 0, 'w': 6, 'h': 4},
                'targets': [{
                    'datasource': {'type': 'postgres', 'uid': 'PCC52D03280B7034C'},
                    'rawSql': 'SELECT battery_temperature as "Temperature" FROM telemetry ORDER BY ts DESC LIMIT 1',
                    'refId': 'A',
                    'format': 'table'
                }],
                'fieldConfig': {
                    'defaults': {
                        'unit': 'celsius',
                        'decimals': 1,
                        'color': {'mode': 'thresholds'},
                        'thresholds': {
                            'mode': 'absolute',
                            'steps': [
                                {'value': 0, 'color': 'blue'},
                                {'value': 20, 'color': 'green'},
                                {'value': 40, 'color': 'orange'},
                                {'value': 50, 'color': 'red'}
                            ]
                        }
                    }
                },
                'options': {'graphMode': 'area', 'colorMode': 'background'}
            },
            {
                'id': 5,
                'type': 'timeseries',
                'title': 'Battery State - SoC and SoH Over Time',
                'gridPos': {'x': 0, 'y': 4, 'w': 12, 'h': 8},
                'targets': [
                    {
                        'datasource': {'type': 'postgres', 'uid': 'PCC52D03280B7034C'},
                        'rawSql': 'SELECT ts as time, soc as "SoC (%)" FROM telemetry WHERE ts >= NOW() - INTERVAL \'15 minutes\' ORDER BY ts',
                        'refId': 'A',
                        'format': 'time_series'
                    },
                    {
                        'datasource': {'type': 'postgres', 'uid': 'PCC52D03280B7034C'},
                        'rawSql': 'SELECT ts as time, soh as "SoH (%)" FROM telemetry WHERE ts >= NOW() - INTERVAL \'15 minutes\' ORDER BY ts',
                        'refId': 'B',
                        'format': 'time_series'
                    }
                ],
                'fieldConfig': {
                    'defaults': {
                        'unit': 'percent',
                        'max': 100,
                        'min': 0
                    }
                }
            },
            {
                'id': 6,
                'type': 'timeseries',
                'title': 'Battery Voltage and Temperature',
                'gridPos': {'x': 12, 'y': 4, 'w': 12, 'h': 8},
                'targets': [
                    {
                        'datasource': {'type': 'postgres', 'uid': 'PCC52D03280B7034C'},
                        'rawSql': 'SELECT ts as time, battery_voltage as "Voltage (V)" FROM telemetry WHERE ts >= NOW() - INTERVAL \'15 minutes\' ORDER BY ts',
                        'refId': 'A',
                        'format': 'time_series'
                    },
                    {
                        'datasource': {'type': 'postgres', 'uid': 'PCC52D03280B7034C'},
                        'rawSql': 'SELECT ts as time, battery_temperature as "Temperature (C)" FROM telemetry WHERE ts >= NOW() - INTERVAL \'15 minutes\' ORDER BY ts',
                        'refId': 'B',
                        'format': 'time_series'
                    }
                ],
                'fieldConfig': {'defaults': {}}
            },
            {
                'id': 7,
                'type': 'timeseries',
                'title': 'Battery Current and Power',
                'gridPos': {'x': 0, 'y': 12, 'w': 12, 'h': 8},
                'targets': [
                    {
                        'datasource': {'type': 'postgres', 'uid': 'PCC52D03280B7034C'},
                        'rawSql': 'SELECT ts as time, battery_current as "Current (A)" FROM telemetry WHERE ts >= NOW() - INTERVAL \'15 minutes\' ORDER BY ts',
                        'refId': 'A',
                        'format': 'time_series'
                    },
                    {
                        'datasource': {'type': 'postgres', 'uid': 'PCC52D03280B7034C'},
                        'rawSql': 'SELECT ts as time, power_consumption as "Power (W)" FROM telemetry WHERE ts >= NOW() - INTERVAL \'15 minutes\' ORDER BY ts',
                        'refId': 'B',
                        'format': 'time_series'
                    }
                ],
                'fieldConfig': {'defaults': {}}
            },
            {
                'id': 8,
                'type': 'timeseries',
                'title': 'Vehicle Speed and Distance',
                'gridPos': {'x': 12, 'y': 12, 'w': 12, 'h': 8},
                'targets': [
                    {
                        'datasource': {'type': 'postgres', 'uid': 'PCC52D03280B7034C'},
                        'rawSql': 'SELECT ts as time, vehicle_speed as "Speed (km/h)" FROM telemetry WHERE ts >= NOW() - INTERVAL \'15 minutes\' ORDER BY ts',
                        'refId': 'A',
                        'format': 'time_series'
                    },
                    {
                        'datasource': {'type': 'postgres', 'uid': 'PCC52D03280B7034C'},
                        'rawSql': 'SELECT ts as time, distance_traveled as "Distance (km)" FROM telemetry WHERE ts >= NOW() - INTERVAL \'15 minutes\' ORDER BY ts',
                        'refId': 'B',
                        'format': 'time_series'
                    }
                ],
                'fieldConfig': {'defaults': {}}
            }
        ],
        'refresh': '5s',
        'time': {'from': 'now-15m', 'to': 'now'},
        'timepicker': {'refresh_intervals': ['5s', '10s', '30s', '1m', '5m']}
    },
    'overwrite': True
}

response = requests.post('http://localhost:3000/api/dashboards/db', 
                        json=dashboard, 
                        auth=auth)
print(f'Status: {response.status_code}')
result = response.json()
print(f'Dashboard URL: http://localhost:3000{result.get("url", "")}')
print(f'UID: {result.get("uid", "")}')
