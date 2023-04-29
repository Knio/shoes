import dataclasses
import enum
import logging
import queue
import socket
import struct
import threading

import requests

LOG = logging.getLogger(__name__)


@dataclasses.dataclass
class Ipv4:
  FORMAT = '!BBBB'
  FORMAT_LEN = struct.calcsize(FORMAT)
  a: int
  b: int
  c: int
  d: int

  def __bytes__(self):
    return struct.pack(self.FORMAT, self.a, self.b, self.c, self.d)

  def __str__(self):
    return f'{self.a}.{self.b}.{self.c}.{self.d}'

  @classmethod
  def from_bytes(cls, bytes):
    (a, b, c, d) = struct.unpack(cls.FORMAT, bytes[:cls.FORMAT_LEN])
    return cls(a, b, c, d)

  @classmethod
  def from_str(cls, s):
    return cls(*map(int, s.split('.')))

  @classmethod
  def from_int(cls, i):
    return cls.from_bytes(struct.pack('!I', (i,)))

  def to_int(self):
    return (self.a << 24) | (self.b << 16) | (self.c << 8) | (self.d)


@dataclasses.dataclass
class Socks4Request:
  FORMAT = '!BBH4s'
  FORMAT_LEN = struct.calcsize(FORMAT)

  ver:      int
  cmd:      int
  dstport:  int
  dstip:    bytes
  id:       bytes

  class Cmd(enum.IntEnum):
    CONNECT = 1
    BIND    = 2

  @classmethod
  def from_bytes(cls, bytes):
    (ver, cmd, dstport, dstip) = \
      struct.unpack(cls.FORMAT, bytes[:cls.FORMAT_LEN])
    id = bytes[cls.FORMAT_LEN:]
    return cls(
      ver=ver,
      cmd=cmd,
      dstport=dstport,
      dstip=dstip,
      id=id,
    )


@dataclasses.dataclass
class Socks4Reply:
  FORMAT = '!BBH4s'
  FORMAT_LEN = struct.calcsize(FORMAT)

  ver:      int
  rep:      int
  dstport:  int
  dstip:    bytes

  class Rep(enum.IntEnum):
    GRANTED = 0x5A
    FAILED  = 0x5B

  def __bytes__(self):
    return struct.pack(
      self.FORMAT, self.ver, self.rep, self.dstport, self.dstip)


class SocksClient:
  def __init__(self, shoes, addr, sock):
    self.shoes = shoes
    self.addr = addr
    self.sock = sock
    self.ri = 0
    self.wi = 0
    self.readq = queue.PriorityQueue()
    self.sendq = queue.PriorityQueue()

  def start(self):
    self.sock.setblock(True)
    self.sock.settimeout(1)
    self.running = True
    self.read_thread = threading.Thread(target=self.run_read)
    self.read_thread.daemon = True
    self.read_thread.start()
    self.write_thread = threading.Thread(target=self.run_write)
    self.write_thread.daemon = True
    self.write_thread.start()

  def stop(self):
    self.running = False
    self.shoes.close(self)
    self.read_thread.join()
    self.write_thread.join()

  def run_read(self):
    req_data = self.sock.read(1024)
    req = Socks4Request.from_bytes(req_data)
    if req.cmd == Socks4Request.Cmd.CONNECT:
      self.shoes_id = self.shoes.connect(self, req.dstip, req.dstport)
      res = Socks4Reply(
        ver=0, rep=Socks4Reply.Rep.GRANTED, dstport=self.shoes_id, dstip=self.addr
      )
      res_bytes = bytes(res)
      self.sendq.append((-len(res_bytes), res_bytes))
    else:
      self.running = False
      raise NotImplementedError(repr(req.cmd))

    self.ri = 0
    self.wi = 0
    while self.running:
      data = self.sock.read(128 * 1024)
      self.shoes.queue((self.shoes_id, self.ri), data)
      self.ri += len(data)

  def run_write(self):
    while self.running:
      wi, data = self.sendq.get()
      if wi == self.wi:
        try:
          n = self.sock.send(data)
        except socket.error:
          LOG.exception('failed to send data')
          self.stop()
      else:
        n = 0
      self.wi += n
      if n != wi:
        self.sendq.put((wi + n, data[n:]))


class ShoesClient:
  def __init__(self, listen_addr, server_addr):
    self.listen_addr = listen_addr
    self.server_addr = server_addr
    self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    self.sock.bind(self.listen_addr)
    self.sock.setblocking(True)
    self.sock.settimeout(1)
    self.sock.listen(64)
    self.clients = []
    self.running = False

  def start(self):
    self.listen_thread = threading.Thread(target=self.run_listen)
    self.listen_thread.daemon = True

  def stop(self):
    self.running = False
    self.listen_thread.join()

  def wait(self):
    self.listen_thread.join()

  def run_listen(self):
    self.running = True
    while self.running:
      try:
        conn, addr = self.sock.accept()
        client = SocksClient(self, addr, conn)
        client.start()
      except socket.timeout:
        pass

  def connect(self, client, dstip, dstport):
    raise NotImplementedError
