# Shoes4

A SOCKS4 tunnel that relays data over a pool of HTTPS connections, to avoid traffic shaping networks that are hostile to long-lived connections.

## Usage

Run the server:
```sh
python -m shoes serve --port 4343
```

Run the client:
```sh
python -m shoes connect http://1.2.3.4:443/shoes
```

Configure your applications:
```
Protocol: SOCKS4
Address: 127.0.0.1
Port: 4343
```

