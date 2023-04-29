'''


'''

import argparse
import logging

from . import client
from . import server

def parse_addr(addr):
  if ':' in addr:
    host, port = addr.split(':', 2)
    return host, int(port)
  else:
    return '0.0.0.0', int(addr)

def main(args):
  if args.command == 'serve':
    s = server.ShoesServer(args.bind)
    s.serve_forever()

  elif args.command == 'connect':
    c = client.ShoesClient(args.bind, args.host)
    c.run_listen()

  else:
    raise ValueError


if __name__ == '__main__':
  logging.basicConfig(level=logging.INFO)
  parser = argparse.ArgumentParser(
    formatter_class=argparse.RawDescriptionHelpFormatter, description=__doc__)
  parser.add_argument('command', choices=['serve', 'connect'])
  parser.add_argument('--bind', type=parse_addr, required=True)
  parser.add_argument('--host', type=parse_addr)
  args = parser.parse_args()

  try:
    main(args)
  except KeyboardInterrupt:
    pass