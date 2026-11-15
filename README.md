# 🍛 FoodExpress: Food Ordering App with a Jenkins CI/CD Pipeline

A real-world food ordering web app (a mini Swiggy). Every push to GitHub is automatically
**built, tested, pushed to Docker Hub and deployed to Kubernetes on AWS EC2** by Jenkins.

**DevOps tools:** Git + GitHub · Jenkins · Docker · Kubernetes (k3s) · AWS EC2

## What the app does
| Customer | Admin |
|---|---|
| Sign up / log in (passwords hashed) | Dashboard: total orders, active orders, revenue |
| Browse menu by category (veg / non-veg) | Change order status: Placed → Preparing → Out for Delivery → Delivered |
| Cart, ₹30 delivery fee, free delivery above ₹499 | Add / edit dishes with photos |
| Place order (Cash on Delivery), minimum ₹100 | Mark dishes available / unavailable |
| Track orders, cancel while still "Placed" | Filter orders by status |

## Architecture
```
Developer ──git push──▶ GitHub ──webhook──▶ Jenkins  (AWS EC2: devops-pbl3)
                                              │ 1 Checkout
                                              │ 2 Build Docker image
                                              │ 3 Run 20 unit tests inside the image
                                              │ 4 Push image ──▶ Docker Hub
                                              │ 5 kubectl apply ──▶ Kubernetes (k3s)
                                              ▼ 6 Smoke test /health
                         Kubernetes:  foodexpress (2 pods)  ──▶  mysql (1 pod + persistent volume)
                                      NodePort 30090 → http://<EC2-IP>:30090
```

## Files
```
app/            Flask application (models, routes, HTML templates, CSS)
tests/          20 automated tests (pytest)
k8s/mysql.yaml  MySQL database + persistent storage + service
k8s/app.yaml    FoodExpress deployment (2 replicas, health probes) + NodePort service 30090
Dockerfile      Builds the app image (Gunicorn, non-root user, healthcheck)
Jenkinsfile     The CI/CD pipeline (6 stages)
```

## One-time setup on the EC2 server
1. Add an inbound rule for **port 30090** in the EC2 security group.
2. Create the Kubernetes secret (passwords live here, never in GitHub):
```bash
kubectl create secret generic foodexpress-secrets \
  --from-literal=MYSQL_ROOT_PASSWORD=Root2026pass \
  --from-literal=MYSQL_PASSWORD=Food2026pass \
  --from-literal=DATABASE_URL='mysql+pymysql://foodapp:Food2026pass@mysql:3306/foodexpress' \
  --from-literal=SECRET_KEY=foodexpress-secret-key-2026-change-me \
  --from-literal=ADMIN_PASSWORD=Admin2026pass
```
3. Jenkins: New Item → `foodexpress` → Pipeline → Pipeline script from SCM → this repo → branch `*/main` → Build Now.

**Admin login:** `admin@foodapp.com` / the `ADMIN_PASSWORD` above.

## Useful commands
```bash
kubectl get pods,svc,pvc                       # everything running?
kubectl logs deployment/foodexpress            # app logs
kubectl rollout undo deployment/foodexpress    # roll back to the previous version
kubectl scale deployment/foodexpress --replicas=3
```

## Run locally (optional)
```bash
pip install -r requirements.txt
pytest -v
python run.py        # http://localhost:5000  (uses SQLite, admin password admin123)
```

## Viva points
- **CI:** every push is built and tested automatically. **CD:** every passing build is deployed automatically.
- **Tests protect production:** if a test fails, Jenkins stops before the deploy stage.
- **Docker:** the same image runs everywhere. Every build has its own tag, so you can roll back.
- **Kubernetes:** 2 replicas for availability, rolling updates (zero downtime), readiness and liveness probes, self-healing (delete a pod and it comes back).
- **Persistent volume:** MySQL data survives pod restarts and redeploys.
- **Security:** secrets in a Kubernetes Secret (not in Git), Docker Hub token stored in Jenkins credentials, hashed passwords, CSRF protection, container runs as a non-root user.
- **Future scope:** AWS RDS for the database, S3 for images, Terraform, Prometheus + Grafana monitoring, online payments.
