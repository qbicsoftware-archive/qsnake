from qsnake import joblib
from unittest import mock


def test_call_timeout():
    assert joblib.call_timeout(["ls"], 1) == 0
    assert joblib.call_timeout(["sleep", "1"], .1) != 0


@mock.patch('qsnake.joblib.call_timeout')
def test_submit_job(call):
    jobid = "123456"
    workflow = {'repository': "repo", 'commit': 'commit1'}
    joblib.submit_job("/tmp", 1, "/tmp", workflow, jobid, ['data1', 'data2'],
                      {'hi': 5, 'blubb': [1, 2]}, "me")

    assert call.called
