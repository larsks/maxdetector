import json
import network
import time


def connect(wait=True):
    try:
        with open('wifi.json', 'r') as fd:
            credentials = json.load(fd)
    except OSError as err:
        print('ERROR: failed to open wifi credentials file: {}'.format(
            err))
        return

    print('Connecting to network {}'.format(credentials['ssid']))

    eth0 = network.WLAN(network.STA_IF)
    eth1 = network.WLAN(network.AP_IF)

    eth1.active(False)
    eth0.active(True)
    eth0.disconnect()
    eth0.connect(credentials['ssid'], credentials['password'])

    if wait:
        while not eth0.isconnected():
            print('Waiting for connection...')
            time.sleep(1)
        print('Connected.')

    if eth0.isconnected():
        print('SSID: {}'.format(eth0.config('essid')))
        print('Address: {}'.format(eth0.ifconfig()[0]))


def set_credentials(ssid, password):
    with open('wifi.json', 'w') as fd:
        json.dump({'ssid': ssid, 'password': password}, fd)
