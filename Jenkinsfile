pipeline {
    agent any
    environment {
        DOCKERHUB_USER = "neelamegan"
        IMAGE = "tamil-doc-qa-server"
        PATH = "/usr/local/bin:${env.PATH}"   // adjust to match your `which docker` output
    }
    stages {
        stage('Checkout') {
            steps {
                checkout scm   // pulls the exact commit GitHub triggered the build for
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
                sh 'docker build -f Dockerfile.server -t ${DOCKERHUB_USER}/${IMAGE}:${GIT_COMMIT} .'
            }
        }
        stage('Smoke Test Container') {
            steps {
                sh '''
                    docker run -d --name test-container -p 8000:8000 ${DOCKERHUB_USER}/${IMAGE}:${GIT_COMMIT}
                    sleep 5
                    curl -f http://localhost:8001/health
                    docker stop test-container && docker rm test-container
                '''
            }
        }
        stage('Push to Registry') {
            when { branch 'main' }
            steps {
                sh 'docker push ${REGISTRY}/${IMAGE}:${GIT_COMMIT}'
            }
        }
        stage('Deploy to Kubernetes') {
            when { branch 'main' }
            steps {
                sh 'kubectl set image deployment/tamil-doc-qa-server server=${REGISTRY}/${IMAGE}:${GIT_COMMIT} --record'
            }
        }
    }
    post {
        failure {
            echo 'Build failed — check logs above.'
        }
    }
}