pipeline {
    agent any

    environment {
        // UI 自动化环境标识（跟你 config.yaml 里的 env 对应）
        UI_AUTOMATION_ENV = "dev"

        // 默认登录账号（正式用尽量改成 Jenkins Credential 注入）
        UI_ACCOUNT_USERNAME = "guang"
        UI_ACCOUNT_PASSWORD = "Aa123456"

        // Python 虚拟环境目录
        VENV_DIR = ".venv"
    }

    stages {
        stage('Checkout') {
            steps {
                // 从 SCM 拉取代码（Git 等）
                checkout scm
            }
        }

        stage('Setup Python Env') {
            steps {
                bat '''
                echo [Setup] 创建或更新虚拟环境
                if not exist "%VENV_DIR%" (
                    python -m venv "%VENV_DIR%"
                )

                call "%VENV_DIR%\\Scripts\\activate"
                python -m pip install --upgrade pip
                '''
            }
        }

        stage('Install Dependencies') {
            steps {
                bat '''
                echo [Install] 安装项目依赖

                call "%VENV_DIR%\\Scripts\\activate"
                pip install -r requirements.txt

                echo [Install] 安装 Playwright 浏览器內核
                python -m playwright install
                '''
            }
        }

        stage('Run UI Tests') {
            steps {
                bat '''
                echo [Test] 运行 UI 自动化用例

                call "%VENV_DIR%\\Scripts\\activate"
                pytest -s -vv ^
                    --html=reports\\ui-report.html ^
                    --self-contained-html
                '''
            }
        }
    }

    post {
        always {
            // 不管成功失败都把报告、日志、截图打包出来
            archiveArtifacts artifacts: 'reports/**', fingerprint: true
        }
        failure {
            echo '[Jenkins] UI 自动化用例执行失败，请查看 reports/ui-report.html 和日志。'
        }
    }
}
