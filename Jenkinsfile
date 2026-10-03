pipeline {
    agent any
    environment {
        DOCKERHUB_USER = "neelamegan"
        IMAGE = "tamil-doc-qa-server"
        PATH = "/usr/local/bin:${env.PATH}"
    }
    stages {
        stage('Checkout') {
            steps {
                checkout scm
            }
        }
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
                    docker run -d --name test-container -p 8001:8000 neelamegan/tamil-doc-qa-server:${GIT_COMMIT}
                    sleep 8
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
                    kubectl set image deployment/tamil-doc-qa-server server=neelamegan/tamil-doc-qa-server:${GIT_COMMIT} --record
                    kubectl rollout status deployment/tamil-doc-qa-server --timeout=120s
                '''
            }
        }
    }
    post {
        failure {
            echo 'Build failed — check logs above.'
        }
    }
}