# Tamil Thirukkural Doc-QA — MLOps Project

An end-to-end Retrieval-Augmented system that reads a Tamil document (the
*Thirukkural*, 164 pages) and answers natural-language questions about it,
served through a FastAPI backend with a simple web UI, built and deployed
via a full CI/CD pipeline: **PyCharm → GitHub → Jenkins → Docker Hub →
Kubernetes (Docker Desktop)**.

---

## Table of Contents

1. [Architecture Overview](#architecture-overview)
2. [Project Structure](#project-structure)
3. [The Data Pipeline](#the-data-pipeline)
4. [The API & UI](#the-api--ui)
5. [Local Development (PyCharm)](#local-development-pycharm)
6. [Containerization (Docker)](#containerization-docker)
7. [Source Control (GitHub)](#source-control-github)
8. [CI/CD (Jenkins)](#cicd-jenkins)
9. [Deployment (Kubernetes)](#deployment-kubernetes)
10. [Accessing the Application](#accessing-the-application)
11. [The Full MLOps Flow, End to End](#the-full-mlops-flow-end-to-end)
12. [Problems Hit & Fixes (Lessons Learned)](#problems-hit--fixes-lessons-learned)
13. [Possible Next Steps](#possible-next-steps)

---

## Architecture Overview

```
┌─────────────┐     ┌──────────┐     ┌─────────┐     ┌────────────┐     ┌──────────────┐
│   PyCharm   │────▶│  GitHub  │────▶│ Jenkins │────▶│ Docker Hub │────▶│  Kubernetes  │
│ (local dev) │ git │  (repo)  │ CI  │ (build/ │push │  (image    │pull │ (Docker      │
│             │push │          │trig.│  test)  │     │  registry) │     │  Desktop)    │
└─────────────┘     └──────────┘     └─────────┘     └────────────┘     └──────────────┘
                                                                                 │
                                                                                 ▼
                                                                        kubectl port-forward
                                                                                 │
                                                                                 ▼
                                                                          Browser UI
                                                                      (Tamil Q&A page)
```

**Why RAG, not fine-tuning:** Rather than fine-tuning a language model on
the document (which changes style, not factual recall), this project uses
**Retrieval-Augmented Generation**: the document is OCR'd, chunked,
embedded into vectors, and indexed with FAISS. At query time, the
question is embedded and matched against the index to retrieve the most
relevant passages, which are returned directly (and could be fed to an
LLM for generation in a future iteration).

---

## Project Structure

```
tamil-doc-qa/
├── src/
│   ├── ocr.py              # PDF pages → OCR'd text (Tesseract, tam+eng)
│   ├── normalize.py        # Unicode normalization + quality filtering
│   ├── chunk.py             # Normalized text → overlapping chunks
│   ├── index.py             # Chunks → embeddings → FAISS index
│   ├── retrieve.py          # Query → embed → search → ranked results
│   ├── api.py                # FastAPI app (serves API + UI)
│   ├── run_pipeline.py      # Chains ocr→normalize→chunk→index
│   ├── quality_filter.py    # Tamil-ratio based page quality filter
│   └── static/
│       └── index.html       # Simple web UI (vanilla HTML/JS)
├── data/
│   ├── Thirukkural_with_meaning.pdf   # Source document
│   ├── index.faiss           # Built vector index (committed)
│   └── meta.json              # Chunk metadata (committed)
├── tests/
│   └── test_api.py           # pytest smoke tests for the API
├── k8s/
│   ├── deployment.yaml       # K8s Deployment + Service
│   └── indexing-job.yaml     # K8s Job to rebuild the index
├── Dockerfile.server          # Serving image (API + pre-built index)
├── Dockerfile.indexer         # Indexing image (OCR → index pipeline)
├── Jenkinsfile                 # CI/CD pipeline definition
├── requirements.txt
├── pytest.ini
└── .gitignore
```

---

## The Data Pipeline

The source PDF uses **glyph-mapped custom fonts** (common in older Tamil
DTP/typesetting tools) — the embedded "text" layer does not map to real
Unicode characters, so direct text extraction (e.g. via PyMuPDF) produces
garbage. The pipeline therefore **renders each page as an image and OCRs
it**, rather than extracting text directly.

| Stage | Script | Input → Output | Notes |
|---|---|---|---|
| 1. OCR | `src/ocr.py` | PDF pages → `data/raw_ocr.jsonl` | Tesseract, `lang="tam+eng"` (bilingual document), 300 DPI page rendering via PyMuPDF |
| 2. Normalize + Filter | `src/normalize.py` | → `data/normalized.jsonl` + `data/normalized_dropped.jsonl` | Unicode NFC normalization, ZWJ/ZWNJ cleanup, and a **Tamil-ratio quality filter** that drops pages that are mostly OCR noise (decorative pages, misread symbols) rather than real Tamil content |
| 3. Chunk | `src/chunk.py` | → `data/chunks.jsonl` | Character-count chunking (~1500 chars, 200 overlap), tracks page numbers per chunk for citation |
| 4. Index | `src/index.py` | → `data/index.faiss`, `data/meta.json` | Embeds chunks with `intfloat/multilingual-e5-large` via **fastembed** (ONNX runtime — see [Problems Hit](#problems-hit--fixes-lessons-learned) for why not PyTorch), builds a FAISS flat inner-product index |
| 5. Retrieve | `src/retrieve.py` | query → ranked chunks | Embeds the query with the `query:` e5 prefix, searches the FAISS index, returns top-k chunks with page numbers and scores |

**Run the full pipeline locally:**

```bash
python src/ocr.py
python src/normalize.py
python src/chunk.py
python src/index.py
python src/retrieve.py   # test query
```

Or as a single step:

```bash
python src/run_pipeline.py
```

### Quality filtering

A page's **Tamil-character ratio** (fraction of non-whitespace characters
in the Tamil Unicode block, U+0B80–U+0BFF) is used to drop pages that are
mostly OCR noise rather than real content:

```python
def tamil_ratio(text: str) -> float:
    tamil_chars = len(re.findall(r'[\u0B80-\u0BFF]', text))
    total_chars = len(re.sub(r'\s', '', text))
    return tamil_chars / total_chars if total_chars else 0.0
```

Dropped pages are written to a separate file (`normalized_dropped.jsonl`)
rather than silently discarded, so they can be reviewed.

---

## The API & UI

**`src/api.py`** is a FastAPI app with three routes:

| Route | Method | Purpose |
|---|---|---|
| `/health` | GET | Liveness/readiness check — returns `{"status": "ok", "chunks_loaded": N}` |
| `/query` | POST | Accepts `{"question": "...", "k": 5}`, returns ranked relevant chunks with page numbers and scores |
| `/` | GET | Serves the static web UI |

**`src/static/index.html`** is a single, dependency-free HTML/JS page
(no build step) that calls `/query` and renders results — Tamil-language
labels, loading state, and result cards showing page number, relevance
score, and the kural/meaning text.

Run locally:

```bash
uvicorn src.api:app --reload --port 8000
```

Open `http://localhost:8000` to use the UI directly, or call the API:

```bash
curl -X POST http://localhost:8000/query \
  -H "Content-Type: application/json" \
  -d '{"question": "நட்பு பற்றி குறள் என்ன கூறுகிறது"}'
```

---

## Local Development (PyCharm)

1. Create and activate a venv, install dependencies:
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```
2. Install Tesseract (system dependency, not pip-installable):
   ```bash
   brew install tesseract tesseract-lang
   ```
3. Run the pipeline scripts in order (see [The Data Pipeline](#the-data-pipeline)).
4. Run tests:
   ```bash
   pip install pytest httpx
   pytest tests/
   ```
5. Run the API locally:
   ```bash
   uvicorn src.api:app --reload --port 8000
   ```

---

## Containerization (Docker)

Two separate images, with different lifecycles:

- **`Dockerfile.server`** — the serving image. Installs Tesseract (kept
  in case of future on-the-fly OCR needs), Python dependencies, and
  **pre-downloads the embedding model at build time** so containers start
  near-instantly rather than fetching ~1GB from Hugging Face Hub on every
  run. Copies `src/` and the **already-built** `data/index.faiss` +
  `data/meta.json`.
- **`Dockerfile.indexer`** — a separate image that runs the full
  `ocr → normalize → chunk → index` pipeline from the source PDF, for
  rebuilding the index as a Kubernetes Job (`k8s/indexing-job.yaml`)
  without needing to rebuild the server image.

Build and test locally before pushing through CI:

```bash
docker build -f Dockerfile.server -t tamil-doc-qa-server:local .
docker run -p 8000:8000 tamil-doc-qa-server:local
curl http://localhost:8000/health
```

---

## Source Control (GitHub)

- Repo: `github.com/neelamegan/tamil-doc-qa`
- `.gitignore` excludes the venv, intermediate pipeline artifacts
  (`raw_ocr.jsonl`, `normalized.jsonl`, `chunks.jsonl` — regenerable), and
  OS/editor cruft.
- `data/index.faiss`, `data/meta.json`, and the source PDF **are
  committed** — this keeps the repo immediately buildable/servable
  without first running the OCR pipeline (which is slow, ~minutes for
  164 pages). The indexer image/Job exists for when the index needs to
  be rebuilt from a changed source document.
- GitHub credentials for Jenkins are a fine-grained Personal Access
  Token with `Contents: Read` + `Metadata: Read` scopes, stored in
  Jenkins Credentials.

---

## CI/CD (Jenkins)

Jenkins is set up as a **Multibranch Pipeline** job pointed at the GitHub
repo, auto-discovering the `Jenkinsfile` at the repo root.

**Pipeline stages:**

| Stage | What it does |
|---|---|
| **Checkout** | Pulls the triggering commit from GitHub |
| **Install & Test** | Creates a venv, installs dependencies, runs `pytest tests/` |
| **Build Image** | `docker build` the server image, tags it with both the Git commit SHA and `latest` |
| **Smoke Test Container** | Runs the built image, **polls `/health` until it responds** (rather than a fixed sleep — model load time varies), dumps container logs on failure |
| **Push to Docker Hub** | Logs in via injected credentials, pushes both tags |
| **Deploy to Kubernetes** | `kubectl apply`s the manifests, updates the Deployment's image, waits for rollout to complete |

```groovy
pipeline {
    agent any
    environment {
        DOCKERHUB_USER = "neelamegan"
        IMAGE = "tamil-doc-qa-server"
        PATH = "/usr/local/bin:${env.PATH}"
    }
    stages {
        stage('Checkout') { steps { checkout scm } }

        stage('Install & Test') {
            steps {
                sh '''
                    python3 -m venv venv
                    . venv/bin/activate
                    pip install -r requirements.txt pytest httpx
                    pytest tests/
                '''
            }
        }

        stage('Build Image') {
            steps {
                sh "docker build -f Dockerfile.server -t ${DOCKERHUB_USER}/${IMAGE}:${GIT_COMMIT} ."
                sh "docker tag ${DOCKERHUB_USER}/${IMAGE}:${GIT_COMMIT} ${DOCKERHUB_USER}/${IMAGE}:latest"
            }
        }

        stage('Smoke Test Container') {
            steps {
                sh '''
                    docker rm -f test-container || true
                    docker run -d --name test-container -p 8001:8000 neelamegan/tamil-doc-qa-server:${GIT_COMMIT}
                    for i in $(seq 1 30); do
                        if curl -sf http://localhost:8001/health > /dev/null; then
                            break
                        fi
                        if [ "$i" -eq 30 ]; then
                            docker logs test-container
                            exit 1
                        fi
                        sleep 2
                    done
                    curl -f http://localhost:8001/health
                    docker stop test-container && docker rm test-container
                '''
            }
        }

        stage('Push to Docker Hub') {
            when { branch 'main' }
            steps {
                withCredentials([usernamePassword(credentialsId: 'dockerhub-creds', usernameVariable: 'DHUB_USER', passwordVariable: 'DHUB_PASS')]) {
                    sh '''
                        echo "$DHUB_PASS" | docker login -u "$DHUB_USER" --password-stdin
                        docker push neelamegan/tamil-doc-qa-server:${GIT_COMMIT}
                        docker push neelamegan/tamil-doc-qa-server:latest
                    '''
                }
            }
        }

        stage('Deploy to Kubernetes') {
            when { branch 'main' }
            steps {
                sh '''
                    kubectl config use-context docker-desktop
                    kubectl apply -f k8s/deployment.yaml
                    kubectl set image deployment/tamil-doc-qa-server server=neelamegan/tamil-doc-qa-server:${GIT_COMMIT}
                    kubectl rollout status deployment/tamil-doc-qa-server --timeout=120s
                '''
            }
        }
    }
    post {
        failure { echo 'Build failed — check logs above.' }
    }
}
```

**Trigger:** a GitHub webhook (or periodic SCM polling as fallback) kicks
off a build on every push to `main`.

---

## Deployment (Kubernetes)

Target: **Docker Desktop's built-in Kubernetes** (single-node, local).

**`k8s/deployment.yaml`** defines:

- A **Deployment** (`tamil-doc-qa-server`) with 2 replicas, readiness and
  liveness probes against `/health`, and resource requests/limits.
- A **Service** (`tamil-doc-qa-service`, `ClusterIP`) exposing port 80 →
  container port 8000.

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: tamil-doc-qa-server
spec:
  replicas: 2
  selector:
    matchLabels: { app: tamil-doc-qa }
  template:
    metadata:
      labels: { app: tamil-doc-qa }
    spec:
      containers:
        - name: server
          image: neelamegan/tamil-doc-qa-server:latest
          ports: [{ containerPort: 8000 }]
          readinessProbe:
            httpGet: { path: /health, port: 8000 }
            initialDelaySeconds: 10
          livenessProbe:
            httpGet: { path: /health, port: 8000 }
            initialDelaySeconds: 15
          resources:
            requests: { cpu: "500m", memory: "1Gi" }
            limits: { cpu: "1", memory: "2Gi" }
---
apiVersion: v1
kind: Service
metadata:
  name: tamil-doc-qa-service
spec:
  selector: { app: tamil-doc-qa }
  ports: [{ port: 80, targetPort: 8000 }]
  type: ClusterIP
```

**`k8s/indexing-job.yaml`** defines a one-shot **Job** running the
indexer image, for rebuilding the FAISS index from the source document
independently of the server deployment.

---

## Accessing the Application

Since the Service is `ClusterIP` (internal-only), access it from your
Mac via `kubectl port-forward`:

```bash
kubectl config use-context docker-desktop
kubectl port-forward svc/tamil-doc-qa-service 8090:80
```

Then open **`http://localhost:8090`** in a browser — the Tamil Q&A UI,
now served from a pod running in the Kubernetes cluster (not a
standalone `docker run`).

```bash
curl http://localhost:8090/health
curl -X POST http://localhost:8090/query \
  -H "Content-Type: application/json" \
  -d '{"question": "நட்பு பற்றி குறள் என்ன கூறுகிறது"}'
```

**Verifying the deployment:**

```bash
kubectl get deployments
kubectl get pods
kubectl get svc tamil-doc-qa-service
kubectl rollout status deployment/tamil-doc-qa-server
kubectl get pods -o jsonpath='{.items[*].spec.containers[*].image}'
```

**Optional — avoid port-forwarding each time:** change the Service
`type` to `LoadBalancer` in `k8s/deployment.yaml`; Docker Desktop
auto-binds `LoadBalancer` services to `localhost`.

---

## The Full MLOps Flow, End to End

```
1. Edit code in PyCharm
2. git add / commit / push → GitHub
3. GitHub webhook → Jenkins triggers build
4. Jenkins: Checkout → Install deps → pytest
5. Jenkins: docker build (server image)
6. Jenkins: smoke-test the built container (poll /health)
7. Jenkins: docker push → Docker Hub (commit-SHA tag + latest)
8. Jenkins: kubectl apply + kubectl set image → Kubernetes
9. Kubernetes: rolling update, 2 replicas, readiness/liveness probes
10. kubectl port-forward → browser → live Tamil Q&A UI
```

Every push to `main` that passes tests and the smoke test automatically
reaches a running pod — this is the actual "MLOps" loop: code changes are
tested, containerized, and deployed with no manual Docker/kubectl steps
required.

---

## Problems Hit & Fixes (Lessons Learned)

A record of the real issues hit while building this, and how they were
resolved — useful if extending this project or building a similar one.

| Problem | Root Cause | Fix |
|---|---|---|
| PyMuPDF extracted garbled text (`[PF"\x01\n\r>L`) | PDF uses **glyph-mapped custom fonts**, not real Unicode Tamil text | Switched to rendering pages as images + OCR instead of text extraction |
| `torch` wouldn't upgrade past 2.2.2 | This Mac's hardware/macOS version caps supported PyTorch wheel versions | Avoided PyTorch-based embeddings entirely; moved to `fastembed` (ONNX Runtime) |
| Segfault during PyTorch embedding forward pass | CPU kernel incompatibility with this hardware | Same fix — `fastembed`/ONNX sidesteps PyTorch entirely |
| `BAAI/bge-m3` not supported in fastembed | fastembed only ships a curated set of ONNX-converted models | Switched to `intfloat/multilingual-e5-large`, with `query:`/`passage:` prefixing as the model expects |
| `MessageFactory has no attribute 'GetPrototype'` | protobuf/TensorFlow version mismatch (TF was being imported unnecessarily by `transformers`) | Pinned `protobuf==3.20.3`; set `USE_TF=0` |
| ONNX Runtime: "External data path validation failed" in Docker | Hugging Face Hub's symlink-based caching doesn't survive Docker's overlay filesystem | Set `HF_HUB_DISABLE_SYMLINKS=1`; pre-download the model at Docker **build** time so it's baked into the image |
| `python: command not found` in Jenkins | Jenkins (native macOS install) has its own `PATH`, separate from the interactive terminal; `python` isn't aliased to `python3` | Used `python3` explicitly in the Jenkinsfile |
| `docker: command not found` / `kubectl: command not found` in Jenkins | Same `PATH` issue — Docker/kubectl installed in `/usr/local/bin`, not on Jenkins' default `PATH` | Added `PATH = "/usr/local/bin:${env.PATH}"` to the Jenkinsfile's `environment` block |
| `pytest` failed: `No module named 'src'` | pytest didn't know the project root should be importable | Added `pyproject.toml`/`pytest.ini` with `pythonpath = ["."]`; added `src/__init__.py` |
| `FileNotFoundError: data/index.faiss` in tests/Docker | Pipeline outputs were saved under `src/data/` but code expected root-level `data/` | Standardized on root-level `data/`; moved files to match |
| `git push` rejected (non-fast-forward) | GitHub auto-created a template commit (README) when the repo was created, diverging from local history | `git push --force` to make local history (the real project) the source of truth — safe since it was a brand-new, non-collaborative repo |
| Jenkins CI failed: `could not open data/index.faiss` | `data/index.faiss`/`meta.json` were `.gitignore`'d, so a clean Jenkins checkout didn't have them (even though they existed locally) | Committed the built index artifacts to git so CI/Docker builds are self-contained |
| Docker build: `COPY requirements.txt .` → file not found | The file was referenced in commands but never actually created on disk | Created it explicitly with `cat > requirements.txt << 'EOF' ... EOF` |
| `docker build`: "Dockerfile cannot be empty" | Same pattern — `Dockerfile.server` was referenced but never actually written | Created the file explicitly with its full contents |
| Smoke test: `curl: Recv failure: Connection reset by peer` | Fixed `sleep 15` wasn't always enough — ONNX model load time varies by system load (seen taking up to 100 seconds under load in CI) | Replaced fixed sleep with a **polling loop** (`curl -sf .../health` every 2s, up to 60s), only failing after a genuine timeout |
| Smoke test: "container name already in use" | A previous failed run's container was never cleaned up, and/or a Jenkins "Restart from Stage" replayed an old commit without the fix | `docker rm -f test-container \|\| true` at the start of every smoke test run; always trigger a fresh "Build Now" rather than "Restart from Stage" when testing a new fix |
| UI returned `{"detail":"Not Found"}` after deploy | The K8s pod was still running an older image (crashed on startup from a since-fixed bug, or deploy hadn't actually run with the latest commit) | Verified via `kubectl get pods -o jsonpath=...image` that the deployed image tag matched the latest successful Jenkins build before debugging further |
| `kubectl port-forward` — "address already in use" | Port 8080 was already bound locally (turned out to be Jenkins itself, which defaults to 8080) | Used a different local port (e.g. `8090`) instead of trying to free the conflicting port |

**General pattern worth noting:** most of the Jenkins-specific failures
(`python`, `docker`, `kubectl` "not found") came from the same root
cause — **Jenkins runs as its own process with its own `PATH`**,
separate from an interactive terminal session, even on the same
machine. Any tool that works fine manually needs to be explicitly
reachable from Jenkins' environment (via `PATH` in the Jenkinsfile, or
global Jenkins configuration).

---

## Possible Next Steps

- **Sentence-aware chunking** — current chunking is character-count
  based and sometimes cuts mid-sentence; `indic-nlp-library`-based
  sentence splitting would produce cleaner chunks.
- **LLM generation layer** — currently the system returns retrieved
  passages directly; adding a generation step (via an API-based LLM,
  given this machine's local hardware constraints) would produce
  direct natural-language answers grounded in the retrieved context.
- **Hybrid search** — combine the current dense (embedding) search with
  BM25 keyword search, fused via reciprocal rank fusion, for better
  recall on queries that paraphrase the document's wording.
- **`LoadBalancer` Service** — avoid needing `kubectl port-forward` for
  routine access.
- **Golden evaluation set** — a hand-written set of real Tamil
  questions with known correct answers/pages, to measure
  retrieval quality (recall@k, MRR) systematically rather than
  spot-checking.
- **Cloud deployment** — move from Docker Desktop's local Kubernetes to
  a managed cluster (e.g. GKE, EKS) for real external access.

---

*This document reflects the actual build process of this project,
including the real errors encountered and how each was diagnosed and
fixed — intended as both documentation and a troubleshooting reference
for similar Tamil-language OCR/RAG/MLOps projects.*