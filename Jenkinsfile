pipeline {
    agent {
        docker {
            image 'docker.io/library/python'
            label 'docker'
        }
    }
    stages {
        stage('Setup') {
            steps {
                sh """
                pip install poetry
                poetry install
                """
            }
        }
        stage('Build') {
            steps {
                sh 'poetry run python ./artemis_changelog/main.py --output-dir=changelog'
            }
        }
        stage('Update') {
            steps {
                sh """
                git add changelog
                git commit -m "scheduled update"
                git push
                """
            }
        }
    }
}
