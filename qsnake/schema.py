workflows = {
    'item_title': 'workflow',

    'resource_methods': ['GET', 'POST'],

    'cache_control': 'max-age=10,must-revalidate',
    'cache_expires': 10,
    'schema': {
        'title': {
            'type': 'string',
            'minlength': 1,
            'required': True,
            'unique': False,
        },
        'parameters': {
            'type': 'dict',
        },
        'repository': {
            'type': 'string',
            'minlength': 1,
            'required': True,
        },
        'commit': {
            'type': 'string',
            'minlength': 1,
            'required': True,
            'writeonly': True,
        },
        'version': {
            'type': 'string',
            'minlength': 1,
            'required': False,
        },
        'graph': {
            'type': 'dict',
            'required': False,
        }
    }
}


jobs = {
    'item_title': 'job',
    'resource_methods': ['GET', 'POST'],

    'schema': {
        'workflow': {
            'type': 'objectid',
            'required': True,
            'data_relation': {
                'resource': 'workflows'
            },
            'embeddable': True,
        },
        'status': {
            'type': 'string',
            'allowed': ['failed', 'running', 'finished'],
        },
        'data': {
            'type': 'list',
            'schema': {
                'type': 'string'
            },
            'required': True,
        },
        'status_detail': {
            'type': 'dict',
            'required': False,
        },
        'no_submit': {
            'type': 'boolean',
            'required': False,
        },
        'parameters': {
            'type': 'dict',
            'required': True,
        },
        'user': {
            'type': 'string',
            'required': True,
        },
        'submit_on_POST': {
            'type': 'boolean',
            'required': True,
        }
    }
}


DOMAIN = {
    'jobs': jobs,
    'workflows': workflows,
}
