import esp
import gc
import ifconfig
import maxdetector
import server

ifconfig.connect(wait=True)

esp.osdebug(None)
gc.collect()

m = maxdetector.Monitor()
m.start()

s = server.Server(m)
s.start()
