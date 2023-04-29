
import http.server
import logging
import socket
import threading


LOG = logging.getLogger(__name__)


class SocksServer(http.server.BaseHTTPRequestHandler):
  def __init__(self, request, client_address, server) -> None:
    self.request = request
    self.client_address = client_address
    self.server = server
    self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

  def do_GET(self):
    LOG.info(f'GET {self.path}')


class ShoesServer(http.server.ThreadingHTTPServer):
  def __init__(self, addr) -> None:
    super().__init__(addr, SocksServer)


  def start(self):
    self.thread = threading.Thread(target=self.serve_forever)
    self.thread.daemon = True
    self.thread.start()

  def stop(self):
    self.shutdown()

  def wait(self):
    self.thread.join()

