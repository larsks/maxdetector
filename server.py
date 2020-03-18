import gc
import json
import re
import select
import socket
import time

from ucollections import namedtuple

buf = bytearray(1024)
extensions = {
    'png': 'image/png',
    'jpg': 'image/jpeg',
    'gif': 'image/gif',
    'html': 'text/html',
    'htm': 'text/html',
    'txt': 'text/plain',
    'md': 'text/plain',
    'tiff': 'image/tiff',
    'tif': 'image/tiff',
    'ico': 'image/x-icon',
    'css': 'text/css',
    'js': 'application/javascript',
}

Request = namedtuple('Request', ['method', 'path', 'version', 'params'])
Response = namedtuple('Response', ['status_code', 'content_type', 'content'])


def parse_qs(qs):
    return dict(x.split('=') for x in qs.split('&'))


def map_content_type(filename):
    try:
        ext = filename.split('.')[-1].lower()
    except IndexError:
        ext = None

    return extensions.get(ext, 'application/octet-stream')


class API(object):
    def api_memory(self, client, req, match):
        return {'free': gc.mem_free(),
                'allocated': gc.mem_alloc()}

    def api_list_targets(self, client, req, match):
        return list(self.mdo.targets)

    def api_add_target(self, client, req, match):
        self.mdo.targets.add(req.params['target'])
        return list(self.mdo.targets)

    def api_delete_target(self, client, req, match):
        self.mdo.targets.remove(match.group(1))
        return list(self.mdo.targets)

    def api_status(self, client, req, match):
        return {
            'alarm': self.mdo.flag_alarm,
            'running': self.mdo.flag_running,
        }

    def api_alarm_status(self, client, req, match):
        return {'alarm': self.mdo.flag_alarm}

    def api_scan_results(self, client, req, match):
        return self.mdo.last_scan

    def api_scan_status(self, client, req, match):
        return {'running': self.mdo.flag_running}

    def api_scan_start(self, client, req, match):
        self.mdo.start()
        return {'running': self.mdo.flag_running}

    def api_scan_stop(self, client, req, match):
        self.mdo.stop()
        return {'running': self.mdo.flag_running}

    def static_content(self, client, req, match):
        filename = match.group(1)
        content_type = map_content_type(filename)
        path = '/static/{}'.format(filename)
        print('static', path)
        return Response('200 OK', content_type, open(path))


class Server(API):
    def __init__(self, mdo, port=80):
        self.mdo = mdo
        self.routes = []

        s = socket.socket()
        s.bind(('', port))
        s.listen(5)
        self.s = s

        self.register('/api/target',
                      self.api_list_targets, method='GET')
        self.register('/api/target',
                      self.api_add_target, method='POST')
        self.register('/api/target/([^/]*)',
                      self.api_delete_target, method='DELETE')
        self.register('/api/status', self.api_status)
        self.register('/api/alarm', self.api_alarm_status)
        self.register('/api/scan/results', self.api_scan_results)
        self.register('/api/scan/start', self.api_scan_start)
        self.register('/api/scan/stop', self.api_scan_stop)
        self.register('/api/scan', self.api_scan_status)
        self.register('/api/memory', self.api_memory)
        self.register('/static/(.*)', self.static_content)
        self.register('/$', self.index)

    def register(self, path, handler, method='GET'):
        self.routes.append({
            'path': path,
            're': re.compile(path),
            'handler': handler,
            'method': method,
        })

    def lookup_route(self, req):
        for route in self.routes:
            if route['method'] != req.method:
                continue

            match = route['re'].match(req.path)
            if match:
                print('method {} path {} matched {}'.format(
                    req.method, req.path, route['path'],
                ))
                break
        else:
            route = None
            match = None

        return route, match

    def handle_request(self, client, req):
        route, match = self.lookup_route(req)
        if route is None:
            return Response(404, 'text/plain',
                            'No handler for {}'.format(req.path))

        res = route['handler'](client, req, match)
        if not isinstance(res, Response):
            res = Response('200 OK', None, res)

        return res

    def handle_response(self, client, res, req):
        client.write('HTTP/1.1 {}\r\n'.format(res.status_code))

        if isinstance(res.content, (dict, list)):
            client.write('Content-type: {}\r\n\r\n'.format(
                res.content_type or 'application/json'
            ))
            client.write(json.dumps(res.content))
        elif res.content is None:
            pass
        elif hasattr(res.content, 'read'):
            client.write('Content-type: {}\r\n\r\n'.format(
                res.content_type or 'text/html'
            ))
            self.send_file(client, res.content)
        else:
            client.write('Content-type: {}\r\n\r\n'.format(
                res.content_type or 'text/html'
            ))
            client.write(res.content)

    def send_file(self, client, fd):
        size = 0
        while True:
            nb = fd.readinto(buf)
            size += nb
            if nb == 0:
                break
            client.write(buf[:nb])

        fd.close()

        print('sent {} bytes'.format(size))

    def index(self, client, *args):
        return open('ui.html')

    def read_request(self, client, addr):
        state = 0
        clen = None
        params = None

        while True:
            if state == 0:
                # Read request line
                line = client.readline()
                method, path, version = line.decode().split()
                state = 1
            elif state == 1:
                # Read headers
                line = client.readline()

                if line and line != b'\r\n':
                    header, value = line.decode().split(': ', 1)
                    if header.lower() == 'content-length':
                        clen = int(value.strip())
                else:
                    if method in ['GET', 'DELETE']:
                        break
                    elif method in ['PUT', 'POST']:
                        state = 2
                    else:
                        raise ValueError(method)
            elif state == 2:
                # Read request body
                content = client.read(clen)
                params = parse_qs(content.decode())
                break

        return Request(method, path, version, params)

    def start(self):
        s = self.s
        poll = select.poll()
        poll.register(s, select.POLLIN)

        while True:
            events = poll.poll(1000)
            if not events:
                continue

            client, addr = s.accept()
            print('DEBUG: client connected from', addr)

            req = self.read_request(client, addr)
            print('{} - - [{}] "{} {} {}"'.format(
                addr[0], time.time(), req.method, req.path, req.version))
            res = self.handle_request(client, req)
            self.handle_response(client, res, req)

            print('closing connection')
            client.close()

    def stop(self):
        self.s.close()
