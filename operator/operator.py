import kopf
from kubernetes import client, config
from datetime import datetime


# ============================================================
# KUBERNETES CONFIGURATION
# ============================================================

# Operator runs INSIDE Kubernetes.
# Therefore use the Pod's ServiceAccount credentials.

config.load_incluster_config()

batch_api = client.BatchV1Api()
custom_api = client.CustomObjectsApi()


# ============================================================
# BACKUP POLICY CREATION
# ============================================================

@kopf.on.create(
    'backup.example.com',
    'v1',
    'backuppolicies'
)
def backup_policy_created(
    spec,
    name,
    namespace,
    patch,
    **kwargs
):

    # ========================================================
    # READ BACKUP POLICY
    # ========================================================

    target = spec.get("target", {})

    database = target.get("database")

    credentials_secret = spec.get(
        "credentialsSecret",
        {}
    )

    secret_name = credentials_secret.get("name")

    secret_key = credentials_secret.get(
        "key",
        "MYSQL_ROOT_PASSWORD"
    )

    schedule = spec.get("schedule")


    print(
        f"BackupPolicy created: {name}"
    )

    print(
        f"Database: {database}"
    )

    print(
        f"Secret: {secret_name}"
    )

    print(
        f"Secret Key: {secret_key}"
    )

    print(
        f"Schedule: {schedule}"
    )


    # ========================================================
    # VALIDATION
    # ========================================================

    if not database:

        raise kopf.PermanentError(
            "spec.target.database is required"
        )


    if not secret_name:

        raise kopf.PermanentError(
            "spec.credentialsSecret.name is required"
        )


    if not secret_key:

        raise kopf.PermanentError(
            "spec.credentialsSecret.key is required"
        )


    if not schedule:

        raise kopf.PermanentError(
            "spec.schedule is required"
        )


    # ========================================================
    # CRONJOB NAME
    # ========================================================

    cronjob_name = f"{name}-backup"


    print(
        f"Creating CronJob: {cronjob_name}"
    )


    # ========================================================
    # CRONJOB
    # ========================================================

    cronjob = client.V1CronJob(

        metadata=client.V1ObjectMeta(
            name=cronjob_name,
            namespace=namespace
        ),

        spec=client.V1CronJobSpec(

            # Example:
            #
            # */5 * * * *
            #
            schedule=schedule,


            # Do not allow overlapping backups.
            concurrency_policy="Forbid",


            # Keep recent successful Jobs.
            successful_jobs_history_limit=3,


            # Keep recent failed Jobs.
            failed_jobs_history_limit=3,


            job_template=client.V1JobTemplateSpec(

                spec=client.V1JobSpec(

                    # Retry failed Job up to 2 times.
                    backoff_limit=2,


                    template=client.V1PodTemplateSpec(

                        spec=client.V1PodSpec(

                            restart_policy="Never",


                            # =================================================
                            # INIT CONTAINER
                            # =================================================
                            # Creates MySQL database backup.
                            # =================================================

                            init_containers=[

                                client.V1Container(

                                    name="database-backup",

                                    image="mysql:8.0",


                                    command=[
                                        "/bin/sh",
                                        "-c"
                                    ],


                                    args=[

                                        'set -e; '

                                        'BACKUP_FILE='
                                        '"backup-$(date '
                                        '+%Y%m%d-%H%M%S).sql"; '

                                        'echo '
                                        '"Creating $BACKUP_FILE"; '

                                        'MYSQL_PWD=$MYSQL_ROOT_PASSWORD '
                                        'mysqldump '
                                        '-h mysql '
                                        '-u root '
                                        f'{database} '
                                        '> /backup/$BACKUP_FILE; '

                                        'echo "$BACKUP_FILE" '
                                        '> /backup/filename.txt; '

                                        'echo '
                                        '"Backup created: '
                                        '$BACKUP_FILE"'
                                    ],


                                    # =================================================
                                    # MYSQL PASSWORD FROM DEVELOPER SECRET
                                    # =================================================

                                    env=[

                                        client.V1EnvVar(

                                            name="MYSQL_ROOT_PASSWORD",

                                            value_from=(
                                                client.V1EnvVarSource(

                                                    secret_key_ref=(
                                                        client
                                                        .V1SecretKeySelector(

                                                            # IMPORTANT:
                                                            #
                                                            # Secret name comes
                                                            # from BackupPolicy.
                                                            #
                                                            # Example:
                                                            #
                                                            # company-db-secret

                                                            name=secret_name,


                                                            # Secret key also
                                                            # comes from
                                                            # BackupPolicy.

                                                            key=secret_key
                                                        )
                                                    )
                                                )
                                            )
                                        )
                                    ],


                                    volume_mounts=[

                                        client.V1VolumeMount(

                                            name="backup-storage",

                                            mount_path="/backup"
                                        )
                                    ]
                                )
                            ],


                            # =================================================
                            # MAIN CONTAINER
                            # =================================================
                            # Uploads backup to MinIO.
                            # =================================================

                            containers=[

                                client.V1Container(

                                    name="upload-backup",

                                    image="minio/mc:latest",


                                    command=[
                                        "/bin/sh",
                                        "-c"
                                    ],


                                    args=[

                                        'set -e; '

                                        'echo "Connecting to MinIO..."; '

                                        'mc alias set myminio '
                                        'http://minio:9000 '
                                        '$MINIO_ROOT_USER '
                                        '$MINIO_ROOT_PASSWORD; '

                                        'FILE=$(cat '
                                        '/backup/filename.txt); '

                                        'echo '
                                        '"Uploading $FILE to MinIO..."; '

                                        'mc cp '
                                        '/backup/$FILE '
                                        'myminio/backups/$FILE; '

                                        'echo '
                                        '"Upload completed: $FILE"'
                                    ],


                                    # =================================================
                                    # MINIO CREDENTIALS
                                    # =================================================

                                    env=[

                                        client.V1EnvVar(

                                            name="MINIO_ROOT_USER",

                                            value_from=(
                                                client.V1EnvVarSource(

                                                    secret_key_ref=(
                                                        client
                                                        .V1SecretKeySelector(

                                                            name="minio-secret",

                                                            key="MINIO_ROOT_USER"
                                                        )
                                                    )
                                                )
                                            )
                                        ),


                                        client.V1EnvVar(

                                            name="MINIO_ROOT_PASSWORD",

                                            value_from=(
                                                client.V1EnvVarSource(

                                                    secret_key_ref=(
                                                        client
                                                        .V1SecretKeySelector(

                                                            name="minio-secret",

                                                            key="MINIO_ROOT_PASSWORD"
                                                        )
                                                    )
                                                )
                                            )
                                        )
                                    ],


                                    volume_mounts=[

                                        client.V1VolumeMount(

                                            name="backup-storage",

                                            mount_path="/backup"
                                        )
                                    ]
                                )
                            ],


                            # =================================================
                            # SHARED TEMPORARY STORAGE
                            # =================================================
                            #
                            # Init container creates:
                            #
                            # /backup/backup-xxxxx.sql
                            #
                            # Main container reads:
                            #
                            # /backup/filename.txt
                            #
                            # and uploads the backup to MinIO.
                            #
                            # =================================================

                            volumes=[

                                client.V1Volume(

                                    name="backup-storage",

                                    empty_dir=(
                                        client
                                        .V1EmptyDirVolumeSource()
                                    )
                                )
                            ]
                        )
                    )
                )
            )
        )
    )


    # ========================================================
    # CREATE CRONJOB
    # ========================================================

    try:

        batch_api.create_namespaced_cron_job(
            namespace=namespace,
            body=cronjob
        )


        print(
            f"CronJob created successfully: "
            f"{cronjob_name}"
        )


    except client.exceptions.ApiException as e:

        # If CronJob already exists, don't crash operator.

        if e.status == 409:

            print(
                f"CronJob {cronjob_name} "
                f"already exists."
            )

        else:

            raise


    # ========================================================
    # INITIAL BACKUP POLICY STATUS
    # ========================================================

    patch.status["phase"] = "Scheduled"

    patch.status["message"] = (
        f"CronJob {cronjob_name} created successfully"
    )


# ============================================================
# BACKUP POLICY DELETION
# ============================================================

@kopf.on.delete(
    'backup.example.com',
    'v1',
    'backuppolicies'
)
def backup_policy_deleted(
    name,
    namespace,
    **kwargs
):

    cronjob_name = f"{name}-backup"


    print(
        f"BackupPolicy deleted: {name}"
    )


    print(
        f"Deleting CronJob: {cronjob_name}"
    )


    try:

        batch_api.delete_namespaced_cron_job(
            name=cronjob_name,
            namespace=namespace
        )


        print(
            f"CronJob deleted successfully: "
            f"{cronjob_name}"
        )


    except client.exceptions.ApiException as e:

        if e.status == 404:

            print(
                f"CronJob {cronjob_name} "
                f"already does not exist."
            )

        else:

            raise


# ============================================================
# JOB WATCHER
# ============================================================

@kopf.on.event(
    'batch',
    'v1',
    'jobs'
)
def watch_backup_jobs(
    event,
    **kwargs
):

    job = event.get(
        "object",
        {}
    )


    metadata = job.get(
        "metadata",
        {}
    )


    job_name = metadata.get(
        "name"
    )


    namespace = metadata.get(
        "namespace",
        "default"
    )


    # ========================================================
    # FIND CRONJOB OWNER
    # ========================================================

    owner_references = metadata.get(
        "ownerReferences",
        []
    )


    cronjob_name = None


    for owner in owner_references:

        if owner.get("kind") == "CronJob":

            cronjob_name = owner.get(
                "name"
            )

            break


    # ========================================================
    # IGNORE JOBS THAT DON'T BELONG TO A CRONJOB
    # ========================================================

    if not cronjob_name:

        return


    # ========================================================
    # ONLY WATCH OUR BACKUP CRONJOBS
    # ========================================================

    if not cronjob_name.endswith("-backup"):

        return


    backup_policy_name = cronjob_name[
        :-len("-backup")
    ]


    print(
        f"Watching backup Job: {job_name}"
    )


    print(
        f"Related BackupPolicy: "
        f"{backup_policy_name}"
    )


    # ========================================================
    # JOB STATUS
    # ========================================================

    status = job.get(
        "status",
        {}
    )


    succeeded = status.get(
        "succeeded",
        0
    )


    failed = status.get(
        "failed",
        0
    )


    # ========================================================
    # SUCCESS
    # ========================================================

    if succeeded and succeeded >= 1:

        print(
            f"Backup Job {job_name} "
            f"completed successfully."
        )


        current_time = (
            datetime.now().strftime(
                "%Y-%m-%d %H:%M:%S"
            )
        )


        body = {

            "status": {

                "phase": "Successful",

                "lastBackup": current_time,

                "message": (
                    f"Backup Job {job_name} "
                    f"completed successfully"
                )
            }
        }


        try:

            custom_api.patch_namespaced_custom_object_status(

                group="backup.example.com",

                version="v1",

                namespace=namespace,

                plural="backuppolicies",

                name=backup_policy_name,

                body=body
            )


            print(
                f"BackupPolicy "
                f"{backup_policy_name} "
                f"status updated to Successful"
            )


        except client.exceptions.ApiException as e:

            # =================================================
            # Old Jobs can remain in the cluster.
            #
            # If their BackupPolicy was deleted,
            # Kubernetes returns 404.
            #
            # Don't crash the operator.
            # =================================================

            if e.status == 404:

                print(
                    f"BackupPolicy "
                    f"{backup_policy_name} "
                    f"not found. "
                    f"Ignoring old Job {job_name}."
                )

                return

            raise


    # ========================================================
    # FAILURE
    # ========================================================

    elif failed and failed > 0:

        print(
            f"Backup Job {job_name} failed."
        )


        body = {

            "status": {

                "phase": "Failed",

                "message": (
                    f"Backup Job {job_name} failed"
                )
            }
        }


        try:

            custom_api.patch_namespaced_custom_object_status(

                group="backup.example.com",

                version="v1",

                namespace=namespace,

                plural="backuppolicies",

                name=backup_policy_name,

                body=body
            )


            print(
                f"BackupPolicy "
                f"{backup_policy_name} "
                f"status updated to Failed"
            )


        except client.exceptions.ApiException as e:

            # =================================================
            # Ignore missing BackupPolicy for old Jobs.
            # =================================================

            if e.status == 404:

                print(
                    f"BackupPolicy "
                    f"{backup_policy_name} "
                    f"not found. "
                    f"Ignoring old Job {job_name}."
                )

                return

            raise