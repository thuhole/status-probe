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
- `tasks`:
  - `Category`: `Reference` or _Whatever you like_. Reference
  - `Name`: the system name in your [cState config.yml](https://github.com/cstate/example/blob/master/config.yml)
  - `URL`: the HTTP GET url you want to monitor
  - `Code`: the expecting status code

## What's `Reference` for?
`Reference` tasks are assumed to have 100% uptime. If `Reference` task is offline, your services' offline won't be counted. You can use popular websites like Google.
