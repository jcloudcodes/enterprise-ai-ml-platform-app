@Library('JavaShared_library@main') _

def pipelineConfig = [
  appName: 'ai-inference',
  agentLabel: 'jslave-inbound',
  imageRepository: 'jcloudcodes/enterprise-ai-ml-platform-app',
  imageTag: env.BUILD_NUMBER,

  vaultAddr: 'https://jcloudcodes-public-vault-e0a9d77c.e1f8f4d8.z1.hashicorp.cloud:8200',
  vaultNamespace: 'admin',
  vaultKvMount: 'kv/jcloudcodes/java-web-app',
  vaultSecretPath: 'jcloudcodes/java-web-app',

  gitopsRepoUrl: 'https://gitlab.com/jcloudcodesgroup/ai-platform-gitops.git',
  gitopsBranch: 'main',
  helmValuesFile: 'environments/dev/values.yaml',

  argocdAppManifestFile: 'applications/ai-inference-dev.yaml',
  argocdAppName: 'ai-inference-dev',
  argocdServer: 'argocd.jcloudcodes.com',

  aksClusterName: 'sap-dev-aksdemo1',
  kubeNamespace: 'ai-platform',
  externalSecretsNamespace: 'external-secrets',
  workspaceKubeDir: '.kube',

  vaultRoleIdCredentialId: 'vault-approle-role-id',
  vaultSecretIdCredentialId: 'vault-approle-secret-id',
  dockerCredentialId: 'jcloudcodes-dockerhub-cred',
  gitopsRepoTokenCredentialId: 'gitops-repo-token',

  bootstrapArgoCdApp: true,
  verifyEnvironment: true,
  refreshVaultToken: false,
  useVaultDockerCredentials: true
]

pipeline {
  agent {
    label "${pipelineConfig.agentLabel}"
  }

  options {
    timestamps()
    disableConcurrentBuilds()
    buildDiscarder(logRotator(numToKeepStr: '5'))
  }

  stages {
    stage('Validate') {
      steps {
        sh 'python3 --version'
        sh 'docker --version'
        sh 'git --version'
        sh 'vault version'
      }
    }

    stage('Test') {
      steps {
        sh '''docker run --rm \
          -v "$PWD:/workdir" \
          -w /workdir \
          python:3.11-slim \
          sh -lc "python -m pip install --no-cache-dir --progress-bar off -r requirements.txt && python -m compileall app"'''
      }
    }

    stage('Docker Build') {
      steps {
        script {
          dockerTemplate.buildImage(pipelineConfig)
        }
      }
    }

    stage('Docker Push') {
      steps {
        script {
          dockerTemplate.pushDockerHub(pipelineConfig)
        }
      }
    }

    stage('GitOps Update') {
      steps {
        script {
          gitopsAksTemplate.update(pipelineConfig)
        }
      }
    }

    stage('Bootstrap Argo CD App') {
      when {
        expression { pipelineConfig.bootstrapArgoCdApp }
      }
      steps {
        script {
          gitopsAksTemplate.bootstrapApp(pipelineConfig)
        }
      }
    }

    stage('Argo CD Sync') {
      steps {
        script {
          gitopsAksTemplate.sync(pipelineConfig)
        }
      }
    }

    stage('Verify Environment') {
      when {
        expression { pipelineConfig.verifyEnvironment }
      }
      steps {
        script {
          gitopsAksTemplate.verify(pipelineConfig)
        }
      }
    }
  }
}
