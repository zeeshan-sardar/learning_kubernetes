# learning_kubernetes

# Kubernetes for ML DevOps — Complete Notes

---

## Part 1: Core Kubernetes Concepts

### Architecture

| Component | Location | Purpose |
|-----------|----------|---------|
| **API Server** | Master | Entry point for all commands |
| **Controller** | Master | Maintains desired state |
| **Scheduler** | Master | Decides which node runs which pod |
| **etcd** | Master | Stores all cluster data |
| **kubelet** | Node | Manages containers on the node |

### Key Resources

| Resource | What It Does |
|----------|--------------|
| **Pod** | Smallest deployable unit. Wraps one or more containers that share network and storage. |
| **Deployment** | Declares "keep N pods running." Handles scaling, updates, and self-healing. |
| **Service** | Stable network endpoint that routes traffic to pods using label selectors. |
| **ConfigMap** | Stores non-sensitive configuration as key-value pairs. |
| **Secret** | Stores sensitive data (API keys, passwords). Base64 encoded. |
| **HPA** | Horizontal Pod Autoscaler. Scales pods based on CPU/memory usage. |

### Labels and Selectors

Labels are tags attached to pods:
```yaml
labels:
  app: ml-model
```

Selectors find pods by their labels:
```yaml
selector:
  matchLabels:
    app: ml-model
```

This is how Deployments know which pods to manage and Services know where to route traffic.

### Declarative Model

You describe **what** you want, not **how** to do it:
```yaml
replicas: 3  # "I want 3 pods"
```

Kubernetes continuously works to match reality to your desired state.

---

## Part 2: Essential kubectl Commands

### Cluster Setup (Minikube)
```bash
# Install Minikube
curl -LO https://storage.googleapis.com/minikube/releases/latest/minikube-linux-amd64
sudo install minikube-linux-amd64 /usr/local/bin/minikube

# Install kubectl
curl -LO "https://dl.k8s.io/release/$(curl -L -s https://dl.k8s.io/release/stable.txt)/bin/linux/amd64/kubectl"
sudo install kubectl /usr/local/bin/kubectl

# Start cluster
minikube start --driver=docker
minikube status
```

### Basic Operations
```bash
kubectl get pods                    # List pods
kubectl get pods -o wide            # List pods with IPs and nodes
kubectl get services                # List services
kubectl get all                     # List everything
kubectl get configmap               # List ConfigMaps
kubectl get secret                  # List Secrets
kubectl get hpa                     # List autoscalers

kubectl apply -f <file.yaml>        # Create/update resources
kubectl delete -f <file.yaml>       # Delete resources
kubectl delete pod <pod-name>       # Delete specific pod

kubectl describe pod <pod-name>     # Detailed pod info
kubectl logs <pod-name>             # View pod logs
kubectl exec -it <pod-name> -- sh   # Shell into pod

kubectl top pods                    # Resource usage (needs metrics-server)
```

### Rollout Commands
```bash
kubectl set image deployment/<name> <container>=<image>:<tag>   # Update image
kubectl rollout status deployment/<name>                        # Watch rollout
kubectl rollout history deployment/<name>                       # View history
kubectl rollout undo deployment/<name>                          # Rollback
```

### Minikube Specific
```bash
eval $(minikube docker-env)             # Point Docker to Minikube's daemon
minikube service <service-name> --url   # Get external URL
minikube addons enable metrics-server   # Enable metrics
```

---

## Part 3: ML Model Deployment

### Project Structure
```
ml-model-demo/
├── requirements.txt      # Python dependencies
├── train_model.py        # Train and save model
├── app.py                # Flask API
├── Dockerfile            # Container definition
├── ml-deployment.yaml    # Kubernetes Deployment
├── ml-service.yaml       # Kubernetes Service
├── ml-configmap.yaml     # Configuration
├── ml-secret.yaml        # Sensitive data
└── ml-hpa.yaml           # Autoscaler
```

### requirements.txt
```
flask==3.0.0
scikit-learn==1.3.2
joblib==1.3.2
```

### train_model.py
```python
from sklearn.datasets import load_iris
from sklearn.ensemble import RandomForestClassifier
import joblib

iris = load_iris()
model = RandomForestClassifier(n_estimators=10)
model.fit(iris.data, iris.target)
joblib.dump(model, 'model.joblib')
print("Model saved!")
```

### app.py
```python
from flask import Flask, request, jsonify
import joblib
import numpy as np

app = Flask(__name__)
model = joblib.load('model.joblib')

CLASS_NAMES = ['setosa', 'versicolor', 'virginica']

@app.route('/predict', methods=['POST'])
def predict():
    data = request.json
    features = np.array(data['features']).reshape(1, -1)
    
    prediction = model.predict(features)[0]
    confidence = model.predict_proba(features).max()
    
    return jsonify({
        'prediction': int(prediction),
        'class_name': CLASS_NAMES[prediction],
        'confidence': float(confidence),
        'version': 'v2'
    })

@app.route('/health', methods=['GET'])
def health():
    return jsonify({'status': 'healthy'})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
```

### Dockerfile
```dockerfile
FROM python:3.10-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY train_model.py .
RUN python train_model.py

COPY app.py .

EXPOSE 5000

CMD ["python", "app.py"]
```

**Note:** Order matters for Docker layer caching. Put least-changing files first.

### Build Commands
```bash
eval $(minikube docker-env)
docker build -t ml-model:v1 .
docker build -t ml-model:v2 .   # After code changes
```

---

## Part 4: Kubernetes YAML Files

### ml-deployment.yaml
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: ml-model-deployment
spec:
  replicas: 2
  selector:
    matchLabels:
      app: ml-model
  template:
    metadata:
      labels:
        app: ml-model
    spec:
      containers:
      - name: ml-model
        image: ml-model:v2
        imagePullPolicy: Never
        ports:
        - containerPort: 5000
        envFrom:
        - configMapRef:
            name: ml-model-config
        - secretRef:
            name: ml-model-secret
        resources:
          requests:
            memory: "128Mi"
            cpu: "100m"
          limits:
            memory: "256Mi"
            cpu: "500m"
        livenessProbe:
          httpGet:
            path: /health
            port: 5000
          initialDelaySeconds: 10
          periodSeconds: 5
```

**Key settings explained:**
- `imagePullPolicy: Never` — Use local image, don't pull from Docker Hub
- `requests` — Minimum guaranteed resources
- `limits` — Maximum allowed (pod killed if exceeds memory)
- `livenessProbe` — Kubernetes checks `/health` every 5 seconds

### ml-service.yaml
```yaml
apiVersion: v1
kind: Service
metadata:
  name: ml-model-service
spec:
  type: NodePort
  selector:
    app: ml-model
  ports:
  - port: 5000
    targetPort: 5000
```

### ml-configmap.yaml
```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: ml-model-config
data:
  CLASS_NAMES: "setosa,versicolor,virginica"
  MODEL_VERSION: "v2"
  LOG_LEVEL: "INFO"
```

### ml-secret.yaml
```yaml
apiVersion: v1
kind: Secret
metadata:
  name: ml-model-secret
type: Opaque
stringData:
  API_KEY: "my-secret-api-key-12345"
```

### ml-hpa.yaml
```yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: ml-model-hpa
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: ml-model-deployment
  minReplicas: 2
  maxReplicas: 5
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 50
```

---

## Part 5: Key Concepts for Interviews

### Self-Healing
```bash
kubectl delete pod <pod-name>
kubectl get pods   # New pod automatically created
```

Deployment notices "I want 3, but I have 2" and creates a replacement.

### Rolling Updates
```bash
kubectl set image deployment/ml-model-deployment ml-model=ml-model:v2
kubectl rollout status deployment/ml-model-deployment
```

Zero downtime: new pods start → pass health checks → old pods terminate.

### Rollback
```bash
kubectl rollout undo deployment/ml-model-deployment
```

Reverts to previous version if new deployment has bugs.

### Resource Management

| Setting | Meaning |
|---------|---------|
| `cpu: 100m` | 100 millicores = 0.1 CPU core |
| `memory: 128Mi` | 128 mebibytes |
| Exceeds memory limit | Pod killed (OOMKilled) |
| Exceeds CPU limit | Pod throttled (runs slower) |

### ConfigMap vs Secret

| ConfigMap | Secret |
|-----------|--------|
| Non-sensitive config | Sensitive data |
| Plain text | Base64 encoded |
| Feature flags, URLs, labels | API keys, passwords, tokens |

---

## Part 6: Common Interview Questions

**Q: How would you deploy an ML model?**
> Containerize with Docker, create Deployment YAML with health probes and resource limits, expose via Service.

**Q: How does Kubernetes handle pod failures?**
> Deployment controller continuously checks desired vs actual state. If a pod dies, it creates a replacement.

**Q: How do you deploy a new model version with zero downtime?**
> Rolling update: `kubectl set image deployment/<name> <container>=<image>:<new-tag>`. Kubernetes starts new pods, waits for health checks, then terminates old pods.

**Q: How do you handle traffic spikes?**
> Horizontal Pod Autoscaler monitors CPU/memory and scales replicas between min and max based on utilization threshold.

**Q: How do you prevent one model from consuming all cluster resources?**
> Set resource requests (guaranteed minimum) and limits (maximum allowed) in the Deployment spec.

**Q: How do you manage configuration and secrets?**
> ConfigMaps for non-sensitive config, Secrets for sensitive data. Inject as environment variables using `envFrom`.

**Q: How do you decide resource limits for ML models?**
> Profile locally, set requests slightly above typical usage, set limits for peak load with buffer, monitor and adjust in production.

**Q: What happens if a new deployment fails health checks?**
> Rollout stops. Old pods keep serving traffic. The livenessProbe protects you.

---

## Quick Reference: Full Deployment Flow

```bash
# 1. Build image
eval $(minikube docker-env)
docker build -t ml-model:v1 .

# 2. Deploy
kubectl apply -f ml-configmap.yaml
kubectl apply -f ml-secret.yaml
kubectl apply -f ml-deployment.yaml
kubectl apply -f ml-service.yaml
kubectl apply -f ml-hpa.yaml

# 3. Verify
kubectl get all
kubectl get pods

# 4. Test
URL=$(minikube service ml-model-service --url)
curl -X POST $URL/predict \
  -H "Content-Type: application/json" \
  -d '{"features": [5.1, 3.5, 1.4, 0.2]}'

# 5. Update
docker build -t ml-model:v2 .
kubectl set image deployment/ml-model-deployment ml-model=ml-model:v2
kubectl rollout status deployment/ml-model-deployment
```

