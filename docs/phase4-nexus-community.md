# Phase 4.0 - Community broadband experience

SkyCache Nexus already forms a multi-node fabric. **0.4** adds the services people expect from "local internet" without lying about commercial broadband.

## Features

| Service | API / CLI | Notes |
|---------|-----------|--------|
| Catalog search | `GET /api/search?q=`  |  `skycache search` | Local node library |
| Village boards | `/api/boards*` | school, clinic, emergency, farm... |
| Ratings | `/api/packages/{id}/rating` | Anonymous hashed token |
| License inventory | `/api/licenses`  |  `skycache licenses` | Operator compliance |
| Power map | `/api/nexus/power-map` | Peer SOC + solar prefer |
| Traffic monitor | `/api/nexus/traffic` | Priority queue view |
| Control plane | `/api/nexus/control*` | LoRa/ISM alerts stub |
| Delta plan | `POST /api/nexus/delta` | Fingerprint sync plan |
| Onboarding | `/api/onboarding` | First-visit coach |

## Privacy

- No third-party analytics  
- Ratings use a **hashed** local voter token, not real names  
- Boards are local store-and-forward only  

## Legal

Still: receive-only satellite, open content only, unlicensed mesh TX, honest non-Starlink language.
