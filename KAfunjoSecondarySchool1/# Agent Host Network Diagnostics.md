# Agent Host Network Diagnostics

## Local OS Proxy Configuration (@vscode/os-proxy-resolver)

- Proxy environment: (none)
- Auto-detect: true
- DHCP WPAD: not-found
- DNS WPAD: not-found
- Configured PAC: unconfigured
- PAC: (none)
- Static rules: (none)
- Platform settings: Windows, proxy=(none), bypass=(none)

- Connections: 1 (1 local, 0 remote)

Connectivity probes run inside each agent host process (local or remote), so results reflect the environment the Copilot SDK actually connects from.

## Local agent host

- Agent host version: 1.145.2
- OS: win32 (x64)
- Account: mavumbantiba
- Proxy settings: (none)
- Proxy environment: (none)

### GitHub API

- URL: https://api.github.com
- DNS IPv4: 140.82.121.5 (8 ms)
- DNS IPv6: error (213 ms): getaddrinfo ENOTFOUND api.github.com
- Proxy: None
- Local OS proxy (@vscode/os-proxy-resolver): direct
- Reachability: ✗ Fetch timeout: 10000ms (10068 ms)

### Copilot API (CAPI)

- URL: https://api.individual.githubcopilot.com/_ping
- DNS IPv4: 140.82.112.22 (12 ms)
- DNS IPv6: error (287 ms): getaddrinfo ENOTFOUND api.individual.githubcopilot.com
- Proxy: None
- Local OS proxy (@vscode/os-proxy-resolver): direct
- Reachability: ✓ 200 via direct (2127 ms)

