import network
import time
import ubinascii

from machine import Pin
from machine import PWM
from machine import Timer


class Monitor(object):
    def __init__(self, targets, pin_bell=5):
        self.targets = targets
        self.signal = Pin(pin_bell, Pin.OUT)
        self.t_scan = None
        self.nic = network.WLAN(network.STA_IF)

    def start(self):
        print('Starting...')
        self.t_scan = Timer(-1)
        self.t_scan.init(period=10000, mode=Timer.PERIODIC,
                         callback=lambda t: self.scan())
        print('Started.')

    def stop(self):
        print('Stopping...')
        self.t_scan.deinit()
        self.t_scan = None
        print('Stopped.')

    def scan(self):
        targets = [ubinascii.unhexlify(x) for x in self.targets]
        print('Start scanning t={}'.format(time.time()))
        nets = self.nic.scan()
        for ssid, bssid, channel, rssi, authmode, hidden in nets:
            ssid = ssid.decode()
            _bssid = ubinascii.hexlify(bssid).decode()
            print('Checking ssid "{}" bssid "{}" channel {} rssi {}'.format(
                ssid, _bssid, channel, rssi
            ))
            if bssid in targets:
                print('Found ssid "{}" bssid "{}"'.format(ssid, _bssid))
                self.signal.value(1)
                break
        else:
            self.signal.value(0)

        print('Finished scanning t={}'.format(time.time()))
