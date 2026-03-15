from kubernetes import client, config
import uuid
import time
import json
import logging

NAMESPACE = "default"

def load_k8s_config():
    try:
        config.load_incluster_config()
        print("Loaded in-cluster Kubernetes config")
    except:
        config.load_kube_config()
        print("Loaded local kubeconfig")

# Remove the module-level call
# load_k8s_config()

# Initialize clients lazily
batch_v1 = None
core_v1 = None

def get_batch_v1():
    global batch_v1
    if batch_v1 is None:
        load_k8s_config()
        batch_v1 = client.BatchV1Api()
    return batch_v1

def get_core_v1():
    global core_v1
    if core_v1 is None:
        load_k8s_config()
        core_v1 = client.CoreV1Api()
    return core_v1

logger = logging.getLogger(__name__)

def wait_for_job_completion(job_name, timeout=3600):
    logger.info(f"Waiting for job {job_name} to complete, timeout: {timeout}s")
    start_time = time.time()

    while True:
        job = get_batch_v1().read_namespaced_job(name=job_name, namespace=NAMESPACE)

        if job.status.succeeded == 1:
            logger.info(f"Job {job_name} succeeded")
            return True
        
        if job.status.failed:
            logger.warning(f"Job {job_name} failed")
            return False
        
        if time.time() - start_time > timeout:
            logger.error(f"Job {job_name} timed out")
            raise TimeoutError("Job execution timeout")

        time.sleep(2)


def get_job_status(job_name):
    """Return job status: 'active', 'succeeded', 'failed', or 'unknown'."""
    try:
        job = get_batch_v1().read_namespaced_job(name=job_name, namespace=NAMESPACE)
    except Exception:
        return "unknown"

    if job.status.succeeded == 1:
        return "succeeded"
    if job.status.failed:
        return "failed"
    if job.status.active and job.status.active > 0:
        return "active"
    return "unknown"

# get the job logs
def get_job_logs(job_name):
    logger.debug(f"Retrieving logs for job {job_name}")
    pods = get_core_v1().list_namespaced_pod(
        namespace=NAMESPACE, 
        label_selector=f"job-name={job_name}"
    )

    if not pods.items:
        logger.warning(f"No pods found for job {job_name}")
        return None
    
    pod_name = pods.items[0].metadata.name
    logger.debug(f"Found pod {pod_name} for job {job_name}")
    
    logs = get_core_v1().read_namespaced_pod_log(
        name=pod_name,
        namespace=NAMESPACE
    )

    logger.debug(f"Retrieved logs for job {job_name}")
    return logs

def create_execution_job(submission_id, code, language):
    # Keep API compatibility for single-job execution, but internally
    # use the batch runner so we only need one execution entrypoint.
    return create_batch_execution_job([
        {"id": submission_id, "code": code, "language": language}
    ])

def count_active_batch_jobs():
    """Return how many batch runner jobs are currently active (not completed)."""
    jobs = get_batch_v1().list_namespaced_job(namespace=NAMESPACE)
    active = 0
    for job in jobs.items:
        if not job.metadata.name.startswith("batch-code-runner-"):
            continue

        # A job is active if it has any active pods.
        if job.status.active and job.status.active > 0:
            active += 1
            continue

        # In case active is missing, consider jobs without succeeded condition as active.
        if not job.status.succeeded:
            active += 1

    logger.debug(f"Found {active} active batch jobs")
    return active


def create_batch_execution_job(submissions_data):
    logger.info(f"Creating batch execution job for {len(submissions_data)} submissions")
    job_name = f"batch-code-runner-{uuid.uuid4().hex[:6]}"
    logger.debug(f"Generated batch job name: {job_name}")

    # volume mount for the container
    volume_mount = client.V1VolumeMount(
        name='tmp-volume',
        mount_path="/tmp"  # Standard path for Python's tempfile
    )

    # create a container
    container = client.V1Container(
        name="batch-code-executor",
        image="coderunner-sandbox:latest",
        volume_mounts=[volume_mount],
        image_pull_policy="Never",
        command=["python", "/sandbox/batch_run_code.py"],

        env=[
            client.V1EnvVar(name="SUBMISSIONS", value=json.dumps(submissions_data)),
            client.V1EnvVar(name="TMPDIR", value="/tmp"),
        ],

        resources=client.V1ResourceRequirements(
            limits={
                "memory": "256Mi", 
                "cpu": "500m"
            },
            requests={
                "cpu": "200m", 
                "memory": "128Mi"
            }   
        ),

        security_context=client.V1SecurityContext(
            run_as_non_root=True,
            run_as_user=1000,
            read_only_root_filesystem=True,
            allow_privilege_escalation=False,
            capabilities=client.V1Capabilities(
                drop=["ALL"]
            )
        )
    )

    # define the volume for the pod
    tmp_volume = client.V1Volume(
        name="tmp-volume",
        empty_dir=client.V1EmptyDirVolumeSource(medium="Memory")
    )

    pod_spec = client.V1PodSpec(
        restart_policy="Never",
        containers=[container],
        volumes=[tmp_volume],
        security_context=client.V1PodSecurityContext(
            run_as_non_root=True,
            fs_group=1000
        )
    )

    template = client.V1PodTemplateSpec(
        metadata=client.V1ObjectMeta(labels={"job-name": job_name}),
        spec=pod_spec
    )

    job_spec = client.V1JobSpec(
        template=template,
        backoff_limit=0,
        ttl_seconds_after_finished=60
    )

    job = client.V1Job(
        api_version="batch/v1",
        kind="Job",
        metadata=client.V1ObjectMeta(name=job_name),
        spec=job_spec
    )

    logger.info(f"Submitting batch job {job_name} to Kubernetes")
    get_batch_v1().create_namespaced_job(
        namespace=NAMESPACE,
        body=job
    )

    logger.info(f"Batch job {job_name} created successfully")
    return job_name