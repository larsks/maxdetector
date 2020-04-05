import ifconfig
import json
import re
import select
import socket
import time

# Allow 'pydoc' to run
try:
    import gc
    import machine

    from machine import Timer
except ImportError:
    pass

try:
    from ucollections import namedtuple
except ImportError:
    from collections import namedtuple

buf = bytearray(1024)

EXTENSIONS = {
    "png": "image/png",
    "jpg": "image/jpeg",
    "gif": "image/gif",
    "html": "text/html",
    "txt": "text/plain",
    "ico": "image/x-icon",
    "css": "text/css",
    "js": "application/javascript",
}

STATUS_MESSAGE = {
    200: "OK",
    201: "CREATED",
    202: "ACCEPTED",
    204: "NO CONTENT",
    300: "MULTIPLE CHOICES",
    301: "MOVED PERMANENTLY",
    302: "FOUND",
    303: "SEE OTHER",
    304: "NOT MODIFIED",
    400: "BAD REQUEST",
    401: "UNAUTHORIZED",
    403: "FORBIDDEN",
    404: "NOT FOUND",
    405: "METHOD NOT ALLOWED",
    408: "REQUEST TIMEOUT",
    410: "GONE",
    500: "INTERNAL SERVER ERROR",
    501: "NOT IMPLEMENTED",
    502: "BAD GATEWAY",
    503: "SERVICE UNAVAILABLE",
}

Request = namedtuple("Request", ["method", "path", "version", "params"])
Response = namedtuple("Response", ["status_code", "content_type", "content"])


def parse_qs(qs):
    '''Convert a query string into a dictionary.'''
    return dict(x.split("=") for x in qs.split("&"))


def map_content_type(filename):
    '''Map a filename to a content type'''
    try:
        ext = filename.split(".")[-1].lower()
    except IndexError:
        ext = None

    return EXTENSIONS.get(ext, "application/octet-stream")


class BaseServer(object):
    def __init__(self, port=80, poll_interval=1000):
        self.port = port
        self.poll_interval = poll_interval
        self.routes = []
        self.running = False

    def register(self, path, handler, method="GET"):
        '''Associate a handler function with a route'''

        self.routes.append(
            {
                "path": path,
                "re": re.compile(path),
                "handler": handler,
                "method": method,
            }
        )

    def lookup_route(self, req):
        '''Find a registered route to handle the given request'''

        for route in self.routes:
            if route["method"] != req.method:
                continue

            match = route["re"].match(req.path)
            if match:
                print(
                    "method {} path {} matched {}".format(
                        req.method, req.path, route["path"],
                    )
                )
                break
        else:
            route = None
            match = None

        return route, match

    def handle_request(self, client, req):
        '''Handle a client request and return a Response'''

        route, match = self.lookup_route(req)
        if route is None:
            raise KeyError("No handler for {}\n".format(req.path))

        res = route["handler"](client, req, match)
        if not isinstance(res, Response):
            res = Response(200, None, res)

        return res

    def send_response(self, client, res, req):
        '''Send a response to the client'''

        nb = client.write(
            "HTTP/1.1 {} {}\r\n".format(
                res.status_code, STATUS_MESSAGE.get(res.status_code, "UNKNOWN")
            )
        )

        if isinstance(res.content, (dict, list)):
            nb += client.write(
                "Content-type: {}\r\n\r\n".format(
                    res.content_type or "application/json"
                )
            )
            nb += client.write(json.dumps(res.content))
        elif res.content is None:
            pass
        elif hasattr(res.content, "read"):
            nb += client.write(
                "Content-type: {}\r\n\r\n".format(res.content_type or "text/html")
            )
            nb += self.send_file(client, res.content)
        else:
            nb += client.write(
                "Content-type: {}\r\n\r\n".format(res.content_type or "text/html")
            )
            nb += client.write(res.content)

        return nb

    def send_file(self, client, fd):
        '''Send content from a file to the given client'''

        size = 0
        while True:
            nb = fd.readinto(buf)
            size += nb
            if nb == 0:
                break
            client.write(buf[:nb])

        fd.close()
        return size

    def read_request(self, client, addr):
        '''Read a request from the client and return a Request object'''

        state = 0
        clen = None
        params = {}

        while True:
            if state == 0:
                # Read request line
                line = client.readline()
                method, path, version = line.decode().split()
                try:
                    path, qs = path.split('?', 1)
                    params.update(parse_qs(qs))
                except ValueError:
                    pass
                state = 1
            elif state == 1:
                # Read headers
                line = client.readline()

                if line and line != b"\r\n":
                    header, value = line.decode().split(": ", 1)
                    if header.lower() == "content-length":
                        clen = int(value.strip())
                else:
                    if method in ["GET", "DELETE"]:
                        break
                    elif method in ["PUT", "POST"]:
                        state = 2
                    else:
                        raise ValueError(method)
            elif state == 2:
                # Read request body
                content = client.read(clen)
                params.update(parse_qs(content.decode()))
                break

        return Request(method, path, version, params)

    def start(self):
        s = socket.socket()
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.bind(("", self.port))
        s.listen(5)
        self.sock = s
        self.running = True
        print('Starting server.')

        try:
            self.loop()
        finally:
            self.stop()

    def idle(self):
        pass

    def loop(self):
        s = self.sock

        poll = select.poll()
        poll.register(s, select.POLLIN)

        while True:
            events = poll.poll(self.poll_interval)

            self.idle()

            if not events:
                continue

            client, addr = s.accept()
            print("Client connected from {}.".format(addr[0]))

            try:
                req = self.read_request(client, addr)
                res = self.handle_request(client, req)
            except Exception as err:
                if isinstance(err, KeyError):
                    status_code = 404
                else:
                    status_code = 500

                print("ERROR: Failed handling request from {}: {}: {}"
                      .format(addr[0], type(err), err))
                res = Response(status_code, "text/html",
                               "An unexpected error has occurred: {}\n".format(err))

            try:
                size = self.send_response(client, res, req)
            except Exception as err:
                print("ERROR: Failed sending response to {}: {}".format(addr[0], err))
                size = 0

            print(
                '{} - - [{}] "{} {} {}" {} {}'.format(
                    addr[0],
                    time.time(),
                    req.method,
                    req.path,
                    req.version,
                    res.status_code,
                    size,
                )
            )

            print("Closing connection from {}".format(addr[0]))
            client.close()

    def stop(self):
        if self.sock is not None:
            print("Closing server socket.")
            self.sock.close()
        self.sock = None
        self.running = False


class Server(BaseServer):
    def __init__(self, mdo, port=80):
        super().__init__(port=port)

        self.mdo = mdo
        self.add_routes()

    def add_routes(self):
        '''Register HTTP route handlers'''

        self.register("/api/target$", self.api_list_targets, method="GET")
        self.register("/api/target$", self.api_add_target, method="POST")
        self.register("/api/target/([^/]*)$", self.api_delete_target, method="DELETE")
        self.register("/api/status$", self.api_status)
        self.register("/api/scan$", self.api_scan_status)
        self.register("/api/scan$", self.api_scan_control, method="POST")
        self.register("/api/scan/results?$", self.api_scan_results)
        self.register("/api/silent$", self.api_silent_status)
        self.register("/api/silent$", self.api_silent_control, method="POST")
        self.register("/api/memory$", self.api_memory)
        self.register("/api/wifi", self.api_wifi, method="POST")
        self.register("/api/reset", self.api_reset)
        self.register("/static/(.*)$", self.static_content)
        self.register("/$", self.index)

    def index(self, *args):
        '''Return web UI'''
        return Response(200, "text/html", open("ui.html"))

    def api_memory(self, client, req, match):
        '''Return heap statistics from gc module'''
        return {"free": gc.mem_free(), "allocated": gc.mem_alloc()}

    def api_list_targets(self, client, req, match):
        '''Return list of current configured targets'''
        return list(self.mdo.targets)

    def api_add_target(self, client, req, match):
        '''Add a BSSID to list of targets'''
        self.mdo.add_target(req.params["target"])
        return list(self.mdo.targets)

    def api_delete_target(self, client, req, match):
        '''Remove a BSSID from list of targets'''
        self.mdo.remove_target(match.group(1))
        return list(self.mdo.targets)

    def api_status(self, client, req, match):
        '''Return basic status information'''
        return {
            "alarm": self.mdo.flag_alarm,
            "running": self.mdo.flag_running,
            "silent": self.mdo.flag_silent,
        }

    def api_scan_status(self, client, req, match):
        '''Return current scan status'''
        return {
            'running': self.mdo.flag_running,
        }

    def api_scan_results(self, client, req, match):
        '''Return list of visible networks'''
        return self.mdo.scan_results

    def api_scan_control(self, client, req, match):
        '''Enable or disbale wifi scanning'''
        mode = req.params.get('scan')

        if mode in ['start', 'on']:
            self.mdo.start()
        elif mode in ['stop', 'off']:
            self.mdo.stop()
        else:
            raise ValueError('scan must be "on" or "off"')

        return {"running": self.mdo.flag_running}

    def api_silent_status(self, client, req, match):
        '''Return current silent mode setting'''
        return {
            'silent': self.mdo.flag_silent,
        }

    def api_silent_control(self, client, req, match):
        '''Enable or disable silent mode'''
        mode = req.params.get('silent')

        if mode in ['start', 'on']:
            self.mdo.silent_on()
        elif mode in ['stop', 'off']:
            self.mdo.silent_off()
        else:
            raise ValueError('silent must be "on" or "off"')

        return {"silent": self.mdo.flag_silent}

    def static_content(self, client, req, match):
        '''Serve a file from the static directory'''
        filename = match.group(1)
        content_type = map_content_type(filename)
        path = "/static/{}".format(filename)
        print("static", path)
        try:
            return Response(200, content_type, open(path))
        except OSError:
            raise KeyError("Not found.\n")

    def _wifi_post(self, ssid, password):
        '''Update wifi configuration

        This is run (via a timer) after the api_wifi method returns
        to actually implement the changes.
        '''
        print("api wifi post")
        ifconfig.set_credentials(
            ssid=ssid,
            password=password,
        )

        ifconfig.connect(wait=True)

    def api_wifi(self, client, req, match):
        '''Request change to wifi credentials configuration'''
        try:
            ssid = req.params["ssid"]
            password = req.params["password"]
        except KeyError:
            raise ValueError('Request must contain both '
                             '"ssid" and "password"')

        t = Timer(-1)
        t.init(period=1000, mode=Timer.ONE_SHOT,
               callback=lambda t: self._wifi_post(ssid, password))

        return Response(200, "text/html", "Reconfiguring wifi\n")

    def _reset_post(self):
        '''Reset the esp8266'''
        print("Resetting.")
        machine.reset()

    def api_reset(self, client, req, match):
        '''Request a reset'''
        t = Timer(-1)
        t.init(period=1000, mode=Timer.ONE_SHOT,
               callback=lambda t: self._reset_post())

        return Response(200, "text/html", "Resetting\n")
