# Xray-Bench (xBench)

Proxy benchmarking engine and modern desktop GUI for filtering, testing, and ranking large lists of V2Ray configurations.

It ingests nodes from subscription links, local lists, or its internal SQLite cache, bundles them into batched `xray-core` instances, and validates them across two stages: **HTTP ping & Google geo-localization verification**, followed by an **elimination-based speed tournament**. Results are saved to `results/` and can be automatically published to GitHub.

---

### 🔗 Live Subscription Links

Download speed tested & ranked:
```text
https://raw.githubusercontent.com/pourih/xray-bench/refs/heads/main/results/nodes_speed.txt
```

HTTP connectivity tested & localized:
```text
https://raw.githubusercontent.com/pourih/xray-bench/refs/heads/main/results/nodes_http.txt
```

---

### 🖥️ Modern Desktop GUI (xBench)

Launch the full-featured desktop dashboard from the root directory with one command:

```bash
python run_gui.py
```

- **⚡ Real-Time Dashboard**: Live metric cards displaying active database nodes, alive ping pass rates, peak bandwidth, and 3-strike pruned nodes. Features an active in-flight testing indicator and a real-time event stream.
- **📋 Node Intelligence Explorer**: Browse and filter nodes by sequential tag (`xBench-0042`), country code (`DE`, `NL`), ISP, protocol, or host, with instant 1-click URI clipboard copying.
- **🌐 In-App Sources & Blacklist Editor**: Tabbed manager to edit `subscriptions.txt`, `custom_nodes.txt`, and `blacklist.txt` directly within the interface.
- **⚙️ Settings & Theme Engine**: Instant switching between **Dark Theme** and **Light Theme**, live tuning of concurrency, timeouts, banned country detection, and GitHub PAT credentials.
- **📜 Console Diagnostic Viewer**: Live colorized terminal feed for engine events, HTTP pings, and core output.

---

### ⚡ CLI Usage

For headless servers, automated scripts, or scheduled cron workflows, run the CLI from inside the `program/` directory:

```bash
cd program
```

#### Mode 1: HTTP Ping & Deep Geo Check
Fetches candidate nodes, verifies live TCP/TLS connectivity, resolves exit IPs, validates Google localization, and writes clean nodes to `results/nodes_http.txt`:

```bash
# Test all sources listed in subscriptions.txt
python -m src.cli.main http-test --source subs

# Fast mode (larger batch size, shorter timeout, bypasses Google HTML scrape)
python -m src.cli.main http-test --source subs --fast

# Test only the first 50 candidate nodes
python -m src.cli.main http-test --source subs --limit 50

# Test from a custom node file
python -m src.cli.main http-test --source file --input data/custom_nodes.txt

# Run benchmark and automatically commit & push results to GitHub
python -m src.cli.main http-test --source subs --push
```

#### Mode 2: Speed Tournament
Runs an elimination tournament downloading Cloudflare speed test chunks in structured rounds and writes the ranked survivors to `results/nodes_speed.txt`:

```bash
# Run tournament using the output from Mode 1
python -m src.cli.main speed-test --source http-output

# Run tournament against all active nodes currently in the SQLite DB
python -m src.cli.main speed-test --source db

# Run tournament from a custom file and push results to GitHub
python -m src.cli.main speed-test --source custom --input data/custom_nodes.txt --push
```

#### Check SQLite Database Statistics
```bash
python -m src.cli.main stats
```

---

### 🧠 Core Features & Architecture

- **Broad Protocol Support**: VMess, VLESS (Reality, WS, gRPC, TCP, HTTPUpgrade, XHTTP), Trojan, Shadowsocks (SIP002, 2022, legacy), SOCKS, and WireGuard.
- **Canonical Node Fingerprinting**: Hashes underlying connection parameters (ignoring `#remark` labels) and tracks performance persistently in SQLite (`program/data/nodes_cache.db`). If a subscription feed renames a node, its historical score and stats remain intact.
- **Deep Google & Geo-Spoof Detection**: Resolves the true exit IP via GeoIP and scrapes Google localization headers through the tunnel. When a node's GeoIP claims Germany but Google routes traffic to restricted countries (`IR`, `RU`), it is automatically disqualified.
- **Standardized Remark Format**: Renames surviving nodes with persistent sequential IDs, national flag emojis, mismatch indicators, ISP names, and cumulative tournament scores:
  ```text
  xBench-0001 | 🇩🇪 DE (or 🇳🇱 NL) | Hetzner | 5pts
  ```
- **Elimination Tournament & 3-Strike Pruning**: Evaluates download bandwidth in rounds (max 4 concurrent connections to avoid saturating local bandwidth). Each round awards surviving nodes `+1` point; the slowest third is eliminated per round. Nodes that fail Round 1 three consecutive times are marked dead and skipped in future tests.
- **Batched In-Memory Core**: Spawns clean, multi-inbound `xray-core` processes (typically 40–50 nodes per instance) with randomized high-port allocations and zero orphaned child processes.

---

### 📦 Setup & Installation

Requires **Python 3.9+**. `xray-core` is automatically downloaded for your operating system and architecture (Windows, Linux, macOS, and Android Termux) into `program/bin/` on first launch.

```bash
git clone https://github.com/pourih/xray-bench.git
cd xray-bench/program
pip install -r requirements.txt
```

#### Source Feeds
- Add subscription links (one per line) to `program/data/subscriptions.txt`.
- Add manual proxy URIs to `program/data/custom_nodes.txt`.
- Drop problematic IPs, domains, or hashes into `program/data/blacklist.txt`.

#### Optional: GitHub Auto-Push Sync
To enable automated `--push` publishing via the GitHub API:
```bash
cp .env.example .env
```
Fill in your `GITHUB_TOKEN`, `GITHUB_REPO` (`owner/repo`), and `GITHUB_BRANCH` in `.env`.

---

### ⚙️ Configuration

Tune concurrency, batch sizing, timeouts, and blocked regions in `program/config.yaml`:

```yaml
general:
  node_prefix: "xBench"
  log_level: "INFO"
  theme: "dark"

xray:
  batch_size: 40
  startup_timeout_sec: 5.0
  listen_host: "127.0.0.1"

geo:
  cache_ttl_days: 14
  blocked_google_countries:
    - "IR"
    - "RU"
  check_google_country: true
  google_check_url: "https://www.youtube.com/sw.js_data"

http_test:
  test_url: "http://cp.cloudflare.com/generate_204"
  timeout_sec: 6.0
  concurrency: 12

speed_test:
  payload_url: "https://speed.cloudflare.com/__down?bytes=5000000"
  timeout_sec: 10.0
  concurrency: 4
  min_speed_mbps: 0.1
  bottom_third_divisor: 3
  max_consecutive_zero_runs: 3
```

---

### 🧪 Unit Tests

Run the comprehensive test suite verifying URI parsing, fingerprint invariance, Google localization, tournament tiers, and config generation:

```bash
cd program
pytest tests -v
```

---

### 📄 License

Distributed under the [MIT License](LICENSE).
