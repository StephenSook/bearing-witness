

NemoClaw + OpenClaw + OpenShell on a Dell Pro Max with GB10, all inference local.
Run top to bottom.

|            |                      |
| ---------- | -------------------- |
| Model      | `qwen3.8:27b-q4_K_M` |
| NemoClaw   | `lkg` (v0.0.109)     |
| Ollama     | >= 0.32.12           |
| Node       | >= 22.19             |
| SSD bundle | 22 GB                |

---

## 01 — Build the SSD bundle
**Before you travel · any aarch64 Ubuntu 24.04 box · good wifi**

Do a full install on a scratch machine first, then harvest from it.

### 1.1 Harvest

```bash
B=/mnt/ssd/gb10-bundle; mkdir -p $B/{images,models,apt,ollama,src}

# base images -- BOTH node digests are build stages and are required
docker save \
  ghcr.io/nvidia/nemoclaw/sandbox-base:v0.0.109 \
  node:22-trixie-slim@sha256:db8a96a63e5264607ada2d206758876ebbed6a12be2ada7517793cbfb0c2a29c \
  node:22-trixie@sha256:a566dd560283ae5615c8bb86b58fa8a1b6f3c82b492473a061672416266625da \
  curlimages/curl:8.10.1 \
  -o $B/images/nemoclaw-base-images.tar

# model blobs
cp -r /usr/share/ollama/.ollama/models $B/models/

# NemoClaw rejects a daemon reporting <64000 ctx -- create the override, then harvest it
sudo mkdir -p /etc/systemd/system/ollama.service.d
printf '[Service]\nEnvironment="OLLAMA_CONTEXT_LENGTH=65536"\n' \
  | sudo tee /etc/systemd/system/ollama.service.d/override.conf
sudo systemctl daemon-reload && sudo systemctl restart ollama

# ollama runtime incl. cuda backends, plus unit files
tar czf $B/ollama/ollama-arm64.tgz -C / usr/local/bin/ollama usr/local/lib/ollama
cp /etc/systemd/system/ollama.service $B/ollama/
cp /etc/systemd/system/ollama.service.d/override.conf $B/ollama/

# node + pinned source (tarred: the clone has symlinks)
(cd $B/apt && apt-get download nodejs)
git clone --depth 1 --branch lkg https://github.com/NVIDIA/NemoClaw.git /tmp/NemoClaw
tar cf $B/src/NemoClaw.tar -C /tmp NemoClaw

sync    # before unplugging
```

### 1.2 Confirm the bundle

| Path | Size | Contents |
|---|---|---|
| `models/` | 19 GB | qwen3.8:27b-q4_K_M + qwen3-embedding:4b |
| `ollama/` | 1.7 GB | binary, cuda_v12 + cuda_v13, systemd unit, override |
| `images/` | 866 MB | sandbox-base + both node digests + curl |
| `src/NemoClaw.tar` | 164 MB | shallow clone at `lkg`, tarred to keep its symlinks |
| `apt/` | 36 MB | nodejs arm64 .deb |

> **Bring a phone hotspot.** Step 04 cannot be pre-staged — the sandbox image
> build fetches npm packages at build time. Budget a few hundred MB.
> Everything before step 04 is fully offline.

---

## 02 — Host prep
**On the GB10 · offline**

### 2.1 Docker group, NVIDIA runtime, Node

The installer needs Docker without `sudo`, and OpenShell sandboxes need GPU
passthrough. A working host `nvidia-smi` does **not** mean Docker knows about
the NVIDIA runtime — check it explicitly.

```bash
B=/mnt/ssd/gb10-bundle               # wherever the SSD mounted; every later step uses $B
ls $B                                # images  models  apt  ollama  src

docker --version                     # DGX OS ships it; no network to install it if missing
sudo usermod -aG docker "$USER"      # then open a NEW shell so the group applies

docker info | grep Runtimes          # must list 'nvidia'
sudo nvidia-ctk runtime configure --runtime=docker
sudo systemctl restart docker
docker run --rm --gpus all nvidia/cuda:13.0.0-base-ubuntu24.04 nvidia-smi -L

sudo dpkg -i $B/apt/nodejs_*_arm64.deb
node --version && npm --version      # >= 22.19 / >= 10
```

---

## 03 — Restore from SSD
**On the GB10 · offline**

### 3.1 Start the 19 GB model copy first

Longest step, needs no supervision. Kick it off, then do 3.2 while it runs.

```bash
sudo tar xzf $B/ollama/ollama-arm64.tgz -C /
sudo useradd -r -s /bin/false -U -m -d /usr/share/ollama ollama 2>/dev/null || true
sudo cp $B/ollama/ollama.service /etc/systemd/system/
sudo mkdir -p /etc/systemd/system/ollama.service.d
sudo cp $B/ollama/override.conf /etc/systemd/system/ollama.service.d/

sudo mkdir -p /usr/share/ollama/.ollama
sudo cp -a $B/models/models /usr/share/ollama/.ollama/
sudo chown -R ollama:ollama /usr/share/ollama/.ollama   # required

sudo systemctl daemon-reload && sudo systemctl enable --now ollama
ollama --version                                        # must be >= 0.32.12
ollama list                                             # both models must appear
```

**Confirm GPU offload before going further.** Verifies the CUDA backend works on
sm_121. `size_vram` must equal `size`, and `context_length` must read `65536`.
If it falls back to CPU, reinstall over the hotspot:
`curl -fsSL https://ollama.com/install.sh | sh`

```bash
ollama run qwen3.8:27b-q4_K_M "say ok" --keepalive 5m
curl -s localhost:11434/api/ps | python3 -m json.tool | grep -E 'size|context_length'
```

> **Do not set `OLLAMA_HOST`.** Leave Ollama on `127.0.0.1:11434`. NemoClaw
> fronts it with a token-gated proxy on `0.0.0.0:11435` that sandboxes use;
> binding Ollama itself wide open bypasses that auth boundary and exposes
> `/api/pull` to the venue LAN.

### 3.2 Load base images

```bash
docker load -i $B/images/nemoclaw-base-images.tar
docker images    # sandbox-base, curl, and 2x  node:<none>
```

The two `node` entries showing `<none>` as their tag is correct — they were
pulled by digest. BuildKit matches them on digest, not tag.

### 3.3 Stage the workspace at final paths

Sandbox paths lock at onboard. Stage them now and reach the real data through
symlinks — then re-copying the kit never moves what the sandbox memorised.

```bash
K=/mnt/nvme/kit                        # ls $K to fill the two dirs below
sudo mkdir -p /opt/bw/{corpus,engine,state}
sudo ln -sfn $K/<corpus-dir>  /opt/bw/corpus
sudo ln -sfn $K/<repo-dir>    /opt/bw/engine

python3.12 -m venv /opt/bw/venv
/opt/bw/venv/bin/pip install --no-index --find-links $K/06_PACKAGES \
  -r /opt/bw/engine/requirements-product.txt

/opt/bw/venv/bin/python -m bearing_witness analyze \
  --root /opt/bw/corpus --condition 35Hz12kN --bearing Bearing1_3 --record 155
echo "exit=$?"                         # engine works host-side before any sandbox exists
```

`/opt/bw/state` is the only writable path — file-fallback decisions land there.
The corpus mounts read-only: evidence locators carry a `sha8` of the source, so
anything that can rewrite a measurement can silently invalidate every claim
pointing at it.

> **Find the mount flag on the box, don't guess it.**
> `nemoclaw onboard --help | grep -iE 'mount|volume|workspace|path'`, and read
> `nemoclaw-blueprint/policies/openclaw-sandbox.yaml`. Fixed layout: `/sandbox`
> and `/tmp` RW, `/usr` `/app` `/etc` RO.

---

## 04 — Install NemoClaw
**On the GB10 · hotspot ON**

### 4.1 Run non-interactively

Set the provider by environment variable, never by menu number — the wizard
renumbers based on what it detects, and the default (`build`) routes to
NVIDIA's cloud endpoints.

```bash
export NEMOCLAW_PROVIDER=ollama
export NEMOCLAW_MODEL=qwen3.8:27b-q4_K_M
export NEMOCLAW_AGENT=openclaw
export NEMOCLAW_SANDBOX_NAME=hack-agent
export NEMOCLAW_WEB_SEARCH_PROVIDER=none
export NEMOCLAW_POLICY_MODE=suggested
export NEMOCLAW_EXPERIMENTAL=1
export NEMOCLAW_NON_INTERACTIVE=1
export NEMOCLAW_NON_INTERACTIVE_SUDO_MODE=prompt
export NEMOCLAW_YES=1
export NEMOCLAW_ACCEPT_THIRD_PARTY_SOFTWARE=1
export NEMOCLAW_SANDBOX_READY_TIMEOUT=600     # real budget is 180s, not the 900s myth
export NEMOCLAW_SANDBOX_MOUNTS=...            # from 3.3; /opt/bw/corpus:ro

unset NVIDIA_INFERENCE_API_KEY OPENAI_API_KEY ANTHROPIC_API_KEY GEMINI_API_KEY \
      OPENROUTER_API_KEY COMPATIBLE_API_KEY BRAVE_API_KEY TAVILY_API_KEY

tar xf $B/src/NemoClaw.tar -C /tmp
cd /tmp/NemoClaw && bash scripts/install.sh
```

Takes roughly 4–5 minutes. Then refresh PATH:

```bash
export PATH="$HOME/.npm-global/bin:$HOME/.local/bin:$PATH"
nemoclaw --version
```

> **If the hotspot drops mid-install.** `nemoclaw onboard --resume` skips
> completed steps and picks up at the one that failed. Use `--fresh` only if you
> want to start over. Re-export the environment block first — it does not
> persist across shells.

> **A stray key silently enables web search.** `BRAVE_API_KEY` or
> `TAVILY_API_KEY` inherited from a shell profile auto-enables web search when
> the provider is unset. The `unset` line plus `WEB_SEARCH_PROVIDER=none`
> covers both.

---

## 05 — Harden
**On the GB10 · offline again — turn the hotspot off**

### 5.1 Close the cloud-inference egress

Selecting the local provider gives you a local inference *route*; it does not
close the cloud *path*. The default policy lets the OpenClaw binary POST to
`integrate.api.nvidia.com/v1/chat/completions` and `/v1/embeddings`, and reach
`openrouter.ai`. Both must go.

```bash
nemoclaw hack-agent policy exclude nvidia --yes
nemoclaw hack-agent policy remove  openclaw-pricing --yes

nemoclaw hack-agent status | grep -E 'integrate\.api\.nvidia\.com|openrouter\.ai' \
  && echo "STILL EXPOSED" || echo "clean"
```

Optional, stricter: `policy remove huggingface` also drops
`router.huggingface.co`. It is GET-only so it cannot serve completions, but it
costs you nothing once models are pre-staged.

### 5.2 Point memory search at local embeddings

Only needed if you enable memory search. It is configured separately from the
inference provider, so it will not follow your provider choice.

```bash
nemoclaw hack-agent config set --config-accept-new-path \
  --key models.providers.ollama-mem \
  --value '{"baseUrl":"http://host.openshell.internal:11434/v1",
            "apiKey":"unused","api":"openai-completions","timeoutSeconds":600,
            "models":[{"id":"qwen3-embedding:4b",
                       "name":"ollama-mem/qwen3-embedding:4b",
                       "input":["text"],
                       "cost":{"input":0,"output":0,"cacheRead":0,"cacheWrite":0},
                       "contextWindow":32768,"maxTokens":4096}]}'

nemoclaw hack-agent config set --config-accept-new-path \
  --key agents.defaults.memorySearch.provider --value ollama-mem --restart
```

Both halves must land — re-read the config and confirm the provider exists, not
just the pointer.

---

## 06 — Verify
**On the GB10**

### 6.1 Health

```bash
nemoclaw credentials list          # expect: ollama-local, nothing else
nemoclaw hack-agent doctor ; echo "exit=$?"
```

Accept only `Summary: healthy` and `exit=0`. These four lines prove the route
is local:

```
[ok] Route: ollama-local / qwen3.8:27b-q4_K_M
[ok] Inference route (gateway): https://inference.local/v1/models reachable
[ok] Provider health (ollama backend): 127.0.0.1:11434 reachable
[ok] Provider health (auth proxy):    127.0.0.1:11435 reachable
```

### 6.2 Prove it is local

Block cloud inference, then run a real tool-using turn. Completion is the
proof; a stall means something in the loop was reaching out.

```bash
sudo iptables -N NEMOCLAW_BLOCK; sudo iptables -I OUTPUT 1 -j NEMOCLAW_BLOCK
sudo iptables -I DOCKER-USER 1 -j NEMOCLAW_BLOCK
for H in integrate.api.nvidia.com api.nvidia.com openrouter.ai; do
  for IP in $(getent ahostsv4 $H | awk '{print $1}' | sort -u); do
    sudo iptables -A NEMOCLAW_BLOCK -d $IP -j REJECT
  done
done

nemoclaw hack-agent agent --agent main -m 'Create airgap.txt containing
  LOCAL-ONLY-VERIFIED, list your workspace, and tell me what 17 * 23 is.'

# tear down -- DOCKER-USER rules affect every container, do not leave them
sudo iptables -D OUTPUT -j NEMOCLAW_BLOCK
sudo iptables -D DOCKER-USER -j NEMOCLAW_BLOCK
sudo iptables -F NEMOCLAW_BLOCK && sudo iptables -X NEMOCLAW_BLOCK
```

> **The turn needs both a selector and `-m`.** Without `--agent main` it exits 2;
> with the prompt passed positionally it exits 1. Get the id from
> `nemoclaw hack-agent agents list`.

### 6.3 Prove the sandbox sees what it should — and only that

6.2 proves the inference loop. It does not touch the corpus, so it passes on a
box the product cannot run on. This is the data-path test.

```bash
nemoclaw hack-agent connect
```

Inside:

```bash
ls /opt/bw/corpus && ls /opt/bw/engine
touch /opt/bw/corpus/x 2>&1 | grep -q denied && echo "corpus RO ok"
touch /opt/bw/state/x && echo "state RW ok"
python -m bearing_witness analyze --root /opt/bw/corpus \
  --condition 35Hz12kN --bearing Bearing1_3 --record 155 | head -c 200
```

Accept only: both paths listed, corpus write **refused**, state write allowed,
contract JSON on stdout.

```bash
openclaw sandbox list
openclaw sandbox explain --agent main --json
```

---

## 07 — Operating it

| Need                 | Command                                                                        |
| -------------------- | ------------------------------------------------------------------------------ |
| Chat (browser)       | `http://127.0.0.1:18789/` — over SSH: `ssh -L 18789:127.0.0.1:18789 user@gb10` |
| Chat (terminal)      | `nemoclaw launch hack-agent`                                                   |
| One-shot turn        | `nemoclaw hack-agent agent --agent main -m '...'`                              |
| Health               | `nemoclaw hack-agent doctor` / `status`                                        |
| Logs                 | `nemoclaw hack-agent logs --follow`                                            |
| Shell in sandbox     | `nemoclaw hack-agent connect`                                                  |
| Change model         | `nemoclaw inference set --model <m> --provider ollama --sandbox hack-agent`    |
| Snapshot before risk | `nemoclaw hack-agent snapshot create`                                          |

> **If doctor reports the auth proxy unreachable:** `nemoclaw hack-agent recover`.
> The proxy on 11435 can stop — notably after destroying another sandbox — and
> the sandbox looks broken while the container is fine. One command fixes it.

---

Sandbox `hack-agent` · agent `main` · model `qwen3.8:27b-q4_K_M` · dashboard
`127.0.0.1:18789`. Substitute your own sandbox name consistently if you change it.
