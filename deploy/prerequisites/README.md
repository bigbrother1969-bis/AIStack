# Prerequisites shipped with AIStack (ADR-0023 § 4)

Compose projects for software AIStack uses but does not own. `install.sh`
copies the one asked for to `/srv/<name>/compose.yml`, writes its `.env`
(mode 0600) and starts it; each runs beside AIStack, as its own project.

| Project | Port on the host | What AIStack uses it for |
|---|---|---|
| `pocket-id` | 1411 (behind the reverse proxy, HTTPS) | signing in (OIDC, passkeys) |
| `gotify` | 8070 | the vigil's notifications |
| `syncthing` | 8384 (web), 22000/tcp+udp, 21027/udp | sync to devices (ADR-0022) |

Pocket ID follows its `v2` tag (its project publishes one per major
version); Gotify and Syncthing take the image the installation pulls.
Once installed, their updates go through the Dock like any service.
