#!/usr/bin/env python
import logging
from eve import Eve
from flask import g, abort
import zmq
import sys

logging.basicConfig(stream=sys.stdout, level=logging.DEBUG)

logger = logging.getLogger("WorkflowServer")
app = Eve()


JOB_SERVER = "ipc://./jobserver.socket"
START_JOB_RETRIES = 1
START_JOB_TIMEO = 1000

zmq_ctx = zmq.Context()


def get_job_socket():
    if hasattr(g, 'job_socket'):
        assert hasattr(g, 'job_socket_poll')
    else:
        g.job_socket = zmq_ctx.socket(zmq.REQ)
        g.job_socket_poll = zmq.Poller()

        g.job_socket.connect(JOB_SERVER)
        g.job_socket_poll.register(g.job_socket, zmq.POLLIN)

    return g.job_socket, g.job_socket_poll


def replace_job_socket(socket):
    g.job_socket = socket


def submit_job(items):
    for item in items:
        if not item['submit_on_POST']:
            continue
        logger.info("Requesting job execution on JobServer")

        workflows = app.data.driver.db['workflows']
        workflow = workflows.find_one({'_id': item['workflow']})
        jobid = str(item['_id'])
        logger.info(workflow)

        message = {
            'command': 'execute',
            'repository': workflow['repository'],
            'commit': workflow['commit'],
            'jobid': jobid,
            'user': item['user'],
            'data': item['data'],
        }

        socket, poll = get_job_socket()

        retries = START_JOB_RETRIES
        while retries:
            logger.debug("Sending %s to job server" % message)
            socket.send_json(message)

            expect_reply = True
            while expect_reply:
                socks = dict(poll.poll(START_JOB_TIMEO))
                if socks.get(socket) == zmq.POLLIN:
                    reply = socket.recv_json()
                    logger.debug("Got reply from job serever: %s" % reply)
                    if 'status' not in reply:
                        logger.critical("Got invalid response from "
                                        "job server: %s" % reply)
                        abort(500)
                    if reply['status'] != 'started' in reply:
                        logger.warn("Job server could not execute request "
                                    "for jobid %s. Message from job server: %s"
                                    % (jobid, reply))
                        abort(500)
                    else:
                        update_job_started(reply)
                        return
                socket.setsockopt(zmq.LINGER, 0)
                socket.close()
                poll.unregister(socket)
                retries -= 1
                if not retries:
                    logger.error("Job executor did not respond to request, "
                                 "maximum number of retries reached")
                    # TODO update db entry
                    abort(500)
                logger.warn("Did not receive response from job executor. "
                            "retrying...")
                socket = zmq_ctx.socket(zmq.REQ)
                socket.connect(JOB_SERVER)
                poll.register(socket, zmq.POLLIN)
                replace_job_socket(socket)
                socket.send_json(message)


def update_job_started(reply):
    logger.info("Reply from job server: %s" % reply)


app.on_inserted_jobs += submit_job

if __name__ == '__main__':
    app.run(debug=True)
