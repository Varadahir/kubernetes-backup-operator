@echo off
setlocal

echo ==========================================
echo   Kubernetes Backup Operator Setup
echo ==========================================
echo.

set /p DB_NAME=Enter database name: 
set /p DB_PASSWORD=Enter MySQL root password: 

echo.
echo [1/8] Creating CRD...
kubectl apply -f crd.yaml

echo.
echo [2/8] Creating RBAC...
kubectl apply -f operator-rbac.yaml

echo.
echo [3/8] Creating MySQL Secret...
kubectl create secret generic mysql-secret --from-literal=MYSQL_ROOT_PASSWORD="%DB_PASSWORD%" --dry-run=client -o yaml | kubectl apply -f -

echo.
echo [4/8] Creating MySQL...
kubectl apply -f mysql-pvc.yaml
kubectl apply -f mysql.yaml
kubectl apply -f mysql-service.yaml

echo Waiting for MySQL to accept connections...

:WAIT_MYSQL
kubectl exec mysql -- mysqladmin -h 127.0.0.1 -u root -p%DB_PASSWORD% ping >nul 2>&1

if errorlevel 1 (
    echo MySQL is not ready yet...
    timeout /t 5 /nobreak >nul
    goto WAIT_MYSQL
)

echo MySQL is ready!

echo.
echo Creating database: %DB_NAME%
kubectl exec mysql -- mysql -h 127.0.0.1 -u root -p%DB_PASSWORD% -e "CREATE DATABASE IF NOT EXISTS %DB_NAME%;"
echo.
echo [5/8] Creating MinIO...
kubectl apply -f minio.yaml

echo.
echo [6/8] Creating Backup Operator...
kubectl apply -f operator-deployment.yaml

echo.
echo Waiting for Backup Operator...
kubectl rollout status deployment/backup-operator

echo.
echo [7/8] Creating BackupPolicy...

(
echo apiVersion: backup.example.com/v1
echo kind: BackupPolicy
echo metadata:
echo   name: my-backup
echo spec:
echo   database: %DB_NAME%
echo   schedule: "*/2 * * * *"
) > developer-backup-policy.yaml

kubectl apply -f developer-backup-policy.yaml

echo.
echo [8/8] Checking resources...
kubectl get pods
kubectl get backuppolicy
kubectl get cronjob

echo.
echo ==========================================
echo        SETUP COMPLETED SUCCESSFULLY
echo ==========================================
echo.
echo Database: %DB_NAME%
echo Backup: Every 2 minutes
echo Storage: MinIO
echo.
pause