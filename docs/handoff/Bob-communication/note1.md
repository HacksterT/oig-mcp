# Note 1: check the VM's tools

Before Phase 0, check the tools on this VM and report the results to Troy as a short table. Do not install anything yet, and do not read or create a `.env` file.

Run these from the `oig-mcp` folder, and report each version or "missing":

| Command | Expect |
|---|---|
| `git log --oneline -1` | The latest commit on `main`, which adds this note |
| `git branch --show-current` | `ibm/deploy` |
| `podman --version` and `docker --version` | At least one |
| `python3 --version` | Any 3.x. `uv` fetches 3.11 itself |
| `uv --version` | Present, or say how you would install it |
| `ibmcloud version`, then `ibmcloud plugin list` | Needed tomorrow, not today |
| `orchestrate --version` | Needed tomorrow, not today |
| `uname -m` | `x86_64` |
| `df -h .` | Free disk space. The build needs about 2 GB |

Then test the network, without logging in anywhere:

```bash
curl -sI https://pypi.org/simple/ | head -1
curl -sI https://registry-1.docker.io/v2/ | head -1
curl -sI https://github.com | head -1
```

Any HTTP status line means the site is reachable; Docker Hub normally answers `401`. A timeout or "could not resolve host" means it is blocked.

For anything missing, say how you would install it, then wait for Troy's go-ahead. Do not start Phase 0 until Troy says so.
