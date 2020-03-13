import network
import time
import ubinascii

from machine import Pin
from machine import PWM
from machine import Timer


class Monitor(object):
    def __init__(self, targets, pin_bell=5, pin_button=0):
        self.targets = targets
        self.button = Pin(pin_button, Pin.IN, Pin.PULL_UP)
        self.bell = Pin(pin_bell, Pin.OUT)
        self.pwm = PWM(self.bell)
        self.t_scan = None
        self.t_monitor = None
        self.nic = network.WLAN(network.STA_IF)
        self.found = False

    def start(self):
        print('Starting...')
        self.t_scan = Timer(-1)
        self.t_monitor = Timer(-1)
        self.t_scan.init(period=10000, mode=Timer.PERIODIC,
                         callback=lambda t: self.scan())
        self.t_monitor.init(period=100, mode=Timer.PERIODIC,
                            callback=lambda t: self.monitor())
        print('Started.')

    def stop(self):
        print('Stopping...')
        self.t_monitor.deinit()
        self.t_monitor = None
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
                self.found = True
                break
        else:
            self.found = False

        print('Finished scanning t={}'.format(time.time()))

    def monitor(self):
        pwm = self.pwm

        if self.found:
            print('ALARM ALARM')
            pwm.freq(500)
            pwm.duty(512)
            for i in range(2):
                pwm.freq(500)
                time.sleep(0.5)
                pwm.freq(800)
                time.sleep(0.5)

            pwm.duty(0)
            self.found = False
