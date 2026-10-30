# Xray-Bench (xBench)

A tool for testing, filtering, and ranking large lists of V2Ray proxies.

It pulls configs from subscription links or local files, compiles them into batched `xray-core` configs (40 nodes per process by default), and runs them through two stages: an initial HTTP ping/geo-check and an elimination speed tournament. Results are saved to `results/` and can be auto-pushed back to GitHub.

### What it does

- **Protocols:** VMess, VLESS (Reality, WS, gRPC, TCP, HTTPUpgrade, XHTTP), Trojan, Shadowsocks, SOCKS, and WireGuard.
- **Fingerprinting:** Hashes the actual connection details (ignoring the `#remark` tag) and stores stats in SQLite (`program/data/nodes_cache.db`). If a provider renames a node, it keeps its history and score.
- **Geo & Spoof Checking:** Checks the exit IP against GeoIP and also scrapes the language tag from Google's homepage through the proxy. Sometimes an IP says it's in Germany on GeoIP, but Google routes it to Iran or Russia. If either check hits `IR` or `RU`, the node is dropped.
- **Tournament Speed Test:** Instead of running one massive speed test once, Mode 2 downloads a Cloudflare payload in rounds (max 4 at a time so your local connection doesn't choke). Each round gives surviving nodes +1 point in the database and drops the slowest third until one node is left.
- **Auto-pruning:** Nodes that fail Round 1 three times in a row get marked dead in the DB and skipped on future runs.
- **Formatting:** Renames working nodes with sequential IDs, country flags (including mismatches), ISP, and total points, e.g., `xBench-0001 | 🇩🇪 DE (or 🇳🇱 NL) | Hetzner | 5pts`.

### Setup

Requires Python 3.9+. It will automatically download the right `xray-core` binary for your OS/arch (works on Windows, Linux, and Android Termux) into `program/bin/`.

```bash
cd program
pip install -r requirements.txt
```

Put your subscription URLs in `program/data/subscriptions.txt` (one per line), or raw proxy URIs in `program/data/custom_nodes.txt`. You can also drop bad IPs, domains, or hashes into `program/data/blacklist.txt`.

If you want to use the `--push` flag to commit results via the GitHub API without needing local git configured:

```bash
cp .env.example .env
```
Then add your `GITHUB_TOKEN`, `GITHUB_REPO` (`username/repo`), and `GITHUB_BRANCH` to `.env`.

### Usage

Run everything from inside the `program/` directory.

**Mode 1: HTTP Ping & Geo Check**
Grabs nodes, checks if they connect, runs the GeoIP/Google checks, and writes working nodes to `results/nodes_http.txt`.

```bash
# Test everything in subscriptions.txt
python -m src.cli.main http-test --source subs

# Fast mode (bigger batches, shorter timeout, skips the Google HTML check)
python -m src.cli.main http-test --source subs --fast

# Test only the first 50 nodes
python -m src.cli.main http-test --source subs --limit 50

# Test from a local file instead
python -m src.cli.main http-test --source file --input data/custom_nodes.txt

# Run and push results to GitHub
python -m src.cli.main http-test --source subs --push
```

**Mode 2: Speed Tournament**
Runs the multi-round download test and writes the ranked list to `results/nodes_speed.txt`.

```bash
# Run tournament using the output from Mode 1
python -m src.cli.main speed-test --source http-output

# Run against all active nodes currently in the SQLite DB
python -m src.cli.main speed-test --source db

# Run from custom file and push to GitHub
python -m src.cli.main speed-test --source custom --input data/custom_nodes.txt --push
```

**Check DB Stats**
```bash
python -m src.cli.main stats
```

### Configuration

You can tweak batch sizes, timeouts, blocked countries, and test URLs in `program/config.yaml`:

```yaml
general:
  node_prefix: "xBench"
  log_level: "INFO"

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
  google_check_url: "https://www.google.com/"

http_test:
  test_url: "http://cp.cloudflare.com/generate_204"
  timeout_sec: 10.0
  concurrency: 12

speed_test:
  payload_url: "https://speed.cloudflare.com/__down?bytes=2000000"
  timeout_sec: 5.0
  concurrency: 4
  min_speed_mbps: 0.1
  bottom_third_divisor: 3
  max_consecutive_zero_runs: 3
```

### Tests

```bash
pytest tests -v
```

### License
MIT
