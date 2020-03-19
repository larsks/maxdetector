import json
import network
import time
import ubinascii

from machine import Pin
from machine import Timer

DEFAULT_PIN_READY = 4  # D2
DEFAULT_PIN_ALARM = 5  # D1
DEFAULT_SCAN_PERIOD = 10000
DEFAULT_TARGETS_FILE = "targets.json"


class Monitor(object):
    def __init__(
        self,
        targets=None,
        targets_file=DEFAULT_TARGETS_FILE,
        pin_ready=DEFAULT_PIN_READY,
        pin_alarm=DEFAULT_PIN_ALARM,
        scan_period=DEFAULT_SCAN_PERIOD,
    ):

        self.targets = set(targets or [])
        self.active_targets = []
        self.targets_file = targets_file
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

        if self.targets_file:
            self.load_targets()

        self.store_targets()

    def load_targets(self):
        try:
            with open(self.targets_file) as fd:
                targets = json.load(fd)
                self.targets = set(targets)
        except OSError as err:
            print('ERROR: failed to load targets: {}'.format(err))

    def store_targets(self):
        with open(self.targets_file, 'w') as fd:
            json.dump(list(self.targets), fd)

    def add_target(self, target):
        self.targets.add(target)
        self.store_targets()

    def remove_target(self, target):
        self.targets.remove(target)
        self.store_targets()

    def start(self):
        """Start the scanning task.

        Sets the READY signal and schedules the scan() task
        to run every self.scan_period seconds (10 by default).
        """

        print("Starting...")
        if self.t_scan is None:
            self.t_scan = Timer(-1)
            self.t_scan.init(
                period=self.scan_period,
                mode=Timer.PERIODIC,
                callback=lambda t: self.scan(),
            )
        self.ready.value(0)
        self.flag_running = True
        print("Started.")

    def stop(self):
        """Stop the scanning task.

        Cancel the scanning task and reset the READY signal.
        """

        print("Stopping...")
        if self.t_scan is not None:
            self.t_scan.deinit()
            self.t_scan = None
        self.ready.value(1)
        self.flag_running = False
        self.flag_alarm = False
        self.active_targets = []
        print("Stopped.")

    def scan(self):
        """Scan for matching BSSIDS

        See if visible BSSIDs are in our list of targets. If we
        find one, set the ALARM signal. If no matching BSSID is
        found, reset the ALARM signal.
        """

        print("Start scanning t={}".format(time.time()))
        nets = self.nic.scan()
        self.last_scan = []
        found = False
        self.active_targets = []
        for ssid, bssid, channel, rssi, authmode, hidden in nets:
            ssid = ssid.decode()
            bssid = ubinascii.hexlify(bssid).decode()
            self.last_scan.append((ssid, bssid, channel, rssi))
            print(
                'Checking ssid "{}" bssid "{}" channel {} rssi {}'.format(
                    ssid, bssid, channel, rssi
                )
            )
            if bssid in self.targets:
                print('Found ssid "{}" bssid "{}"'.format(ssid, bssid))
                found = True
                self.active_targets.append((ssid, bssid, channel,
                                            rssi, authmode, hidden))

        if found:
            self.alarm.value(0)
            self.flag_alarm = True
        else:
            self.alarm.value(1)
            self.flag_alarm = False

        print("Finished scanning t={}".format(time.time()))
