# Security policy

## Supported versions

| Version | Supported |
|---------|-----------|
| 0.1.x (alpha) | Best-effort |

## Reporting

Please report security issues privately to the maintainers (open a confidential security advisory on the GitHub repository when published, or contact the listed maintainers).

Do **not** file public issues for:

- Admin PIN bypass  
- Path traversal in content serving  
- Dependency RCE  

## Non-goals / out of scope

- Decrypting third-party commercial satellite services  
- Requests to add unauthorized transmit capability  

## Deployment advice

- Change `SKYCACHE_ADMIN_PIN` from the default.  
- Run as a dedicated system user.  
- Keep the hub on an isolated LAN (no automatic internet bridging).  
- Update base OS packages regularly.  
