# Village multi-node fabric - ops notes

See also: `docs/mesh-deployment.md`, `docs/village-nexus-playbook.md`.

## systemd

1. Install package under `/opt/skycache`.
2. Use `deploy/skycache.service` or `deploy/nexus-mesh.service` as a template.
3. Set unique `SKYCACHE_NODE_ID` per machine.
4. Start with `mesh_mode=sim` until batman/hostapd is proven, then switch.

## batman-adv (summary)

- Prefer OpenWrt mesh APs for radio complexity; Pis run SkyCache + wired/wireless backhaul when possible.
- Same IP plan: `10.42.0.0/24`, unique host per node.
- Portal port 8080 on each node (or reverse-proxy on edge AP).

## QoS hint (optional)

On a Linux gateway node, mark Emergency/Health HTTP paths with higher priority via nftables/tc - advanced; not required for MVP. Application-level prioritizer already protects disk and DTN queues.

## Solar

- Prefer charging midday; ECO mode disables live SDR when SOC is low.
- Prefer solar-powered peers in mesh route preference (software).
