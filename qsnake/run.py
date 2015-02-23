#!/usr/bin/env python
import logging
import logging.handlers
from eve import Eve
import sys
import json
import os
from . import schema
from . import joblib


try:
    with open('/etc/qsnake.json', 'r') as f:
        etc_config = json.load(f)
        assert 'flask' in etc_config
        assert 'eve' in etc_config
        if 'debug' not in etc_config['flask']:
            raise ValueError(
                "'debug' must be specified if /etc/qsnake.json is used"
            )
except OSError:
    etc_config = {'flask': {}, 'eve': {}}

with open(os.path.join(os.path.dirname(__file__), 'default_config.json')) as f:
    config = json.load(f)

assert 'eve' in config
assert 'flask' in config

config['flask'].update(etc_config['flask'])
config['eve'].update(etc_config['eve'])

config['eve']['DOMAIN'] = schema.DOMAIN

app = Eve(__name__, settings=config['eve'])
app.config.update(config['flask'])

if app.debug:
    handler = logging.StreamHandler(sys.stdout)
else:
    handler = logging.handlers.SysLogHandler('/dev/log')

app.logger.addHandler(handler)
logging.getLogger('joblib').addHandler(handler)


def submit_job_batch(items):
    for item in items:
        if not item['submit_on_POST']:
            app.logger.info("Got job POST, but submit_on_POST was not set.")
            continue

        workflows = app.data.driver.db['workflows']
        workflow = workflows.find_one({'_id': item['workflow']})
        if not workflow:
            app.logger.error("Got invalid job request: workflow %s could not "
                             "be found", item['workflow'])

        user, params, data = item['user'], item['params'], item['data']
        jobid = str(item['_id'])

        joblib.submit_job(
            app.config['JOB_WORKDIR'],
            app.config['START_JOB_TIMEO'],
            os.path.join(app.config['JOB_PID_DIR'], jobid),
            workflow,
            jobid,
            data,
            params,
            user
        )


app.on_inserted_jobs += submit_job_batch


def main():
    app.run()


if __name__ == '__main__':
    main()
