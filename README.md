# maxdetector

This is the software part of a project that rings a bell whenever a specific WiFi hotspot comes online.  The software consists of two parts:

- `maxdetector.py` is [MicroPython][] code that runs on an ESP8266, scans
  for the target networks, and raises a signal when it founds a target
  BSSID.

- `src/maxdetector.cpp` is Arduino code (structured to compile with
  [Platformio][]) that watches for the signal from the ESP8266 and takes
  care of ringing a bell and implementing other UI elements.

[micropython]: https://micropython.org/
[platformio]: https://platformio.org/

## Building and installing the code

### Install the Micropython component

Use [ampy][] or a similar tool to upload the code to your ESP8266:

```
ampy -p /dev/ttyUSB2 put maxdetector.py
```

You will need to create a `main.py` file (and upload it to the the ESP8266)
that configures things to start a boot. For example:

```
import maxdetector

target_bssid = 'c0ffee123456'

m = maxdetector.Monitor([target_bssid])
m.start()
```

### Installing the Arduino component

After installing Platformio, just run:

```
pio run
```

Or to build and upload the code:

```
pio run -t upload
```

If you're Uno isn't on `/dev/ttyACM0` you will need to update the
`platformio.ini` file or specify a device path on the command line.

## Simulation

You can find a simulated version of the Arduino component [on Tinkercad][].

[on tinkercad]: https://www.tinkercad.com/things/cpRuevAoV5L-max-detector
