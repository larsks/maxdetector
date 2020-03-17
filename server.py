import select
import socket

buf = bytearray(512)


def parse_qs(qs):
    return dict(x.split(b'=') for x in qs.split(b'&'))


class Server(object):
    def __init__(self, mdo, port=80):
        self.mdo = mdo

        s = socket.socket()
        s.bind(('', port))
        s.listen(1)
        self.s = s

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
            redirect = False

            while True:
                if state == 0:
                    line = cl.readline()
                    state = 1
                    verb, path, version = line.split()
                elif state == 1:
                    line = cl.readline()

                    if line and line != b'\r\n':
                        header, value = line.split(b': ', 1)
                        if header.lower() == b'content-length':
                            clen = int(value.strip())
                    else:
                        if verb == b'GET':
                            break
                        elif verb == b'POST':
                            state = 2
                        else:
                            raise ValueError(verb)
                elif state == 2:
                    content = cl.read(clen)
                    parms = parse_qs(content)
                    action = parms.get(b'action')
                    if action == b'Stop':
                        self.mdo.stop()
                    elif action == b'Start':
                        self.mdo.start()
                    redirect = True
                    break

            if redirect:
                cl.send('HTTP/1.1 303 See Other\r\n')
                cl.send('Location: /\r\n')
            else:
                cl.send('HTTP/1.1 200 OK\r\n')

            cl.send('Content-type: text/html\r\n')
            cl.send('\r\n')
            with open('ui.html') as fd:
                while True:
                    nb = fd.readinto(buf)
                    if nb == 0:
                        break
                    cl.send(bytes(buf[:nb]).format(
                        running=self.mdo.flag_running,
                        alarm=self.mdo.flag_alarm,
                    ))

            print('closing connection')
            cl.close()

    def stop(self):
        self.s.close()
