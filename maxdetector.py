import network
import time
import ubinascii

from machine import Pin
from machine import Timer

DEFAULT_PIN_READY = 4   # D2
DEFAULT_PIN_ALARM = 5  # D1
DEFAULT_SCAN_PERIOD = 10000


class Monitor(object):
    def __init__(self, targets,
                 pin_ready=DEFAULT_PIN_READY,
                 pin_alarm=DEFAULT_PIN_ALARM,
                 scan_period=DEFAULT_SCAN_PERIOD):

        self.targets = targets
        self.alarm = Pin(pin_alarm, Pin.OUT)
        self.ready = Pin(pin_ready, Pin.OUT)
        self.scan_period = scan_period
        self.last_scan = []

        # READY and ALARM are active low. Make sure they are
        # high when we start up.
        self.alarm.value(1)
        self.ready.value(1)

        self.flag_running = False
        self.flag_alarm = False
        self.t_scan = None
        self.nic = network.WLAN(network.STA_IF)

    def start(self):
        '''Start the scanning task.

        Sets the READY signal and schedules the scan() task
        to run every self.scan_period seconds (10 by default).
        '''

        print('Starting...')
        if self.t_scan is None:
            self.t_scan = Timer(-1)
            self.t_scan.init(period=self.scan_period,
                             mode=Timer.PERIODIC,
                             callback=lambda t: self.scan())
        self.ready.value(0)
        self.flag_running = True
        print('Started.')

    def stop(self):
        '''Stop the scanning task.

        Cancel the scanning task and reset the READY signal.
        '''

        print('Stopping...')
        if self.t_scan is not None:
            self.t_scan.deinit()
            self.t_scan = None
        self.ready.value(1)
        self.flag_running = False
        self.flag_alarm = False
        print('Stopped.')

    def scan(self):
        '''Scan for matching BSSIDS

        See if visible BSSIDs are in our list of targets. If we
        find one, set the ALARM signal. If no matching BSSID is
        found, reset the ALARM signal.
        '''

        targets = [ubinascii.unhexlify(x) for x in self.targets]
        print('Start scanning t={}'.format(time.time()))
        nets = self.nic.scan()
        self.last_scan = nets
        for ssid, bssid, channel, rssi, authmode, hidden in nets:
            ssid = ssid.decode()
            _bssid = ubinascii.hexlify(bssid).decode()
            print('Checking ssid "{}" bssid "{}" channel {} rssi {}'.format(
                ssid, _bssid, channel, rssi
            ))
            if bssid in targets:
                print('Found ssid "{}" bssid "{}"'.format(ssid, _bssid))
                self.alarm.value(0)
                self.flag_alarm = True
                break
        else:
            self.alarm.value(1)
            self.flag_alarm = False

        print('Finished scanning t={}'.format(time.time()))
