import tempfile
import subprocess
import signal
import logging
import json
import os

try:
    PermissionError
    ProcessLookupError
except NameError:
    PermissionError = OSError
    ProcessLookupError = OSError


logger = logging.getLogger(__name__)


def call_timeout(command, timeout):
    popen = subprocess.Popen(command)
    try:
        popen.wait(timeout=timeout)
    except subprocess.TimeoutExpired:
        logger.error("Process timed out: %s" % command)
        popen.kill()
        try:
            popen.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            logger.error("Process was killed but did not terminate in time. "
                         "Sending SIGKILL. Command was: %s " % command)
            popen.send_signal(signal.SIGKILL)
            popen.wait()
    return popen.returncode


def submit_job(workdir, timeout, piddir, workflow, jobid, data, params, user,
               dropbox, barcode, keep_workdir):
    repository, commit = workflow['repository'], workflow['commit']
    logger.info(
        "Starting new job %s. Workflow: %s, user: %s", jobid, repository, user
    )

    pidfile = os.path.join(piddir, jobid)

    with tempfile.NamedTemporaryFile('w') as tmp:
        json.dump(params, tmp.file)
        tmp.file.flush()
        command = [
            'qproject',
            'run',
            '--target', os.path.join(workdir, jobid),
            '--user', user,
            '--workflow', repository,
            '--commit', commit,
            '--params', tmp.name,
            '--data',
        ]
        command.extend(data)
        command += [
            '--jobid', jobid,
            '--daemon',
            '--pidfile', pidfile,
            '--dropbox', dropbox,
            '--barcode', barcode,
        ]

        if not keep_workdir:
            command.append('--cleanup')

        logger.debug("Starting qproject daemon for job %s: %s", jobid, command)
        retcode = call_timeout(command, timeout)
        if retcode:
            raise RuntimeError(
                "Failed to execute qproject. Returncode: %s" % retcode
            )


def job_status(workdir, piddir, jobid):
    jobdir = os.path.join(workdir, jobid)
    pidfile = os.path.join(piddir, jobid)

    if not os.path.exists(jobdir):
        if os.path.exists(pidfile):
            logger.error("Found pidfile %s but jobdir %s does not exists",
                         pidfile, jobdir)
        return False
    else:
        try:
            with open(pidfile) as f:
                pid = int(f.read())
                try:
                    os.kill(pid, 0)
                except ProcessLookupError:
                    logger.error(
                        "Pidfile %s exists but process is not running", pid
                    )
                    return False
                except PermissionError:
                    logger.error(
                        "Pidfile %s exists, but we do not have permissions to "
                        "send signals."
                    )
                    raise
                return pid

        except OSError:
            logger.error("Found jobdir %s but can not access pidfile %s",
                         jobdir, pidfile)
            return False


def abort_job(workdir, piddir, jobid):
    pid = job_status(workdir, piddir, jobid)
    if not pid:
        logger.warn("Trying to abort job %s, but it is not running.", jobid)

    logger.info("Sending SIGTERM to process group %s of job %s", pid, jobid)
    os.kill(pid)
