import json
import re
import select
import socket

buf = bytearray(512)


def parse_qs(qs):
    return dict(x.split(b'=') for x in qs.split(b'&'))


class API(object):
    def api_list_targets(self, client, method, path, params, mo):
        return list(self.mdo.targets)

    def api_add_target(self, client, method, path, params, mo):
        self.mdo.targets.add(params[b'target'])
        return list(self.mdo.targets)

    def api_delete_target(self, client, method, path, params, mo):
        self.mdo.targets.remove(mo.group(1))
        return list(self.mdo.targets)

    def api_alarm_status(self, client, method, path, params, mo):
        return {'alarm': self.mdo.flag_alarm}

    def api_scan_results(self, client, method, path, params, mo):
        return self.mdo.last_scan

    def api_scan_status(self, client, method, path, params, mo):
        return {'running': self.mdo.flag_running}

    def api_scan_start(self, client, method, path, params, mo):
        self.mdo.start()
        return {'running': self.mdo.flag_running}

    def api_scan_stop(self, client, method, path, params, mo):
        self.mdo.stop()
        return {'running': self.mdo.flag_running}


class Server(API):
    def __init__(self, mdo, port=80):
        self.mdo = mdo
        self.routes = []

        s = socket.socket()
        s.bind(('', port))
        s.listen(1)
        self.s = s

        self.register(b'/api/target',
                      self.api_list_targets, method=b'GET')
        self.register(b'/api/target',
                      self.api_add_target, method=b'POST')
        self.register(b'/api/target/(.*)',
                      self.api_delete_target, method=b'DELETE')
        self.register(b'/api/alarm', self.api_alarm_status)
        self.register(b'/api/scan/results', self.api_scan_results)
        self.register(b'/api/scan/start', self.api_scan_start)
        self.register(b'/api/scan/stop', self.api_scan_stop)
        self.register(b'/api/scan', self.api_scan_status)
        self.register(b'/', self.index)

    def register(self, path, handler, method=b'GET'):
        self.routes.append({
            'path': path,
            'pattern': re.compile(path),
            'handler': handler,
            'method': method,
        })

    def route(self, client, method, path, params):
        print(method, path, params)
        for route in self.routes:
            print('check', route['path'], route['method'])
            if route['method'] != method:
                continue

            mo = route['pattern'].match(path)
            if mo:
                print(path, 'matched', route['path'], ':', mo.group(0))
                res = route['handler'](client, method, path, params, mo)
                break

        client.send('HTTP/1.1 200 OK\r\n')
        if isinstance(res, (dict, list)):
            client.send('Content-type: application/json\r\n\r\n')
            client.send(json.dumps(res))
        elif res is None:
            pass
        else:
            client.send('Content-type: text/html\r\n\r\n')
            client.send(res)
        client.send('\r\n')

    def index(self, client, *args):
        return 'index'

    def start(self):
        s = self.s
        poll = select.poll()
        poll.register(s, select.POLLIN)

        while True:
            events = poll.poll(1000)
            if not events:
                continue

            cl, addr = s.accept()
            print('client connected from', addr)
            state = 0
            clen = None
            params = None

            while True:
                if state == 0:
                    line = cl.readline()
                    state = 1
                    method, path, version = line.split()
                elif state == 1:
                    line = cl.readline()

                    if line and line != b'\r\n':
                        header, value = line.split(b': ', 1)
                        if header.lower() == b'content-length':
                            clen = int(value.strip())
                    else:
                        if method in [b'GET', b'DELETE']:
                            break
                        elif method in [b'PUT', b'POST']:
                            state = 2
                        else:
                            raise ValueError(method)
                elif state == 2:
                    content = cl.read(clen)
                    params = parse_qs(content)
                    break

            self.route(cl, method, path, params)

            print('closing connection')
            cl.close()

    def stop(self):
        self.s.close()
