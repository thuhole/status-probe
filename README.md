# status-probe

A simple bot for monitoring your web services status and automatically publish issues on [cState](https://github.com/cstate/cstate).

# Getting Started

```
git clone https://github.com/thuhole/status-probe
cd status-probe
pip3 install -r requirements.txt
```

# Configuation

Copy `config.json.example` to `config.json`, then edit:

- `token`: GitHub Personal Token
- `repo`: Your forked [cstate/example](https://github.com/cstate/example) repo.
- `tasks`: Websites you wanna monitor
  - `Category`: `Reference` or _Whatever you like_
  - `Name`: The system name in your [cState config.yml](https://github.com/cstate/example/blob/master/config.yml)
  - `URL`: The HTTP GET url you want to monitor *or* the hostname or IP address to check
  - `Code`: The expecting status code *or* the port you want to check
  - `Scheme`: Either HTTP or TCP. Note that the TCP scheme expects `URL` to be an IP or hostname, and `Code` to be a port. View the `congfig.json.example` for more info

## What's `Reference` for?

`Reference` websites are assumed to have 100% uptime. If any `Reference` website is offline, your services' offline won't be counted. You can use popular websites like Google as `Reference` websites.
