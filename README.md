\# Kubernetes Database Backup Operator



A custom Kubernetes Operator that automates scheduled MySQL database backups using a declarative `BackupPolicy` Custom Resource.



The operator creates Kubernetes CronJobs dynamically, executes `mysqldump`, and uploads the generated SQL backup to MinIO object storage. Database credentials are referenced securely through Kubernetes Secrets instead of being stored directly in the BackupPolicy.



\## Architecture



Developer

&#x20;   |

&#x20;   | BackupPolicy

&#x20;   v

+-----------------------+

| Backup Operator       |

| Python + Kopf         |

+-----------+-----------+

&#x20;           |

&#x20;           v

&#x20;     Kubernetes CronJob

&#x20;           |

&#x20;           v

&#x20;      Kubernetes Job

&#x20;       /           \\

&#x20;      /             \\

&#x20;mysqldump         Secret

&#x20;   |

&#x20;   v

&#x20;backup.sql

&#x20;   |

&#x20;   v

&#x20; MinIO

&#x20;/backups/





\## Key Features



\- Custom Kubernetes `BackupPolicy` CRD

\- Python/Kopf based Kubernetes Operator

\- Automatic CronJob creation

\- Configurable backup schedules

\- MySQL `mysqldump` backups

\- Kubernetes Secret based database credentials

\- MinIO object storage

\- Automatic `backups` bucket creation

\- Dockerized operator

\- Docker Hub image

\- Single-file Kubernetes installation manifest

\- Developer-friendly backup workflow



\## Technology Stack



\- Kubernetes

\- Python

\- Kopf

\- Docker

\- MySQL

\- MinIO

\- Kubernetes CRDs

\- Kubernetes CronJobs

\- Kubernetes Secrets

\- RBAC



\## Project Structure



```text

kubernetes-backup-operator/

│

├── operator/

│   ├── operator.py

│   ├── Dockerfile

│   └── requirements.txt

│

├── crd.yaml

├── operator-rbac.yaml

├── operator-deployment.yaml

├── minio.yaml

├── backup-operator-install.yaml

├── setup.bat

│

├── mysql.yaml

├── mysql-pvc.yaml

├── mysql-service.yaml

├── mysql-deployment.yaml

├── mysql-secret.yaml

│

├── backup-policy.yaml

├── developer-backup-policy.yaml

└── friend-backup-policy.yaml

