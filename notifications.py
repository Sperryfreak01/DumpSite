import urllib
import urllib2
import urlparse
import json
import os
import subprocess
import logging
import logging.handlers

PUSHOVER_API = "https://api.pushover.net/1/"

class PushoverError(Exception): pass

def pushover(**kwargs):
    assert 'message' in kwargs

    if not 'token' in kwargs:
        kwargs['token'] = os.environ['PUSHOVER_TOKEN']
    if not 'user' in kwargs:
        kwargs['user'] = os.environ['PUSHOVER_USER']

    url = urlparse.urljoin(PUSHOVER_API, "messages.json")
    data = urllib.urlencode(kwargs)
    req = urllib2.Request(url, data)
    try:
        response = urllib2.urlopen(req)
        output = response.read()
        data = json.loads(output)
    except urllib2.HTTPError, httperror:

        raise PushoverError(httperror)

    if data['status'] != 1:
        raise PushoverError(output)

def sickbeard(sb_location, location):
    try:
        subprocess.call(["python", sb_location + '/autoProcessTV/autoProcessTV.py', location])
        logging.debug('Triggered a SickBeard scan of DumpFolder')
    except:
        logging.warning('Unable to reach SickBeard, check your config')

def couchpotato(location,host,port,api,):
    try:
        params = urllib.urlencode({'movie_folder': location})
        urllib.urlopen(host + ':' + port + '/api/' + api + '/renamer.scan/?' + params)
        logging.debug('Triggered a CouchPotato scan of DumpFolder')
    except IOError, err_msg:
        logging.warning('Unable to reach CouchPotato, check your config')
        logging.warning(err_msg)