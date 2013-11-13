__author__ = 'matt'


import sys
import urllib
import os.path
import ConfigParser

class AuthURLOpener(urllib.FancyURLopener):
    def __init__(self, user, pw):
        self.username = user
        self.password = pw
        self.numTries = 0
        urllib.FancyURLopener.__init__(self)

    def prompt_user_passwd(self, host, realm):
        if self.numTries == 0:
            self.numTries = 1
            return (self.username, self.password)
        else:
            return ('', '')

    def openit(self, url):
        self.numTries = 0
        return urllib.FancyURLopener.open(self, url)


def processEpisode(dirName, nzbName=None):

    config = ConfigParser.ConfigParser()
    configFilename = os.path.join(os.path.dirname(sys.argv[0]), "autoProcessTV.cfg")
    print "Loading config from", configFilename

    if not os.path.isfile(configFilename):
        print "ERROR: You need an autoProcessTV.cfg file - did you rename and edit the .sample?"
        sys.exit(-1)

    try:
        fp = open(configFilename, "r")
        config.readfp(fp)
        fp.close()
    except IOError, e:
        logging.warning("Could not read configuration file: " + str(e))

    host = config.get("SickBeard", "host")
    port = config.get("SickBeard", "port")
    username = config.get("SickBeard", "username")
    password = config.get("SickBeard", "password")
    try:
        ssl = int(config.get("SickBeard", "ssl"))
    except (ConfigParser.NoOptionError, ValueError):
        ssl = 0

    try:
        web_root = config.get("SickBeard", "web_root")
    except ConfigParser.NoOptionError:
        web_root = ""

    params = {}

    params['quiet'] = 1

    params['dir'] = dirName
    if nzbName != None:
        params['nzbName'] = nzbName

    myOpener = AuthURLOpener(username, password)

    if ssl:
        protocol = "https://"
    else:
        protocol = "http://"

    url = protocol + host + ":" + port + web_root + "/home/postprocess/processEpisode?" + urllib.urlencode(params)

    logging.debug("Opening URL: " + url+

    try:
        urlObj = myOpener.openit(url)
    except IOError, e:
        logging.warning("Unable to open URL: " + str(e))

