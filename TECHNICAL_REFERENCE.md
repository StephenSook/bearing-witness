# How All Of This Works — Technical Reference

Hermit Crab · Bearing Witness · August 2026

The hardware, the model, the serving layer, the agent stack, and the signal chain — and how
they fit together.

---

## 1. The machine: what a GB10 actually is

The Dell Pro Max with GB10 is built around NVIDIA's **GB10 Grace Blackwell superchip**. Not a
workstation with a graphics card in it — the CPU and GPU are one package.

| Component | Detail |
|---|---|
| CPU | 20-core ARM (Grace) — 10 performance, 10 efficiency |
| GPU | Blackwell, compute capability **12.1** (sm_121) |
| Memory | 128 GB LPDDR5X, **unified** between CPU and GPU |
| Bandwidth | ~273 GB/s |
| Peak compute | ~1 PFLOP at FP4 (~170 TFLOPS at FP16) |
| Power | 240 W max draw, 280 W brick — quiet, little heat |
| OS | DGX OS 7 (Ubuntu 24.04 LTS base, aarch64) |

### Two things that matter enormously

**It is ARM, not x86.** Compiled software — Python C extensions, Docker containers, CUDA
kernels — is built for one architecture and does not cross over. A container built for an x86
machine will refuse to run here. That's correct behaviour, not a bug.

**sm_121 is not sm_100.** "Blackwell" covers a family. The datacenter B200 is sm_100. The GB10
is sm_121. Same architecture generation, different instruction set. Kernels compiled for one
may not run on the other, and some datacenter-Blackwell features are absent here. This is the
most common source of confusion about this hardware.

> **Why bandwidth is the number to watch.** 273 GB/s is large against a laptop and small
> against a datacenter GPU (H100/B200 have multi-terabyte-per-second HBM). That gap defines
> the box: *capacity* a laptop can't match, *bandwidth* a datacenter card exceeds by an order
> of magnitude. Everything about how it performs follows from that.

---

## 2. Unified memory, and why it changes things

Normal machines have two memory pools. System RAM belongs to the CPU. VRAM belongs to the GPU.
To run a model you copy weights across PCIe into VRAM, and if it doesn't fit, you're stuck.

The GB10 has **one pool**. 128 GB addressable by both, no copy step.

**What it buys:**
- Big models fit — a laptop GPU has 8–16 GB VRAM; here you have 128 GB
- No transfer tax — data the CPU produced is already visible to the GPU
- Multiple things coexist — model, database, vector index, application, one pool

**What it costs:** LPDDR5X is not HBM, and CPU and GPU share the same 273 GB/s.

> **The honest characterization.** The GB10 is a **capacity and locality** machine, not a raw
> speed machine. It exists so a large model can run *here*, with your data, rather than in
> someone else's datacenter. It does not beat an H100 on tokens per second and doesn't try to.

---

## 3. The model: what "35B-A3B" means

`nvidia/Qwen3.6-35B-A3B-NVFP4`

| Part | Meaning |
|---|---|
| `Qwen3.6` | Model family and version |
| `35B` | 35 billion total parameters |
| `A3B` | **3 billion active** per token |
| `NVFP4` | NVIDIA 4-bit floating-point quantization |

### Mixture of Experts, in plain terms

A dense model uses every parameter for every token. A **Mixture of Experts** model splits much
of its network into parallel sub-networks. For each token a small router picks a handful; the
rest sit idle.

```
Dense 35B:     [========== all 35B active ==========]  every token

MoE 35B-A3B:   [expert 1] [expert 2] [expert 3] ... [expert N]
                    ^          ^
                 router picks these — ~3B active
```

- **Memory cost is the full 35B** — all experts must be resident, you don't know in advance
  which the router picks
- **Compute cost is roughly 3B** — only selected experts run
- **Quality lands between the two**

> **Why this is the right shape for a GB10.** Plenty of capacity (128 GB), limited bandwidth
> (273 GB/s). MoE needs capacity to hold all experts but reads a small active set per token —
> plays to the strength, dodges the weakness. A dense 35B would be a worse fit on identical
> hardware.

---

## 4. Quantization: what NVFP4 is and why it exists

| Format | Bits/weight | 35B model size |
|---|---|---|
| FP32 | 32 | ~140 GB |
| BF16 / FP16 | 16 | ~70 GB |
| FP8 | 8 | ~35 GB |
| **NVFP4** | **4** | **~23 GB** |

### Why NVFP4 rather than INT4

Older 4-bit schemes used integers. NVFP4 is 4-bit *floating point* with a shared scaling
factor per small block of weights. Floating point handles wider dynamic range than integers at
the same bit count, and block scaling lets each group find its own range. Better quality
retention than naive INT4 at the same size.

It's also **Blackwell-native** — this generation's tensor cores were designed with FP4 in mind,
which is where the ~1 PFLOP FP4 figure comes from.

> **The catch on our hardware.** The native FP4 MoE kernels that ship in vLLM are built for
> datacenter Blackwell (sm_100 / sm_120) and don't include sm_121 targets yet — the PR adding
> them is still open. Earlier-2026 builds crashed on that path; current builds detect the gap and
> fall back to a different kernel (§7) on their own. The model still runs and still occupies
> ~23 GB — but it isn't getting the full native-FP4 speedup the marketing number implies.

---

## 5. How inference actually runs: prefill and decode

Two phases with completely different performance characteristics. This explains almost every
performance question you'll be asked.

### Prefill — reading the prompt

The model reads your entire prompt at once. Every token processes in parallel because they're
all already known. Big matrix multiplication, which GPUs are excellent at.

**Prefill is compute-bound.** Fast, scales well. Low thousands of prompt tokens per second on
this hardware class.

### Decode — writing the answer

One token, then the next, then the next. Strictly sequential — token N+1 depends on token N.

The crucial part: **to produce each single token, the model must read its weights from
memory.** One token of output requires streaming gigabytes through the memory bus.

**Decode is memory-bandwidth-bound.** The GPU spends most of its time waiting. Adding compute
doesn't help; only bandwidth does.

```
PREFILL:  prompt ─────────► [ all tokens in parallel ]  fast
                                     │
DECODE:                              ├──► token 1  (read weights)
                                     ├──► token 2  (read weights)
                                     ├──► token 3  (read weights)
                                     └──► ...      one at a time
```

> **Why this explains the GB10's profile.** 273 GB/s divided by bytes-read-per-token gives a
> hard ceiling on tokens/second, and no amount of tensor-core throughput moves it. A 120B model
> here might prefill at 1,600–1,900 tok/s but decode at ~23 tok/s. It's also why MoE helps so
> much — reading 3B active parameters instead of 35B is a direct bandwidth saving.

### The KV cache

As the model generates, it stores intermediate state for every token so far — the "key-value
cache" — so it doesn't recompute the whole context each step.

The cache grows with context length and concurrent requests, lives in the same memory pool as
the weights, and can be enormous. At aggressive default settings a server may pre-allocate tens
of gigabytes for KV cache alone.

> **The tuning trap.** Serving software often pre-allocates based on a theoretical maximum. A
> default reserving ~89 GB for millions of tokens is wasteful when a single-user workflow needs
> a few hundred thousand at most. Biggest single memory lever on the box — get it wrong and you
> either waste capacity or OOM at startup. NVIDIA's own DGX Spark recipe for this model sets
> `--gpu-memory-utilization 0.4`; that is the value we use.

---

## 6. The serving layer: vLLM, Ollama, llama.cpp

A model file is inert. Something has to load it, hold it in memory, and answer requests.

| | vLLM | Ollama | llama.cpp |
|---|---|---|---|
| **Built for** | High-throughput serving | Simple local use | Portable local inference |
| **Concurrency** | Continuous batching, paged KV | Sequential queue | Sequential, some batching |
| **Format** | safetensors, NVFP4, FP8 | GGUF (its NVFP4 builds are MLX, macOS-only) | GGUF |
| **API** | OpenAI-compatible | Native `/api/chat` + OpenAI shim | `llama-server` HTTP |
| **Setup cost** | High — container, kernels, flags, tuning | Low — pull and run | Medium — compile from source |
| **Observability** | Rich metrics | Minimal | Minimal |

### Continuous batching, explained

vLLM's headline feature. Traditional batching waits for a fixed group, runs them together,
returns when the slowest finishes. Continuous batching admits and retires requests *between
decode steps* — a finished request leaves immediately, a new one takes its slot.

Large win when requests overlap. Does nothing when they don't. **Batching cannot manufacture
load from infrequent arrivals**, which is why it isn't a justification for our workload — our
calls are sequential.

### What each implies for us

- **vLLM** is staged and serves NVFP4 directly — image `vllm/vllm-openai:latest` (arm64; the
  image NVIDIA's DGX Spark playbook uses for this exact model — `cu130-nightly` is deprecated).
  Cost is setup risk: container compatibility, kernel-backend flags, KV cache tuning, and a first
  start that can take 10–15 minutes (weight load, CUDA-graph compile, warmup). Not a hang.
- **Ollama** is the 11:15 parachute — `qwen3.6:35b-a3b-q4_K_M` (GGUF, ~24 GB). Ollama's
  `-nvfp4` tags are MLX builds that only run on macOS, so the fallback is ordinary 4-bit GGUF,
  not NVFP4: same model family, different quantization. Use native `/api/chat` — the OpenAI shim
  ignores Modelfile sampling parameters, which has been measured to suppress tool calls. Avoid
  JSON-schema `format` combined with `think:false` on this model (open GB10 crash).
- **llama.cpp** is a third path worth knowing: compile with `-DCMAKE_CUDA_ARCHITECTURES=121`,
  serve GGUF through `llama-server`. A prior GB10 hackathon project used exactly this. Sidesteps
  both the vLLM container question and Ollama's GPU-detection quirks.

---

## 7. Kernels: why we pin Marlin

A *kernel* is a small program that runs on the GPU to perform one operation. Which kernel gets
used depends on data format and hardware.

For 4-bit MoE weights on Blackwell, the intended path uses CUTLASS / FlashInfer FP4 kernels built
for datacenter Blackwell. **The published builds don't target sm_121.** On earlier-2026 builds the
native FP4 MoE path crashed on this chip; on current builds vLLM sees there is no sm_121 kernel
and falls back on its own.

**Marlin** is the fallback — a W4A16 kernel (4-bit weights, 16-bit activations) that dequantizes
FP4 to BF16 on the fly, multiplies in 16-bit, moves on.

```
Intended:   FP4 weights ──► native FP4 tensor cores ──► result
                             (unavailable on sm_121)

Marlin:     FP4 weights ──► dequantize to BF16 ──► BF16 multiply ──► result
                             (works, costs throughput)
```

`--moe-backend marlin` is the value in NVIDIA's own DGX Spark recipe for this model. Current vLLM
would land on it anyway; we pin it so the behaviour is explicit and can't change under us. You
keep 4-bit storage but give up some speed of native 4-bit math.

> **How to say this to a judge:** "We store at 4-bit for the memory footprint, but the native FP4
> MoE kernels are built for datacenter Blackwell and don't target SM121 yet, so we run through
> Marlin — dequantize to BF16 at compute time. We keep the 23 GB footprint and accept the
> throughput cost." That shows you know what's happening inside the box rather than just typing
> flags.

---

## 8. The agent stack: OpenClaw, NemoClaw, OpenShell

Three names used interchangeably that shouldn't be. They're layers.

```
┌─────────────────────────────────────────────┐
│  NemoClaw          (NVIDIA's distribution)   │
│  installs, configures, wires it together     │
│                                              │
│  ┌────────────────────────────────────────┐ │
│  │  OpenClaw       (the agent framework)   │ │
│  │  reads files, calls tools, reasons      │ │
│  └────────────────────────────────────────┘ │
│                     runs inside              │
│  ┌────────────────────────────────────────┐ │
│  │  OpenShell      (the sandbox runtime)   │ │
│  │  network policy, filesystem, syscalls   │ │
│  └────────────────────────────────────────┘ │
└─────────────────────────────────────────────┘
```

**OpenClaw** — agent framework, runs locally, reads files, executes commands, calls tools. Our
agent is a *skill*: a markdown file describing what it does, shelling out to our Python. The
framework handles the loop; we supply the capability.

**NemoClaw** (0.0.110 staged; 0.0.113 is current, no breaking changes between them) — packages
OpenClaw with NVIDIA's local inference setup and security controls. Installs the sandbox,
configures the model endpoint, gives you a CLI. If you start your own vLLM on `:8000` first,
`NEMOCLAW_PROVIDER=vllm nemoclaw onboard` reuses it rather than pulling a managed one.

**OpenShell** (0.0.106 — the exact version NemoClaw's blueprint requires; never `self-update`) —
the security runtime beneath everything:
- **Default-deny networking.** Sandbox can only contact explicitly allowed endpoints. Everything
  else blocked and logged.
- **Filesystem confinement.** Specific paths writable, system paths read-only. Permissions fixed
  at creation — get them wrong and you rebuild.
- **Process restriction.** Namespace isolation, syscall filtering, privilege dropping.
- **Audit logging.** Every tool call, file access, and blocked network attempt recorded.

> **Why this matters for the pitch.** The security story isn't "we promise the agent won't
> exfiltrate the waveform." It's "the agent has no allowed network path, so it cannot, and the
> audit log proves it." A probabilistic model can be wrong or manipulated. A containment policy
> is deterministic.

---

## 9. The signal chain: waveform to decision

This is the actual product, and none of it touches the GPU.

**What arrives:** a CSV of 32,768 acceleration samples at 25.6 kHz — 1.28 seconds of vibration
from an accelerometer on a bearing housing. One record per minute of bearing life.

**Step 1 — Compute fault frequencies.** From geometry alone, before touching data. Ball count,
ball diameter, pitch diameter, contact angle, shaft speed. Four numbers: where a defect on each
element *must* ring. For the LDK UER204 in our dataset — 8 balls, 7.92 mm ball, 34.55 mm pitch,
0° contact — at the 35 Hz setpoint: BPFO 107.9 Hz, BPFI 172.1 Hz, 2×BSF 144.7 Hz, FTF 13.5 Hz.

**Step 2 — Find the resonance band.** Each impact excites a structural resonance somewhere in
2–10 kHz. We don't know where, so we sweep candidate bands and score by **kurtosis** — a
statistical measure of spikiness. A band full of sharp repeated impacts scores high. This is the
kurtogram method (Antoni 2007) — the band selector the standard bearing-diagnostics tutorial
(Randall & Antoni 2011) recommends. Its known trap: it can elect a band of impulsive noise that
has nothing to do with the bearing, so the band it picks is checked, not trusted.

**Step 3 — Demodulate.**

```
raw ──► band-pass ──► Hilbert envelope ──► square ──► FFT ──► envelope spectrum
        (keep the      (trace the                     (find the
         resonance)     outline)                       repetition rate)
```

The Hilbert transform gives the analytic signal; its magnitude is the envelope — the outline of
the oscillation, discarding the carrier. FFT of that outline reveals how often impacts repeat.

*The analogy:* you can't hear someone tapping a wine glass across a noisy room, but you can see
it flickering in the light at the tapping rate. Envelope analysis watches the flicker instead of
listening for the tap.

**Step 4 — Match against prediction.**

```
bin width = sample_rate / N = 25600 / 32768 = 0.78125 Hz

half_width = max(0.5 × bin_width, f_expected × relative_uncertainty)
```

A flat ±2% at FTF (13.5 Hz) is ±0.27 Hz — narrower than half a bin, therefore unresolvable.
This is why the tolerance must be resolution-aware.

The other half of the tolerance is physics. Rolling elements slip, so real bearing frequencies
sit roughly 1–2 % off the calculated value and jitter around it (Randall & Antoni, *Mechanical
Systems and Signal Processing*, 2011). Our measured BPFO runs 0.8 % low — inside that band, and
the reason a ±0.5 % window would have missed the peak entirely.

**Step 5 — Decide, or refuse.** One family supported with clear margin → name it. Several
families, or none, or missing trust inputs → refuse and say why.

### The v3 rules (approved 2026-08-21, frozen before the evaluator runs)

- **Stage 1 is one-sided.** Windows 1–10 of each bearing are held as baseline; a window is
  abnormal only when its z-score is ≥ +5 in the fault-physics direction, and it takes three
  consecutive abnormal windows to count as persistent. So the earliest onset the detector can
  report is window 11. (A two-sided rule was falsified in build-test: an injected pure tone
  *suppresses* crest and kurtosis and moves two feature groups.)
- **Harmonic floor.** Any element call needs ≥ 3 harmonics of that family above three times
  the noise floor. A lone peak near a predicted line is never enough.
- **View A is a gate.** The ordinary spectrum must support the same family as the envelope
  spectrum, or the result is `ABNORMAL_LOCATION_UNCONFIRMED`, not a call. We pre-declared that
  this may turn some previously-correct calls into abstentions, and we report what comes out.
- **Measured shaft speed labels, it never predicts.** The ~34.7 Hz we measure anchors the
  labels on shaft harmonics in Stage 2 only; every bearing-family prediction uses the documented
  35.0 Hz setpoint plus tolerance. Both numbers are shown in the trust panel.

### Why this is all CPU work

At 32,768 samples a band-pass, Hilbert transform, and FFT are small operations. Moving that data
to the GPU costs more in launch overhead and transfer than the computation saves. Crossover is
hundreds to thousands of same-shaped records batched together. We are not there.

> **Frame this as a design choice, not a limitation.** Deterministic CPU signal processing means
> the diagnosis is reproducible, explainable, and independent of a generative model. Run it twice
> on the same input, get the same answer. That's a property you want in a system that recommends
> taking a machine offline.

---

## 10. End to end: one record through the system

```
   [ CSV lands in watched directory ]
                │
                ▼
   ┌─────────────────────────────────┐
   │  Heartbeat loop notices it      │   ← this is what makes it an agent
   └─────────────────────────────────┘   ← rather than a script
                │
                ▼
   ┌─────────────────────────────────┐
   │  STAGE 0 — Trust gate            │   CPU
   │  speed? geometry? provenance?    │   deterministic
   └─────────────────────────────────┘
                │  (blocked → task created, stop)
                ▼
   ┌─────────────────────────────────┐
   │  STAGE 1 — Detect change         │   CPU
   │  RMS, kurtosis, crest, energy    │   fault-agnostic
   │  vs chronological baseline       │   no BPFO lookup here
   └─────────────────────────────────┘
                │  (no change → GREEN, stop)
                ▼
   ┌─────────────────────────────────┐
   │  STAGE 2 — Explain the machine   │   CPU
   │  shaft, electrical, gear, vane   │
   └─────────────────────────────────┘
                │
                ▼
   ┌─────────────────────────────────┐
   │  STAGE 3 — Corroborate           │   CPU
   │  ordinary spectrum + envelope    │   both must agree
   │  kurtogram → bandpass → Hilbert  │
   │  → FFT → match families          │
   └─────────────────────────────────┘
                │  (ambiguous → YELLOW, stop)
                ▼
   ┌─────────────────────────────────┐
   │  Result JSON                     │   the contract
   │  evidence locators, refusals     │   ← everything above is
   └─────────────────────────────────┘      deterministic and testable
                │
                ▼
   ┌─────────────────────────────────┐
   │  OpenClaw agent                  │   GPU
   │  reads the JSON via typed tools  │   model explains evidence
   │  drafts inspection in English    │   it did not compute
   └─────────────────────────────────┘
                │
      ┌─────────┴─────────┐
      ▼                   ▼
  OpenShell           MongoDB
  denies egress       stores evidence,
  logs the attempt    decision, reason
                │
                ▼
   ┌─────────────────────────────────┐
   │  Human approves or rejects       │   ← nothing becomes a work order
   └─────────────────────────────────┘      without this
```

**Vocabulary, exactly as the code and the Mongo validators spell it.** States:
`BLOCKED_SIGNAL`, `BLOCKED_BASELINE`, `NO_ANOMALY_DETECTED`, `WATCH_EARLY`,
`ABNORMAL_LOCATION_UNCONFIRMED`, `ANALYST_REVIEW_REQUIRED`, `INSPECTION_APPROVED`,
`INSPECTION_REJECTED`. Task types: `INSPECTION_WORK_ORDER` (the drafted inspection — a review
request, never a repair order), `MEASURE_SHAFT_SPEED`, `VERIFY_BEARING_GEOMETRY`,
`RECAPTURE_SIGNAL`, `ANALYST_REVIEW`. Every evidence locator is
`{asset_id}|w{window}|{sha8}|{view}|{freq:.2f}Hz[|h{k}][|sb{m:+d}]` — `|h` is absent only for
unexplained residual peaks, `|sb` never appears without `|h`, and consumers parse by prefix
(`w`/`h`/`sb`), 5–7 segments, never by position (PLAN.md Shared Contracts, `⚠️ CONTRACT`
2026-08-21). The same string appears in the JSON, the UI, and the model's draft.

> **The one-sentence architecture.** Deterministic physics produces the diagnosis and owns the
> truth; the model translates that evidence into a human-readable task; the sandbox guarantees
> neither ever leaves the room; a person makes the final call.

---

## 11. Answering technical questions

### "Why do you need a $5,700 machine for this?"

*(Dell US list ≈ $5,650 for the 4 TB configuration as of Aug 2026, up from ~$3,999 at the Nov 2025
launch; ≈ £6,000 UK, ≈ €6,900 DE incl. VAT — the priciest of the GB10 boxes. If a judge says
"a $4,000 machine", that's the launch price; don't argue it, the answer is the same.)*

The signal processing doesn't — and we keep it on CPU deliberately, because reproducible fault
detection shouldn't depend on a generative model. The box is here because the event requires an
always-on local agent, and because in a plant the vibration data and asset geometry aren't
supposed to reach a hosted API. The model runs in the room. If it were merely slower on a laptop
we'd have a weak argument; the argument is that on a laptop this class of model doesn't fit at
all.

### "Isn't this just an FFT with an LLM bolted on?"

The FFT is one of five stages, and it's stage three. Stage one detects a persistent change
without looking at any fault frequency — deliberately, so we don't find 107.9 Hz because we went
looking for it. Stage two explains what the machine normally produces so we don't blame the
bearing for a vane pass. The model doesn't compute anything; it explains evidence and drafts a
task a human has to approve.

### "How do you know it works?"

Fifteen bearings from a public run-to-failure dataset, each with a documented failure mode. We
measure warning lead time, abstention rate with reason codes, and wrong-call count. We don't
claim a headline accuracy number unless a frozen evaluator produced it before we saw the results.
The thresholds are one frozen dataclass; its version and file hash are embedded in the evaluator
output, and nobody edits it after the freeze commit. Wrong calls go in the first sentence of the
results, not a footnote.

One honesty note we raise ourselves: the v3 detector holds windows 1–10 as baseline and needs
three consecutive abnormal windows, so its earliest possible onset is window 11. An earlier prep
evaluator reported an onset at window 9 on one bearing — which told us the two onset definitions
differed, so no lead time was quoted until they were reconciled and written down. That is now
done (`eval/onset_inspection.md`, Task 14): the prep evaluator scored the baseline windows
against their own median under a two-sided rule; v3 never evaluates windows 1–10 and is
one-sided. Eight of fifteen onsets are identical under both rules, seven moved later under v3
and are taken from v3 only, and the v2 aggregate is dropped. The quotable lead-time statement is
the v3 one: files − onset over 15/15 bearings, min 11 / median 99 / max 2519 min — with one stated
caveat: Bearing3_5's baseline is already contaminated (rms 14.8 MAD inside windows 1–10), so
its onset 11 is the structural floor, not a measurement; its floor value (103 min) sits in that
15-bearing median, and excluding it the median is 98 min (min/max unchanged). We quote no lead
time for Bearing3_5 on its own.
Bearing3_1's early onset (19 of 2538) has a clean baseline and stands. None of this is a
remaining-useful-life claim.

### "How much of this existed before today?"

The signal-processing prep — frequency math, feature extraction, two earlier evaluator passes on
a laptop — was done in the days before, and the event rules allow starter scaffolds and existing
libraries. After the rules were read on Friday, both build lanes also laid scaffolding Friday
evening and said so in PLAN.md's status notes: on the engine side the package skeleton and its
first four modules (signal math, record loader, the frozen thresholds dataclass, the result
contract) with their tests; on the product side the Mongo store, the UI running on fixtures, and
the contract-shaped adapter. We say all of it plainly in the submission. What is built on the
day is what makes it a product: the Stage-1 detector, the engine and CLI, the adapter flip from
fixtures to real output, the agent tools, the sandbox policy, and the Saturday freeze-and-evaluate
run that every number we quote comes from.

### "Why not train a model on the failure data?"

Because in the field that data doesn't exist. A plant may run a pump nine years without a
failure, so there's nothing to train on — that's the documented gap in the prognostics
literature. We compute what the failure must look like from the bearing's geometry instead,
which works on day one on a machine that has never broken.

### "What's NVFP4 and why does it matter here?"

A 4-bit floating-point format with per-block scaling, Blackwell-native. Takes the model from
~70 GB at BF16 to ~23 GB, which makes a 35B model comfortable on this box alongside everything
else. One caveat we're honest about: the native FP4 MoE kernels are built for datacenter
Blackwell and don't target SM121 yet, so we run through Marlin and dequantize to BF16 at compute
time. We keep the footprint, we give up some throughput.

### "Why MoE rather than a dense model?"

35 billion parameters total, about 3 billion active per token. Memory cost is the full 35B
because all experts have to be resident, but compute and bandwidth cost is closer to 3B. On a box
with plenty of capacity and modest bandwidth, that's exactly the right trade — plays to the
strength, dodges the weakness.

### "Why vLLM instead of something simpler?"

It's what we staged, and it serves the NVFP4 checkpoint directly. Our calls are sequential, so
we're not using continuous batching for throughput — we'd say so rather than pretend otherwise.
If it isn't serving by 11:15 we switch to Ollama on the native chat endpoint with a 4-bit GGUF
build of the same model, and the deterministic engine's output exists either way. The demo
narrows; it doesn't die.

### "Is the fallback also NVFP4?"

No. Ollama's NVFP4 builds exist only for Apple Silicon, through its MLX engine. The fallback is a
standard 4-bit GGUF of the same model family — about the same footprint, conventional block
quantization, no Blackwell-specific kernels. The deterministic engine doesn't care which one is
answering; only the explanation layer changes.

### "What stops the agent leaking the data?"

OpenShell runs default-deny networking. The sandbox can only reach endpoints explicitly allowed,
and there aren't any beyond local inference. That's not a promise about model behaviour — a model
can be wrong or manipulated. It's a containment policy, and it's deterministic.

### "Is this replayed data?"

Yes, and deliberately — that's how we prove the peaks land where physics predicted, against
documented ground truth. The method needs no prior failure data. Replaying recordings validates
the method; it isn't a substitute for it.

### "Why does it refuse instead of giving a best guess?"

Because a confident wrong answer costs more than no answer. If two signal views disagree, or the
shaft speed is untrusted, or several fault families fit equally well, we return the reason and
create a task — measure the speed, verify the geometry, recapture the signal. An alarm nobody
trusts gets ignored, and that's how condition-monitoring programmes die.

### "What can't it do?"

It's one detector for one fault class. No unbalance, misalignment, looseness, electrical faults,
or gear faults — each needs separate validation. No remaining-useful-life prediction. No
temperature. Nothing above 12.8 kHz, because that's the dataset's Nyquist limit. It doesn't
replace a vibration analyst; it tells one where to look.

---

## 12. The evidence engine, module by module (the engine lane)

Everything in this section is read from `bearing_witness/` at the frozen v3 state
(`thresholds.py` sha256 `59a9d901…`). Every constant below is a field of the one frozen dataclass
`thresholds.Thresholds` unless it says otherwise. If a number here and a number in the code ever
disagree, the code wins and this file is wrong.

### 12.1 The map

| Stage | Module | One sentence |
|---|---|---|
| I/O | `data.py` | One CSV = one 1.28 s record; column 0 (horizontal) only; sha256 of the raw file bytes travels with every result. |
| math | `dsp.py` | Fault frequencies, band-pass, envelope, two spectra, noise floors, peak refinement, robust z. Pure functions. |
| 0 — trust | `trust.py` | What we are allowed to conclude from this record: signal sanity, and whether speed / geometry / regime / acquisition are trusted. |
| 1 — detect | `features.py` + `detect.py` | Nine fault-agnostic indicators per window; robust z against the asset's own first ten windows; persistence. Nothing in here knows what BPFO is. |
| 2 — explain | `explain.py` | Label what the machine normally produces in the ordinary spectrum (shaft orders, line orders) so Stage 3 cannot blame the bearing for them. Also View A. |
| 3 — localize | `families.py` | Envelope-spectrum family scoring (View B): band choice, harmonics, sidebands, exclusion, aggregation over the last five windows, the decision rule. |
| glue | `engine.py` | `Engine.analyze(k)`: runs 0→1→2→3 on window `k` using only windows `1..k`, fills the contract, builds locators, drafts the task. |
| output | `contract.py` | The 14-field `ResultContract` (pydantic), the 8 statuses, the 5 task types, the locator string. |
| review | `review.py` | `apply_decision` (APPROVE / REJECT / DEFER) — only on `ANALYST_REVIEW_REQUIRED`, always through a `DecisionStore`, evidence retained. |
| CLI | `__main__.py` | `python -m bearing_witness analyze|replay …` prints the contract JSON / one line per window. |
| eval | `eval/run_eval.py` | Frozen evaluator: last record of each of the 15 bearings, verdict vs documented failure element, results committed verbatim. |
| thresholds | `thresholds.py` | `VERSION = "v3"`, one frozen dataclass, read-only since the freeze commit `3bda3b7`. |

Data flow for one call, `Engine(ctx, record_dir, cache_dir).analyze(k)`:

```
record k.csv ─► trust gate ─► ordinary spectrum ─► Stage 2 labels (if order analysis allowed)
                   │
                   ├─► Stage 1 replay over windows 1..k (features from the cache, recomputed on miss)
                   │        └─► persistent?  no → GREEN / WATCH_EARLY, stop
                   │
                   └─► yes → Stage 3 on the last 5 windows → decide → View A gate → status, draft, locators
```

Tests: 56 fast (synthetic signals only) + 4 slow (real Bearing1_3, needs `data/`). `pytest -q` runs the fast
set by default (`addopts = -m 'not slow'`).

### 12.2 Records and constants (`data.py`, `dsp.py`)

- `FS = 25600.0` Hz, `N_EXPECTED = 32768` samples, so one record is 1.28 s and the FFT bin is
  `BIN_W = FS / N = 0.78125 Hz`. Nyquist is 12.8 kHz — nothing above it exists in this data.
- `load_record` reads `np.loadtxt(path, delimiter=",", skiprows=1, usecols=0)` — the one-line header is
  skipped, **only the horizontal channel is used**, and `Record.channel = "horizontal (column 0)"` is
  written into the contract's `source_window` so nobody has to guess.
- `sha256_file` hashes the CSV bytes in 1 MiB chunks; the first 8 hex characters are the `{sha8}` segment of
  every evidence locator. A locator therefore points at one specific file, not "window 155 of something".
- `count_records` counts files matching `^\d+\.csv$` — `notes.csv` would not count.

### 12.3 Fault frequencies — computed from geometry, never fitted

```python
ratio = (d / D) * cos(contact_angle)
BPFO = (n/2) * (1 - ratio) * f_shaft
BPFI = (n/2) * (1 + ratio) * f_shaft
BSF2 = 2 * (D / (2d)) * (1 - ratio**2) * f_shaft      # 2×BSF: both sides of the ball strike per revolution
FTF  = 0.5 * (1 - ratio) * f_shaft
```

LDK UER204, from the dataset paper (Wang, Lei, Li, Li, IEEE Trans. Reliability 2020): `n = 8` balls,
`d = 7.92 mm`, `D = 34.55 mm`, contact angle 0°. At the 35 Hz setpoint: **BPFO 107.907, BPFI 172.093,
2×BSF 144.660, FTF 13.488 Hz** (`tests/test_dsp.py` asserts these and the identity FTF = BPFO / 8).
The family list is `("BPFO", "BPFI", "BSF2", "FTF")` — there is no plain BSF anywhere; a rolling-element
defect strikes inner and outer race once each per ball revolution, so 2×BSF is the primary line (spec §2).

### 12.4 The two spectra and the small helpers (`dsp.py`)

- **Ordinary spectrum** — mean removed, Hann window, rFFT, amplitude-corrected `2·|X| / Σw` so a unit sine
  reads 1.0 (tested to 5 %). Used by Stage 2 (labels) and View A.
- **Envelope chain** — `bandpass` is a 4th-order Butterworth in SOS form, applied with `sosfiltfilt`
  (zero-phase, so no group delay smears the impacts); then `|hilbert(xb)|` is the envelope; the
  **envelope spectrum** is `rFFT(env² − mean) / N`. Squaring before the FFT is the classic squared-envelope
  spectrum; removing the mean kills the DC spike.
- `noise_floor(freqs, amp, lo=5, hi=500)` — the **median** amplitude between 5 and 500 Hz of whichever
  spectrum it is handed. Median, not mean, so the peaks we are looking for do not inflate their own floor.
- `local_noise(f, half_span=20, exclude_hw)` — median in `f ± 20 Hz` with the candidate's own window cut
  out. `snr_local = peak / local_noise`. This is the SNR every "above floor" test in Stage 2 / View A uses.
- `peak_in_window(f, hw)` — largest bin inside `f ± hw`. `refine_peak` — parabolic interpolation on log
  amplitude over three bins, which takes 0.78 Hz quantisation to ~0.05 Hz (tested on a 34.7 Hz tone).
- `half_width(f, rel=0.02) = max(0.5·BIN_W, f·rel)` — the resolution-aware tolerance. With ±2 % only FTF
  (13.49 Hz → 0.27 Hz) is narrower than half a bin; the rule engages exactly there (test: FTF → 0.3906,
  BPFO → 2.158).
- `excess_kurtosis = E[(x−μ)⁴] / σ⁴ − 3` (Gaussian → 0, impulsive → large). `robust_z` below.

### 12.5 Stage 0 — trust (`trust.py`)

Three trust levels: `TRUSTED_MEASURED`, `TRUSTED_FOR_REPLAY`, `UNVERIFIED`. `xjtu_context(cond, bearing)`
builds the `AssetContext` for a dataset bearing: speed = the documented setpoint (35 / 37.5 / 40 Hz),
`uncertainty_rel = 0.02`, trust `TRUSTED_FOR_REPLAY` (a setpoint is not per-window telemetry); geometry =
the paper's LDK UER204 numbers, same trust; regime = the condition and load; acquisition = 25.6 kHz,
horizontal, 32 768 samples; machine map = shaft orders up to 10, no line frequency, no gears/vanes
documented. `asset_id = "XJTU-SY/{condition}/{bearing}"`.

`evaluate_trust(ctx, record)` first runs five signal checks — sample count ≠ 32 768, fs ≠ 25 600,
non-finite samples, clipping (>0.1 % of samples at ≥99.9 % of the peak), flatline — and any hit returns
`signal_ok = False, blocks = ["ALL"], tasks = ["RECAPTURE_SIGNAL"]`. Otherwise:

| Input `UNVERIFIED` | adds to `blocks` | task | note |
|---|---|---|---|
| speed | `ORDER_ANALYSIS`, `LOCALIZATION` | `MEASURE_SHAFT_SPEED` | `SPEED_UNVERIFIED` |
| geometry | `LOCALIZATION` | `VERIFY_BEARING_GEOMETRY` | `GEOMETRY_UNVERIFIED` |
| regime | `BASELINE_COMPARISON` | — (→ `ANALYST_REVIEW` in the engine) | `REGIME_UNVERIFIED` |
| acquisition | `ALL` | `RECAPTURE_SIGNAL` | `ACQUISITION_UNVERIFIED` |

`with_unverified(ctx, "geometry")` is how demo step 7 and the CLI flags flip one input to `UNVERIFIED`
without touching anything else.

### 12.6 Stage 1 — detect a persistent change (`features.py`, `detect.py`)

**Nine indicators, four groups, names frozen** (the feature cache CSVs depend on them):

| group | features | how |
|---|---|---|
| `energy` | `rms`, `p2p` | `sqrt(mean x²)`, `max − min` |
| `shape` | `crest`, `kurtosis_excess` | `max|x| / rms`, excess kurtosis |
| `hf_band` | `be_2000_4000`, `be_4000_6000`, `be_6000_8000`, `be_8000_10000` | RMS of the band-passed signal in each fixed 2 kHz band (raw band RMS, not a ratio) |
| `envelope` | `env_energy` | RMS of the Hilbert envelope of the 2–10 kHz band |

No fault frequency is looked up here — that is the point. Stage 1 is allowed to say "something changed",
never "BPFO".

**The rule (v3):**
1. Windows 1–10 (`baseline_n = 10`) are the baseline. Per feature: `median` and `MAD = median(|x − median|)`
   over those ten windows. Windows 1–10 return state `BASELINE` — **they are never scored**.
2. From window 11: `z = 0.6745 · (x − median) / MAD` (`dsp.robust_z`; 0.6745 = Φ⁻¹(0.75) makes MAD
   comparable to σ for Gaussian data; MAD = 0 → z = 0 if equal, else ±1e9).
3. A group "moves" if **any** of its features has `z ≥ +5` (`z_thresh = 5.0`, `one_sided = True`). Drops do
   not count.
4. `≥ 2` groups moved (`min_groups = 2`) → `ABNORMAL`; exactly one group → `WATCH`, or `WATCH_EARLY` if
   that group is `hf_band` or `envelope` (`watch_early_groups`); none → `NORMAL`.
5. `persist = 3` consecutive `ABNORMAL` windows → persistent; `onset_window = windows[-3]`, the **first**
   window of the run. Any non-abnormal window resets the run to 0. Earliest possible onset: **11**.

**Why one-sided, in one sentence:** the build test injected a pure 107.9 Hz tone at 5× RMS into a healthy
window; it raised `energy` but *lowered* crest and kurtosis (a sine is less spiky than noise), so under
two-sided |z| two groups moved and the fake looked abnormal. One-sided, only `energy` moves → `WATCH`, never
`ABNORMAL` (`tests/test_detect.py::test_build_test_fake_tone_cannot_look_abnormal`, and the same test at
engine level). Real onsets did not move on Bearing1_3 (59 either way); seven other bearings moved later
(§11 honesty note).

**Replay discipline:** `Engine.analyze(k)` builds a fresh `ReplayDetector` and pushes windows `1..k` in
order, features from `FeatureCache` (`eval/feature_cache/{bearing}.csv`, header `window,rms,…,env_energy`)
and recomputed on a miss (≈15 ms per window cold). A window's state depends only on windows at or before
it; nothing from the future and nothing from ground truth is readable from the package
(`grep ground_truth bearing_witness/` is empty).

### 12.7 Stage 2 — explain the machine, and View A (`explain.py`)

`explain_ordinary(freqs, amp, ctx, th)` works on the ordinary spectrum **≤ 1 000 Hz** (`ordinary_max_hz`):
- Global floor = median amplitude over 5–1000 Hz.
- **1× shaft search:** inside `half_width(setpoint, 0.02)` (±2 % of 35 Hz = ±0.7 Hz) find the peak; accept
  if ≥ `3×` local noise (`ordinary_snr = 3.0`); refine to ~0.05 Hz. That refined value is
  `shaft_hz_measured` (≈ 34.7 Hz on Bearing1_3). If nothing qualifies, the anchor falls back to the setpoint.
- **Shaft orders 1..10** (`shaft_orders`): window `max(BIN_W, 0.005 · k · anchor)` — **0.5 %**, anchored on
  the *measured* 1×. Why so tight: 3× shaft is 105 Hz and BPFO is 107.9 Hz; a 2 % window at 3× reaches
  107.1 Hz and would label the real bearing peak "3x shaft" (`test_three_x_shaft_window_does_not_swallow_bpfo`).
  Labels `"{k}x shaft"` carry `order = k` → locator `|h{k}`.
- **Line orders 1..4** if `machine_map.line_hz` is set (it is `None` for the XJTU rig).
- **Unexplained residuals:** local maxima ≥ `5×` the global floor (`residual_snr`), not within a tolerance of
  any explained frequency, top 5 by amplitude, label `"unexplained"`, `order = None` (locator without `|h`).
- Returns `shaft_hz_reference` (the setpoint — what every bearing prediction uses) **and**
  `shaft_hz_measured` (reported only). Spec §11 hard cut: measured speed never feeds a fault frequency.

**View A** (`ordinary_supports(freqs, amp, f0, explained_hz, th)`): in the same ≤ 1 kHz ordinary spectrum,
look for `k = 1..5` harmonics of the envelope winner's measured `f0`, window `half_width(k·f0, 0.015)`;
skip any harmonic that sits on an already-explained machine line; count those ≥ 3× local noise. Supported
if **≥ 1** (`view_a_min_harmonics`). Failure reason string:
`ALL_HARMONICS_EXPLAINED_OR_BELOW_FLOOR_k1..5`. View A is a *gate*, not a score — it can only turn a call
into an abstention, never create one.

### 12.8 Stage 3 — localize (`families.py`)

`localize_window(x, window, preds, f_shaft, th)` for one record:

1. **Band choice.** Two candidates: the fixed `demod_band = (2000, 4000)` Hz, and the compact-kurtogram
   winner (`sk_winner_band`: bandwidths 4 / 2 / 1 kHz, 50 % overlap, swept 1 000–12 200 Hz, score =
   excess kurtosis of the band's envelope). Score all four families in both; **coherence** = the largest
   `harmonics_above_floor` any family reaches in that band; keep the more coherent band, **tie → fixed**.
   The prep finding behind this: SK alone elected 11.5–12 kHz noise bands whose BPFO family was 8× weaker
   than 2–4 kHz. Kurtosis rank is not demodulation quality.
2. **Envelope spectrum** of the chosen band; `noise` = median 5–500 Hz.
3. **Per family** (`score_family`): candidate fundamentals on a grid `fpred · (1 ± 0.025)` in half-bin steps
   (`f0_rel`, slip measured ≈ 1 % here). For each candidate, harmonics `k = 1..3` (`n_harmonics`), window
   `max(0.5·BIN_W, 0.015 · k · f0)` (`harm_rel`); `above_floor` = amplitude ≥ `3 × noise` (`harm_snr`).
   **Sidebands** only for the two families the spec gives a spacing: BPFI ± shaft, BSF2 ± FTF
   (`sideband_spacing`); a pair counts only if **both** sides are ≥ 3× noise (one-sided sidebands add
   nothing — `test_bpfi_sidebands_credit_both_sides_only`). `score = (Σ harmonic peaks + Σ sideband pairs) / noise`.
   The reported `f0` is the **measured k = 1 peak** when that harmonic is above the floor (ties on flat
   spectra make the grid candidate meaningless); a family whose k = 1 is below the floor keeps the raw
   grid value — which is why losing families in `results_v3.json` show off-grid `f0`s like 147.29 Hz.
4. **Exclusion** (the B2_5 lesson): take the top family's `f0`; mask `k·f0 ± m·f_shaft` for `k = 1..5`,
   `m = −2..2` (`exclusion_harmonics`, `exclusion_sidebands`); re-score every other family with those bins
   zeroed; record what each lost as `excluded_hz`. Why: at 37.5 Hz, BPFO + 1× shaft sideband
   (115.6 + 37.5 = 153.1 Hz) lands inside BSF2's fundamental window and used to give BSF2 a fake harmonic.
5. `aggregate(locs)` over the last `loc_last = 5` windows (≤ k): per family the **median** of score,
   harmonics above floor, sideband pairs.
6. `decide(agg)`:
   - eligibility: FTF needs ≥ 3 harmonics (`cage_min_harmonics`), any other family ≥ 1 (`margin_min_harmonics`);
   - top = highest median score; not eligible → `TOP_{fam}_FAILS_COHERENCE_{n}`;
   - `score < 9.0` (`family_present` ≈ three harmonics each 3× floor) → `TOP_{fam}_{score}_BELOW_9`;
   - runner-up = best *eligible* other family; `top < 1.5 × runner` (`margin`) → `NO_MARGIN_{top}_{s}_vs_{runner}_{s}`;
   - harmonics < 3 (`element_min_harmonics`, the v3 harmonic floor) → `INSUFFICIENT_HARMONICS_{fam}_{n}_NEED_3`;
   - top is FTF → `CAGE_CONSISTENT` (the cage is **never** called as an element);
   - else `SUSPECTED_OUTER | SUSPECTED_INNER | SUSPECTED_BALL` (`ELEMENT = BPFO→outer, BPFI→inner, BSF2→ball, FTF→cage`).

### 12.9 The engine's status tree (`engine.py`)

| condition, in order | status | refusal reason(s) | draft |
|---|---|---|---|
| `not signal_ok` or `"ALL"` in blocks | `BLOCKED_SIGNAL` | the trust notes (e.g. `SAMPLE_COUNT_100_EXPECTED_32768`, `ACQUISITION_UNVERIFIED`) | `RECAPTURE_SIGNAL` |
| `"BASELINE_COMPARISON"` in blocks (regime) | `BLOCKED_BASELINE` | `REGIME_UNVERIFIED` | `ANALYST_REVIEW` |
| Stage 1 state `BASELINE` (k ≤ 10) | `BLOCKED_BASELINE` | `BASELINE_ACCUMULATING_{k}_OF_10` | — |
| not persistent, state `NORMAL`/`WATCH` | `NO_ANOMALY_DETECTED` | `SINGLE_GROUP_{g}_NOT_FUSED` if one group moved | — |
| not persistent, `ABNORMAL` or early indicators | `WATCH_EARLY` | `ABNORMAL_NOT_PERSISTENT_RUN_{r}_OF_3` or `EARLY_INDICATORS_{groups}` | — |
| persistent, `"LOCALIZATION"` in blocks | `ABNORMAL_LOCATION_UNCONFIRMED` | `LOCALIZATION_BLOCKED_SPEED_UNVERIFIED` / `…_GEOMETRY_UNVERIFIED` | `MEASURE_SHAFT_SPEED` / `VERIFY_BEARING_GEOMETRY` |
| persistent, `SUSPECTED_*`, View A supports | **`ANALYST_REVIEW_REQUIRED`** | — | `INSPECTION_WORK_ORDER` (suspected element + all locators) |
| persistent, `SUSPECTED_*`, View A does not | `ABNORMAL_LOCATION_UNCONFIRMED` | `VIEW_A_NO_SUPPORT_{family}` | `ANALYST_REVIEW` |
| persistent, `CAGE_CONSISTENT` | `ABNORMAL_LOCATION_UNCONFIRMED` | `CAGE_CONSISTENT_NOT_CALLED` | `ANALYST_REVIEW` |
| persistent, anything else | `ABNORMAL_LOCATION_UNCONFIRMED` | `BEARING_PATTERN_LOCATION_UNCONFIRMED` + the `decide` reasons | `ANALYST_REVIEW` |

Order analysis (Stage 2) runs only when `signal_ok` and neither `ORDER_ANALYSIS` nor `ALL` is blocked;
when it is withheld the payload shows `shaft_hz_measured = null`, `explained_peaks = []`,
`predicted_hz = {}` — we do not print predictions derived from a speed we just declared untrusted.
`shaft_hz_used_for_prediction` is always the setpoint. `analysis_id = "{bearing}-{k:04d}-{sha8}"`.
`series["ordinary"]`, `series["envelope"]` are `(freqs, amp)`; `series["stage1"]` is the per-window
Stage-1 history for the trend plot.

**Locators.** `{asset_id}|w{window}|{sha8}|{view}|{freq:.2f}Hz[|h{k}][|sb{m:+d}]` — envelope harmonics
carry `|h{k}`, sideband peaks `|h{k}|sb-1` / `|sb+1`, View A harmonics `|h{k}`, explained shaft peaks
`|h{order}`, unexplained residuals no `|h`. `contract.locator` raises if asked for `|sb` without `|h`.
The same string appears in the JSON, the UI and the model's draft — a claim you can grep.

### 12.10 The contract and the review (`contract.py`, `review.py`)

Fourteen fields, in order: `analysis_id, asset_id, source_window, input_trust, anomaly_evidence,
machine_components, ordinary_spectrum_evidence, envelope_evidence, candidate_families, suspected_location,
status, refusal_reasons, inspection_draft, human_review`. `status` is a closed `Literal` of the eight
states; `INSPECTION_APPROVED` / `INSPECTION_REJECTED` are reachable only through `review.apply_decision`.
`EMPTY` is a valid all-blocked payload (`BLOCKED_SIGNAL`, blocks `["ALL"]`). Stephen's
`bw_product/contract_shape.py` is a field-for-field transcription; the final review diffed them — identical.

`apply_decision(result, "APPROVE"|"REJECT"|"DEFER", reason, store)`: raises unless
`status == "ANALYST_REVIEW_REQUIRED"` (same rule as the Mongo store); calls `store.record(...)` first;
APPROVE → `INSPECTION_APPROVED`, REJECT → `INSPECTION_REJECTED`, DEFER keeps the status; every evidence
field is retained (a rejected draft is still a record). Every `InspectionDraft` carries `not_claimed`:
no RUL, no severity scale from peak height, no part number / outage window / repair schedule, and
"`NO_ANOMALY_DETECTED` means no persistent change in the evidence we have", not "healthy".

### 12.11 The evaluator and the numbers (`eval/`)

`eval/run_eval.py` walks `eval/ground_truth.json` (15 bearings, documented failure elements, file counts),
asserts the record count, and analyzes **the last record** of each bearing with `xjtu_context`
(trusted inputs — the trust-block paths are not exercised by the evaluator). Verdict rules:

| status at the last window | verdict |
|---|---|
| `ANALYST_REVIEW_REQUIRED` and suspected ∈ documented | `CORRECT` |
| `ANALYST_REVIEW_REQUIRED` and suspected ∉ documented | `WRONG` |
| `ABNORMAL_LOCATION_UNCONFIRMED` with `CAGE_CONSISTENT_NOT_CALLED` | `CORRECT_CONSISTENT` if "cage" documented, else `WRONG_CONSISTENT` (counted as wrong) |
| any other `ABNORMAL_LOCATION_UNCONFIRMED` | `ABSTAIN` |
| anything else with no onset | `MISSED` |

It writes `version`, `thresholds_sha256`, `run_at`, `wall_s`, the summary and every per-bearing record to
`eval/results_v3.json`; the freeze doc `eval/frozen_thresholds_v3.md` was committed (`3bda3b7`) **before**
`run_eval.py` existed, with the expectations written down; the run is `978f025`.

**v3, 15/15, no exclusions, 7 s wall (cache warm): 0 wrong · 10 correct · 1 cage-consistent (B1_4) ·
4 abstain (B2_1, B2_3, B2_4, B3_2 — all on the harmonic floor, `INSUFFICIENT_HARMONICS_*_2_NEED_3`) ·
0 missed · View A abstains 0.** Predeclared and held: B2_3 (v2's wrong call) → abstain; B2_4 / B3_2 →
abstain on the floor; B2_5 → outer via exclusion; B3_3 → inner via sidebands. Every call Stage 3 made passed
View A. Bearing1_3 at window 158: BPFO score 30.1, three harmonics, `f0 = 107.03 Hz`, `view_a_supports = BPFO`,
onset 59 — the RED reference the freeze doc named in advance.

**Onsets and lead time** (§11 honesty note has the full statement): lead = files − onset, onset = first of
three consecutive one-sided abnormal windows after the ten-window baseline. 15/15: min 11 / median 99 /
max 2519 min (median 98 over the 14 without Bearing3_5, whose baseline is contaminated — rms rises 14.8 MAD
inside windows 1–10 — so its onset 11 is the structural floor and gets no lead time of its own).
`early_onset_first_30pct = 7`: seven bearings fire inside the first 30 % of their life — long, slow
degradations (Bearing3_1: onset 19 of 2538 with a clean baseline), reported, not tuned.

**What it is not:** not a false-alarm rate (every XJTU-SY bearing runs to failure, so there is no healthy
run to be wrong on — what we can say is that persistence absorbed 12 `WATCH_EARLY` and 3 isolated abnormal
windows before Bearing1_3's onset without a false persistent fire); not RUL; not severity; one fault class.

## 13. Engine-lane Q&A — what a judge or a vibration engineer will ask

Answers are short on purpose; the numbers are in §12. Say the number, name the file, stop.

**"Walk me through one window."** Trust gate (five signal checks + four trust inputs) → Stage 1 replays
windows 1..k against the first ten with one-sided robust z, ≥ 2 of 4 groups, 3 consecutive → if
persistent, Stage 2 labels shaft orders in the ordinary spectrum → Stage 3 scores the four families in
the envelope spectrum over the last five windows, excludes the winner's harmonics/sidebands from the
others, applies floor, margin, harmonic floor → View A must find ≥ 1 unexplained harmonic of the same
`f0` in the ordinary spectrum → `ANALYST_REVIEW_REQUIRED` with an inspection draft and locators, or an
`ABNORMAL_LOCATION_UNCONFIRMED` with the reason.

**"Why median and MAD instead of mean and standard deviation?"** Ten windows, and an outlier in the baseline
would inflate σ and hide the very change we look for. Median/MAD are robust; 0.6745 rescales MAD to σ for
Gaussian data so "z ≥ 5" means what people expect.

**"Why 5? Why 10 windows? Why 3 consecutive? Why 2 groups?"** All four are v3 thresholds frozen before the
run, in `thresholds.py`, and they were set from the prep replay on Bearing1_3, not tuned on the 15 results.
5 is a conservative robust-z alarm; 10 windows is the shortest baseline whose MADs were tight (< 3 % of
median except kurtosis); 3 consecutive is persistence — 12 `WATCH_EARLY` and 3 isolated abnormals before
onset on Bearing1_3 were all absorbed; 2 groups is fusion — one family of indicators alone is an
early-warning (`WATCH_EARLY`), not an anomaly.

**"Why one-sided?"** Because two-sided was falsified by our own build test: a pure tone at 5× RMS lowers
crest and kurtosis, two groups move, a synthetic fake looks abnormal. Fault physics says indicators rise.
One-sided, the fake stays `WATCH`. The cost is real and reported: seven onsets moved later.

**"So what is your lead time?"** v3, files − onset, 15/15: min 11 / median 99 / max 2519 min; median 98 if
you exclude Bearing3_5, which we do for any per-bearing claim because its baseline is already damaged
(rms 14.8 MAD inside windows 1–10). Not RUL — it is how many one-minute records remained after our onset
in a run-to-failure dataset.

**"Bearing3_5 fires at the earliest possible window — isn't that a failure of the method?"** It is a
limitation of a ten-window *self* baseline on a bearing that is already degrading at record 7; we say so,
we quote no lead time for it, and it still gets the element right (outer). A fleet or commissioning
baseline would fix it; we did not have one and did not invent one.

**"Why 2–4 kHz? Why not the kurtogram?"** We run both. The spectral-kurtosis sweep (1–12.2 kHz, 4/2/1 kHz
bands) elected 11.5–12 kHz on Bearing1_3 — a band whose BPFO family is 8× weaker than 2–4 kHz. Kurtosis
measures spikiness, not demodulation quality; the trap is in the literature (Randall & Antoni 2011). So
the band that shows the more coherent harmonic family wins, tie to the fixed band. Source: `families.py`.

**"Why three harmonics? Why 3× the floor? Why 1.5 margin?"** Three harmonics above 3× the median floor is
the classic "a family, not a peak" rule (`family_present = 9` ≈ 3 × 3). Margin 1.5 against the best
*eligible* competitor is what prevented inner-vs-ball coin flips in v2. The v3 change was to make the
3-harmonic floor apply to *every* element call — it removed the one wrong call (B2_3, a fractured cage
putting 2 BPFO harmonics in the envelope) at the predeclared cost of two v2 correct calls becoming
abstentions (B2_4, B3_2). We took that trade on purpose and wrote it down before the run.

**"Why sidebands, and only for BPFI and 2×BSF?"** Spec §2: an inner-race defect passes through the load
zone once per shaft turn (shaft-spaced sidebands); a rolling-element defect moves with the cage (FTF-spaced).
Outer-race and cage have no such modulation in the model. A pair counts only when both sides are above
floor. It is what closed B3_3 (inner).

**"What is 'exclusion'?"** Stage-2 discipline applied inside Stage 3: once a family wins, its harmonics
`k = 1..5` and their `±2` shaft sidebands are masked before the other families are rescored. On condition 2,
BPFO + 1× shaft (153.1 Hz) sat in 2×BSF's fundamental window and gave it a fake harmonic; B2_5 went from
abstain to outer. The contract shows what each family lost as `excluded_hz`.

**"You measured 34.7 Hz but predict from 35 Hz — why not use the measured speed?"** Hard cut in the spec
(§11): no speed inference feeds a fault frequency, because measured speed from the same spectrum you are
trying to diagnose is circular when it is wrong. The measured 1× is used for exactly one thing — anchoring
the 0.5 % windows that label shaft orders, so 3× shaft (105 Hz) cannot swallow BPFO (107.9 Hz). Both
numbers are in `machine_components`, and the 0.8 % slip is exactly why the ±2 % tolerance exists.

**"Why is View A a gate and not a score?"** Two independent views — ordinary spectrum and envelope — must
agree on the same `f0`; that is the contract's evidence rule. A gate can only turn a call into an
abstention. In the frozen run it cost nothing (0 View A abstains), which we report as a finding, not a
design virtue.

**"Why is the cage never called?"** FTF is 13.5 Hz; its harmonics are a bin or two apart and inside every
other family's tolerance; a cage family is *consistent with* a cage problem, not proof of one. We return
`CAGE_CONSISTENT_NOT_CALLED` and ask an analyst. B1_4 (documented cage) lands exactly there.

**"What if the shaft speed is wrong or missing?"** `speed` → `UNVERIFIED`: order analysis and localization
are blocked, Stage 1 still runs, status is `ABNORMAL_LOCATION_UNCONFIRMED` with
`LOCALIZATION_BLOCKED_SPEED_UNVERIFIED`, the task is `MEASURE_SHAFT_SPEED`, and the payload withholds
`predicted_hz` and `shaft_hz_measured` — we do not print numbers derived from an input we just refused.
Geometry unknown → same shape with `VERIFY_BEARING_GEOMETRY` (demo step 7). Bad signal → `BLOCKED_SIGNAL`
+ `RECAPTURE_SIGNAL`.

**"Why is Stage 1 fault-agnostic?"** So we do not find 107.9 Hz because we went looking for it. The nine
indicators are RMS, peak-to-peak, crest, kurtosis, four band energies, envelope energy. Localization is only
allowed after a persistent, fault-agnostic change.

**"How do you test without failure data?"** `tests/synth.py`: `synth_fault(f_imp)` is the textbook model —
an impulse train at the fault rate, each impulse ringing a 3 kHz resonance with a 1 ms decay, in white
noise. 56 fast tests use that and pure tones; 4 slow tests pin the real Bearing1_3 numbers (onset 59,
BPFO, `f0` within 1.5 Hz of 107.0, three harmonics, the geometry-unverified path).

**"What does 0 wrong calls mean with n = 15?"** Exactly that: on the fifteen documented bearings of
XJTU-SY, with thresholds frozen before the run and every bearing counted, no element call was wrong;
ten were right, one cage case was reported as consistent, four abstained with a reason code. Small n, no
exclusions, committed verbatim. We do not extrapolate it to a rate.

**"What is the sha256 for?"** `thresholds_sha256()` hashes `thresholds.py`; it is printed in the run and
stored in `results_v3.json` (`59a9d901…`). The freeze doc carries the same hash and precedes the evaluator
in git history. If the thresholds had been touched after the freeze, the hashes would not match.

**"Why is it all CPU?"** 32 768 samples: a Butterworth, a Hilbert and an FFT are sub-millisecond work;
a full `analyze(158)` on Bearing1_3 is 0.4 s with a warm feature cache (≈15 ms per window to rebuild it cold), and the 15-bearing evaluator ran in 7 s.
Determinism matters more than speed for a system that recommends taking a machine offline — same input,
same JSON, every time.

**"What can it not do?"** One fault class; no unbalance, misalignment, looseness, gear or electrical
faults; no RUL; no severity; nothing above 12.8 kHz; horizontal channel only; units unproven so we never
say velocity; no false-alarm rate from this dataset. It tells an analyst where to look and leaves the
decision a human's.

**v1 → v2 → v3 in one breath:** v1 trusted the kurtogram and used a flat ±1.5 Hz window (11 % of FTF) —
13 abstentions; v2 checked the band by coherence and made windows resolution-aware — 10 correct, 1 wrong;
v3 froze one-sided z, the 3-harmonic floor, scored sidebands, exclusion and the View A gate — 10 correct,
0 wrong, 4 abstentions, all predeclared.

---

*Performance figures cited are drawn from community reports and vendor documentation for this
hardware class and should be treated as indicative rather than measured on our specific
configuration. Measure on the box and report what you measure.*

*Checked 2026-08-21 against vendor docs, GitHub issues, the Hugging Face model card, and the
bearing-diagnostics literature — §4, §6, §7, §8 and §9 were corrected where they had drifted.
Sources and the full verified / changed / unknown table are in `LOOKUPS_2026-08-21.md`. The v3
engine rules, the vocabulary, and the onset-semantics caveat in §9–§11 follow the approved review
in `docs/REVIEW_2026-08-21.md` and the coordination decisions in `PLAN.md` (D1–D10).
Updated 2026-08-21 evening: §10 locator format follows the `⚠️ CONTRACT` clarification (`|h`
optional for unexplained residual peaks); §11 "How much existed before today" now names the
Friday-evening scaffolds on both lanes (disclosed in PLAN.md 1.1–1.3 and 2.1–2.7 Notes).
Updated 2026-08-22 00:5x: §11 honesty note carries the reconciled onset semantics and the quotable v3
lead-time statement (Task 14, `eval/onset_inspection.md`); §12 (engine module by module) and §13
(engine-lane Q&A) added — every constant read from `bearing_witness/` at the frozen v3 state, every
evaluator number from `eval/results_v3.json` / `eval/run_v3_output.txt`; the 12 + 3 pre-onset counts and
the 0.4 s timing were re-measured on Bearing1_3 while writing.*
