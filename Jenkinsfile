pipeline {
    agent any

    environment {
        IMAGE = "sandeep262005/foodexpress"
        TAG   = "${BUILD_NUMBER}"
    }

    options {
        timestamps()
        buildDiscarder(logRotator(numToKeepStr: '10'))
    }

    stages {
        stage('Checkout') {
            steps { checkout scm }
        }

        stage('Build Docker Image') {
            steps {
                sh 'docker build -t $IMAGE:$TAG -t $IMAGE:latest .'
            }
        }

        stage('Unit Tests') {
            steps {
                // Run the 20 automated tests inside the image we just built.
                // If any test fails, the pipeline stops here and nothing is deployed.
                sh 'docker run --rm $IMAGE:$TAG python -m pytest -v -p no:cacheprovider'
            }
        }

        stage('Push to Docker Hub') {
            steps {
                withCredentials([usernamePassword(credentialsId: 'dockerhub-creds',
                        usernameVariable: 'USER', passwordVariable: 'PASS')]) {
                    sh 'echo $PASS | docker login -u $USER --password-stdin'
                    sh 'docker push $IMAGE:$TAG'
                    sh 'docker push $IMAGE:latest'
                }
            }
        }

        stage('Deploy to Kubernetes') {
            steps {
                sh 'sed -i "s|IMAGE_PLACEHOLDER|$IMAGE:$TAG|g; s|VERSION_PLACEHOLDER|1.$TAG|g" k8s/app.yaml'
                sh 'kubectl apply -f k8s/mysql.yaml'
                sh 'kubectl apply -f k8s/app.yaml'
                sh 'kubectl rollout status deployment/mysql --timeout=180s'
                sh 'kubectl rollout status deployment/foodexpress --timeout=300s'
            }
        }

        stage('Smoke Test') {
            steps {
                // Check that the live app AND the database answer on /health
                sh '''
                    for i in $(seq 1 12); do
                        if curl -fs http://localhost:30090/health; then
                            echo ""; echo "App is healthy"; exit 0
                        fi
                        echo "Waiting for app... ($i)"; sleep 5
                    done
                    echo "Health check failed"; exit 1
                '''
            }
        }
    }

    post {
        success { echo "FoodExpress v1.${BUILD_NUMBER} is live on port 30090" }
        failure { echo 'Pipeline failed - check the red stage above.' }
        always  { sh 'docker image prune -f || true' }
    }
}
