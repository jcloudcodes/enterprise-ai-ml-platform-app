# Enterprise AI ML Platform App

This repository contains the FastAPI-based AI inference service used by the Spring Boot dashboard for:
- sentiment analysis
- summarization

The service is deployed to AKS through Jenkins, a shared Jenkins library, GitOps, and Argo CD.

## Repository Role

This app repository is responsible for:
- building the AI inference container image
- pushing the image to Docker Hub
- updating the AI GitOps repository
- bootstrapping the Argo CD `Application`
- syncing the app into AKS

Related repos and paths:
- App repo: `/Users/makutaworldmpm/Desktop/eagunu_2025/jcloudcodes/jenkins/enterprise-ai-ml-platform-app`
- Jenkins shared library: `/Users/makutaworldmpm/Desktop/eagunu_2025/jcloudcodes/jenkins/JavaShared_library`
- AI GitOps repo: `/Users/makutaworldmpm/Desktop/eagunu_2025/jcloudcodes/applications/AI/ai-platform-gitops`
- Spring Boot app repo: `/Users/makutaworldmpm/Desktop/eagunu_2025/jcloudcodes/jenkins/jcloud-springboot-aks-app`

## Current Jenkins Pipeline

This repo now uses a Jenkinsfile with the shared library instead of the old GitLab-only flow.

Current Jenkinsfile:
- `/Users/makutaworldmpm/Desktop/eagunu_2025/jcloudcodes/jenkins/enterprise-ai-ml-platform-app/Jenkinsfile`

Main pipeline flow:
1. Validate tools on the Jenkins agent
2. Run an offline Python compile check
3. Build Docker image
4. Push image to Docker Hub
5. Update the AI GitOps repo
6. Bootstrap the Argo CD app manifest
7. Sync the Argo CD application
8. Verify the AKS environment

Important pipeline config currently in use:
- app name: `ai-inference`
- image repository: `jcloudcodes/enterprise-ai-ml-platform-app`
- GitOps repo: `https://gitlab.com/jcloudcodesgroup/ai-platform-gitops.git`
- Argo CD app: `ai-inference-dev`
- Argo CD server: `argocd.jcloudcodes.com`
- AKS namespace: `ai-platform`
- AKS cluster: `sap-dev-aksdemo1`

## Runtime and Build Notes

Current Dockerfile:
- `/Users/makutaworldmpm/Desktop/eagunu_2025/jcloudcodes/jenkins/enterprise-ai-ml-platform-app/Dockerfile`

Key behaviors:
- base image: `python:3.11-slim`
- installs CPU PyTorch from `https://download.pytorch.org/whl/cpu`
- installs app dependencies from `requirements.txt`
- model prefetch is disabled by default
- Hugging Face models now lazy-load at runtime unless explicitly enabled during build

Current model prefetch control:
```dockerfile
ARG PREFETCH_MODELS=false
```

To force prefetch in a custom build:
```bash
docker build --build-arg PREFETCH_MODELS=true -t jcloudcodes/enterprise-ai-ml-platform-app:local .
```

## AKS and Argo CD Target

Current Argo CD application manifest:
- `/Users/makutaworldmpm/Desktop/eagunu_2025/jcloudcodes/applications/AI/ai-platform-gitops/applications/ai-inference-dev.yaml`

Current target:
- destination namespace: `ai-platform`
- source repo: `https://gitlab.com/jcloudcodesgroup/ai-platform-gitops.git`
- chart path: `charts/ai-inference`
- values file: `../../environments/dev/values.yaml`

## Vault and Jenkins Credentials

The pipeline reuses the existing Vault/AppRole pattern already used by the Spring Boot deployment.

Vault settings currently used by the Jenkinsfile:
- Vault address: `https://jcloudcodes-public-vault-e0a9d77c.e1f8f4d8.z1.hashicorp.cloud:8200`
- Vault namespace: `admin`
- KV mount: `kv/jcloudcodes/java-web-app`
- secret path: `jcloudcodes/java-web-app`

Expected Jenkins credentials:
- `vault-approle-role-id`
- `vault-approle-secret-id`
- `jcloudcodes-dockerhub-cred`
- `gitops-repo-token`

## Issues and Resolutions

### 1. Repo was still GitLab-oriented and had no Jenkinsfile

Problem:
- the repository only had `.gitlab-ci.yml`
- there was no Jenkins shared-library pipeline for this app

Resolution:
- added a Jenkinsfile using the existing shared Jenkins library pieces
- kept the Python-specific test stage local to this repo
- reused shared steps for Docker build/push, GitOps update, Argo CD bootstrap/sync, and verification

### 2. Test stage failed because host Python had no `pip`

Error seen:
```text
/usr/bin/python3: No module named pip
```

Resolution:
- moved the test stage into a public Python container instead of depending on the Jenkins slave Python setup

### 3. Test stage still failed because the Jenkins network could not resolve PyPI reliably

Error seen:
```text
Failed to establish a new connection: [Errno -3] Temporary failure in name resolution
```

Resolution:
- simplified the `Test` stage to an offline validation step
- current test step runs:
```bash
python -m compileall app
```

This keeps a quick syntax/bytecode check without needing package downloads in the test stage.

### 4. Docker build needed special networking on the Jenkins slave

Problem:
- package resolution during Docker build was failing inside the build environment
- the same Jenkins setup had already shown container-level network differences elsewhere

Resolution:
- updated the Jenkins pipeline to request:
```groovy
dockerBuildExtraArgs: '--network host'
```
- updated the shared Docker build helper so extra Docker build args can be passed through

Expected build command shape:
```bash
docker build --network host -t <image> .
```

### 5. Docker image build ran out of disk space

Error seen:
```text
no space left on device
```

Root cause:
- the image was getting much larger when Hugging Face models were downloaded during build
- export of the built layers exhausted local Docker/containerd storage on the Jenkins slave

Resolution:
- changed the Dockerfile so model prefetch is disabled by default
- models now lazy-load at runtime
- prefetch is available only when explicitly requested with `PREFETCH_MODELS=true`

### 6. Jenkins slave disk pressure

Observed warning:
```text
Disk space is below threshold
```

Useful cleanup commands:
```bash
docker system df
docker image prune -af
docker container prune -f
docker builder prune -af
docker system prune -af
```

Remove app image tags safely only if they exist:
```bash
docker images 'jcloudcodes/jcloud-springboot-aks-app' --format '{{.Repository}}:{{.Tag}}' | xargs -r docker rmi -f
docker images 'jcloudcodes/enterprise-ai-ml-platform-app' --format '{{.Repository}}:{{.Tag}}' | xargs -r docker rmi -f
```

### 7. Argo CD could log in but could not read the AI GitOps repo

Error seen:
```text
failed to list refs: authentication required
```

Root cause:
- Jenkins credentials do not automatically become Argo CD repo credentials
- Argo CD itself needed access to:
  `https://gitlab.com/jcloudcodesgroup/ai-platform-gitops.git`

Resolution:
- add the GitLab repo to Argo CD with a valid token
- or apply a repository secret in the `argocd` namespace

Expected secret shape:
```yaml
apiVersion: v1
kind: Secret
metadata:
  name: gitlab-ai-platform-gitops-repo
  namespace: argocd
  labels:
    argocd.argoproj.io/secret-type: repository
stringData:
  type: git
  url: https://gitlab.com/jcloudcodesgroup/ai-platform-gitops.git
  username: oauth2
  password: <GITLAB_TOKEN>
```

### 8. Argo CD sync failed because the target namespace did not exist

Error seen:
```text
namespaces "ai-platform" not found
```

Root cause:
- the app manifest targeted namespace `ai-platform`
- the current Argo CD app manifest has:
```yaml
- CreateNamespace=false
```

Resolution options:
1. create the namespace manually:
```bash
kubectl create namespace ai-platform
```
2. or change the Argo CD app manifest to:
```yaml
- CreateNamespace=true
```

Recommended long-term fix:
- set `CreateNamespace=true` in the AI GitOps Argo CD app manifest

### 9. Argo CD sync reached the app but a prior operation was already running

Error seen:
```text
another operation is already in progress
```

Resolution:
```bash
argocd app terminate-op ai-inference-dev --grpc-web
argocd app sync ai-inference-dev --grpc-web
argocd app wait ai-inference-dev --health --sync --timeout 600 --grpc-web
```

## Known Deployment Dependencies

Before the AI app can deploy cleanly, confirm these platform pieces already exist in the AKS cluster:
- `argocd` installed and healthy enough to sync applications
- `ingress-nginx` installed and exposed
- namespace `ai-platform` exists, or Argo CD is allowed to create it
- Argo CD has repo access to `ai-platform-gitops`
- Docker Hub credentials are valid if image pull is private

## Recommended Verification Commands

### Verify Argo CD app state
```bash
argocd app get ai-inference-dev --grpc-web
```

### Verify namespace exists
```bash
kubectl get namespace ai-platform
```

### Verify Argo CD repo connectivity
```bash
argocd repo list --grpc-web
```

### Verify AI app resources
```bash
kubectl get all -n ai-platform
kubectl get ingress -n ai-platform
```

## Current Deployment Flow That Worked Best

1. make sure Jenkins shared-library changes are committed and available
2. run the AI app pipeline
3. let Jenkins build and push the image
4. let Jenkins update the AI GitOps repo
5. make sure Argo CD can read the GitOps repo
6. make sure `ai-platform` exists or `CreateNamespace=true` is set
7. sync the Argo CD app
8. verify the ingress and service in `ai-platform`

## Notes for Future Cleanup

If this repo is promoted further, the next useful cleanup items would be:
- rewrite any remaining GitLab-era wording in repo metadata
- make `CreateNamespace=true` the default in the AI Argo app manifest
- decide whether model prefetch should stay runtime-only or move to a separate release build profile
- align Spring Boot AI client configuration with the real deployed AI endpoint for each environment
