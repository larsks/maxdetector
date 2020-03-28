# maxdetector

This is the software part of a project that rings a bell whenever a specific
WiFi hotspot comes online.  The software consists of several components:

- `maxdetector.py` is [MicroPython][] code that runs on an ESP8266, scans
  for the target networks, and raises a signal when it founds a target
  BSSID.

- `server.py` is [MicroPython][] code that provides a web interface for 
  managing maxdetector from a browser.

- `static/md.js` is the Javascript responsible for the dynamic web ui.

- `src/maxdetector.cpp` is Arduino code (structured to compile with
  [Platformio][]) that watches for the signal from the ESP8266 and takes
  care of ringing a bell and implementing other physical UI elements.

[micropython]: https://micropython.org/
[platformio]: https://platformio.org/

## Building and installing the code

### Install the Micropython component

Use [ampy][] or a similar tool ([mpfshell][], [rshell][], etc) to upload
the code to your ESP8266. You will need to upload the following files
(preserving the directory structure):

[ampy]: https://github.com/scientifichackers/ampy
[mpfshell]: https://github.com/wendlers/mpfshell
[rshell]: https://github.com/dhylands/rshell

- `maxdetector.mpy`
- `server.mpy`
- `ui.html`
- `static/md.js`
- `static/style.css`
- `static/max.jpg`

You can configure wifi credentials by creating a file `wifi.json` with
the SSID and password for your network. For example:

```
{
  "ssid": "mynetwork",
  "password": "supersecret"
}
```

You can configure target networks using the API, or create a file
named `targets.json` on your device with a list of BSSIDs to monitor.
E.g:

```
[
  "c0ffee123456",
  "cafe87654321",
]
```

You can also manage targetes via the web interface.

### Installing the Arduino component

After installing [Platformio][], just run:

```
pio run
```

Or to build and upload the code:

```
pio run -t upload
```

If your Uno isn't on `/dev/ttyACM0` you will need to update the
`platformio.ini` file or specify a device path on the command line.

## API

maxdetector has a simple HTTP API:

- `GET /api/alarm`
- `GET /api/memory`
- `GET /api/scan`
- `GET /api/scan/result`
- `GET /api/scan/start`
- `GET /api/scan/stop`
- `GET /api/status`
- `GET /api/target`
- `POST /api/target`
- `DELETE /api/target/<bssid>`

## Simulation

You can find a simulated version of the Arduino component [on Tinkercad][].

[on tinkercad]: https://www.tinkercad.com/things/cpRuevAoV5L-max-detector
