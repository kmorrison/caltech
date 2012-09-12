from datetime import timedelta
from datetime import datetime
import httplib2
import itertools
from apiclient.discovery import build
from oauth2client.client import OAuth2WebServerFlow
from oauth2client.client import AccessTokenRefreshError
from oauth2client.client import flow_from_clientsecrets
from oauth2client.file import Storage
from oauth2client.tools import run

import lib

CLIENT_SECRETS = 'auth.json'
TIME_FORMAT = "%Y-%m-%dT%H:%M:%SZ"

def build_service():
    # Set up a Flow object to be used if we need to authenticate.
    FLOW = flow_from_clientsecrets(
            CLIENT_SECRETS,
            scope='https://www.googleapis.com/auth/calendar',
            message=""
    )
    storage = Storage('schedule.dat')

    credentials = storage.get()
    if credentials is None or credentials.invalid:
        credentials = run(FLOW, storage)

    # Create an httplib2.Http object to handle our HTTP requests and authorize it
    # with our good Credentials.
    http = httplib2.Http()
    http = credentials.authorize(http)

    service = build('calendar', 'v3', http=http)
    return service