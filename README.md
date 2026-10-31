<p align="center">
  <img src="assets/banner.png" alt="xBench Banner" width="100%">
</p>

# Xray-Bench (xBench)

A cross-platform tool for testing, filtering, and ranking large lists of V2Ray/Xray proxy configs on Windows, Linux, and macOS. 

If you're just here for working proxies, grab the subscription links below. If you want to test your own lists, you can run the desktop app or CLI yourself.

---

## Live Subscription Links

**Speed-tested & ranked (fastest nodes):**
```text
https://raw.githubusercontent.com/pourih/xray-bench/refs/heads/main/results/nodes_speed.txt
```

**Connectivity-tested (larger pool of working nodes):**
```text
https://raw.githubusercontent.com/pourih/xray-bench/refs/heads/main/results/nodes_http.txt
```

### How these lists are filtered
Instead of just pinging a server and hoping it works, xBench runs configs through a two-stage pipeline using real `xray-core` instances:

1. **HTTP & Geo-Spoof Check (`nodes_http.txt`):** Tests actual HTTP connectivity through the tunnel. It also checks the real exit IP and scrapes Google to make sure the node isn't lying about its country or quietly routing traffic through restricted regions (like `IR` or `RU`).
2. **Speed Tournament (`nodes_speed.txt`):** Takes the working nodes and runs them through a multi-round Cloudflare download test. The slowest third gets dropped each round, and the fastest survivors are ranked by score.
3. **3-Strike Pruning:** Nodes are tracked in a local database. If a node fails three times in a row, it gets marked dead and dropped so broken configs don't clog up the list.

Surviving nodes are renamed with clean tags showing their rank, country flag, ISP, and score (e.g., `xBench-0001 | 🇩🇪 DE | Hetzner | 5pts`).

---

## Running It Yourself

Requires **Python 3.9+**. The tool automatically detects your OS and architecture (`Linux`, `Windows`, `macOS` on `x86_64` / `arm64`), downloads the matching official `xray-core` binary on first run, and configures appropriate permissions.

### Setup

```bash
git clone https://github.com/pourih/xray-bench.git
cd xray-bench
python3 -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install -r program/requirements.txt
```

### 1. Desktop GUI
You can launch the visual dashboard directly from the project root:

- **Linux / macOS:**
  ```bash
  ./run_gui.sh
  # or: python run_gui.py
  ```
- **Windows:**
  ```cmd
  python run_gui.py
  ```

From the app, you can:
- Run ping and speed tests and watch live progress.
- Search, filter, and copy working nodes by country, ISP, or protocol.
- Edit your subscription URLs, custom nodes, and blacklists directly.
- Tweak timeouts, concurrency, and dark/light themes without touching config files.

### 2. Command Line (CLI)
You can run CLI commands from the root folder with `run_cli.py` / `run_cli.sh` (or from inside `program/`):

```bash
# Check database statistics
python run_cli.py stats

# Stage 1: Test subscriptions for HTTP connectivity & geo-spoofing
python run_cli.py http-test --source subs

# Stage 2: Run the speed tournament on the survivors from Stage 1
python run_cli.py speed-test --source http-output
```

On Linux, you can also use `./run_cli.sh stats`.

**Useful CLI flags:**
- `--fast`: Skips the deeper Google check and uses shorter timeouts for quicker HTTP runs.
- `--limit 50`: Only tests the first *N* nodes.
- `--source file --input data/custom_nodes.txt`: Tests a local file instead of subscription URLs.
- `--push`: Automatically commits and pushes updated results to your GitHub repo.

---

## Configuration & Input Files

Configuration files live inside `program/` (mirrored at root for convenience):

- **`program/data/subscriptions.txt`**: Put your subscription URLs here (one per line).
- **`program/data/custom_nodes.txt`**: Paste raw proxy links (`vless://`, `vmess://`, `trojan://`, `ss://`, etc.) here.
- **`program/data/blacklist.txt`**: IPs, domains, or hashes you want to ignore.
- **`program/config.yaml`**: Adjust batch sizes, timeouts, blocked countries, and speed test rounds.
- **`program/.env`**: Copy `program/.env.example` to `program/.env` and add your `GITHUB_TOKEN` and `GITHUB_REPO` if you want to use the `--push` flag to auto-update your own GitHub repo.

---

## Dual-Boot & Cross-Platform Git Sync

This repository includes `.gitattributes` to normalize line endings (`LF`) across Windows and Linux, preventing unstaged newline diffs when switching between operating systems.

- **On Windows:** Edit, test, and push with `git push origin main`.
- **On Linux (Fedora):** Pull changes with `git pull --rebase` and run tests with `pytest program/tests`.

---

## License

MIT License
