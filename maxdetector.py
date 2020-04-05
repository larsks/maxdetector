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
        self.targets_file = targets_file
        self.alarm = Pin(pin_alarm, Pin.OUT)
        self.ready = Pin(pin_ready, Pin.OUT)
        self.scan_period = scan_period
        self.scan_results = []

        # READY and ALARM are active low. Make sure they are
        # high when we start up.
        self.alarm.value(1)
        self.ready.value(1)

        # This flag is True if the scanning code is running
        self.flag_running = False

        # This flag is True when there is an active alarm
        self.flag_alarm = False

        # This flag is True when silent mode is active
        self.flag_silent = False

        self.t_scan = None
        self.nic = network.WLAN(network.STA_IF)

        if self.targets_file:
            self.load_targets()

        self.store_targets()

    def load_targets(self):
        '''Read list of targets from the targets file'''
        try:
            with open(self.targets_file) as fd:
                targets = json.load(fd)
                self.targets = set(targets)
        except OSError as err:
            print('ERROR: failed to load targets: {}'.format(err))

    def store_targets(self):
        '''Save list of targets to targets file'''
        with open(self.targets_file, 'w') as fd:
            json.dump(list(self.targets), fd)

    def add_target(self, target):
        '''Add a target and update targets file'''
        self.targets.add(target)
        self.store_targets()

    def remove_target(self, target):
        '''Remove a target and update targets file'''
        self.targets.remove(target)
        self.store_targets()

    def start(self):
        """Start the scanning task.

        Sets the READY signal and schedules the scan() task
        to run every self.scan_period seconds (10 by default).
        """

        print("Starting scan task...")
        if self.t_scan is None:
            self.t_scan = Timer(-1)
            self.t_scan.init(
                period=self.scan_period,
                mode=Timer.PERIODIC,
                callback=lambda t: self.scan(),
            )
        self.ready.value(0)
        self.flag_running = True
        print("Finished starting scan task.")

    def stop(self):
        """Stop the scanning task.

        Cancel the scanning task and reset the READY signal.
        """

        print("Stopping scan task...")
        if self.t_scan is not None:
            self.t_scan.deinit()
            self.t_scan = None
        self.ready.value(1)
        self.alarm.value(1)
        self.flag_running = False
        self.flag_alarm = False
        print("Finished stopping scan task.")

    def scan(self):
        """Scan for matching BSSIDS

        See if visible BSSIDs are in our list of targets. If we
        find one, set the ALARM signal. If no matching BSSID is
        found, reset the ALARM signal.
        """

        print("Start scanning t={}".format(time.time()))
        self.scan_results = []
        found = False

        nets = self.nic.scan()
        for ssid, bssid, channel, rssi, authmode, hidden in nets:
            ssid = ssid.decode()
            bssid = ubinascii.hexlify(bssid).decode()
            network = (ssid, bssid, channel, rssi, authmode, hidden)
            print(
                'Checking ssid "{}" bssid "{}" channel {} rssi {}'.format(
                    ssid, bssid, channel, rssi
                )
            )
            if bssid in self.targets:
                print('Found ssid "{}" bssid "{}"'.format(ssid, bssid))
                found = True
                self.scan_results.append((True, network))
            else:
                self.scan_results.append((False, network))

        if found:
            if not self.flag_silent:
                self.alarm.value(0)
            self.flag_alarm = True
        else:
            self.alarm.value(1)
            self.flag_alarm = False

        print("Finished scanning t={}".format(time.time()))

    def silent_on(self):
        '''Enable silent mode.

        When silent mode is enabled, do not raise the ALARM signal
        when an alarm is active.
        '''
        self.flag_silent = True

    def silent_off(self):
        '''Disable silent mode'''
        self.flag_silent = False
