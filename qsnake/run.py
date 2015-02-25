#!/usr/bin/env python
import logging
import logging.handlers
from eve import Eve
import sys
import json
import os
from qsnake import schema, joblib
from bson.objectid import ObjectId


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

        user, params, data = item['user'], item['parameters'], item['data']
        jobid = str(item['_id'])
        barcode = item.get('barcode', jobid)
        dropbox = app.config['QPROJECT_DROPBOX']

        try:
            joblib.submit_job(
                workdir=app.config['JOB_WORKDIR'],
                timeout=app.config['START_JOB_TIMEO'],
                piddir=app.config['JOB_PID_DIR'],
                workflow=workflow,
                jobid=jobid,
                data=data,
                params=params,
                user=user,
                dropbox=dropbox,
                barcode=barcode,
                keep_workdir=item.get('keep_workdir', False),
            )
        except Exception:
            app.data.driver.db['jobs'].update(
                {'_id': ObjectId(jobid)},
                {'$set': {'running': False}}
            )
            item['running'] = False
            raise
        else:
            app.data.driver.db['jobs'].update(
                {'_id': ObjectId(jobid)},
                {'$set': {'running': True}}
            )
            item['running'] = True


def update_job_status(response):
    if not response['running']:
        return

    jobid = response['_id']
    running = joblib.job_status(
        app.config['JOB_WORKDIR'], app.config['JOB_PID_DIR'], str(jobid)
    )

    if not running:
        app.data.driver.db['jobs'].update(
            {'_id': jobid},
            {'$set': {'running': False}}
        )
        response['running'] = False


app.on_inserted_jobs += submit_job_batch
app.on_fetched_item_jobs += update_job_status


def main():
    app.run(debug=True)


if __name__ == '__main__':
    main()
