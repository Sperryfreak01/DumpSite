############################################################################### 
#																			  #
# DumpSite python script													  #
# https://github.com/Sperryfreak01/DumpSite									  #
#																			  #
# Copyright 2013 Matt Lovett 										  		  #
#																			  #
# This program is free software: you can redistribute it and/or modify		  #
# it under the terms of the GNU General Public License as published by		  #
# the Free Software Foundation, either version 3 of the License, or			  #
# (at your option) any later version.										  #
# 																			  #
# This program is distributed in the hope that it will be useful,	 	  	  #
# but WITHOUT ANY WARRANTY; without even the implied warranty of			  #
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the				  #
# GNU General Public License for more details.								  #
# 																			  #
# You should have received a copy of the GNU General Public License			  #
# along with this program.  If not, see <http://www.gnu.org/licenses/>.		  #
# 																			  #
###############################################################################
import dbus
import gobject
import subprocess
import logging
import logging.handlers
import atexit
import transfer
import ConfigParser
import notifications

testing = False

config = ConfigParser.RawConfigParser()
config.read('DumpSite.cfg')

#Load general settings from the config file
try:
    logging_level = config.get('GENERAL', 'debug-level')
    mount_location = config.get('GENERAL', 'mount-location')
    folder_to_dump = config.get('GENERAL', 'folder-to-dump')
    dump_location = config.get('GENERAL', 'dump-location')
    unmount_on_fail = config.get('GENERAL', 'unmount-on-fail')
    unmount_on_finish = config.get('GENERAL', 'unmount-on-finish')
    clean_dumptruck = config.getboolean('GENERAL', 'clean-dumptruck')
except ConfigParser.NoSectionError as err_msg:
    logging.warning("Encountered an error loading settings, can not find section")
    logging.warning(err_msg)
except ConfigParser.NoOptionError as err_msg:
    logging.warning("Encountered an error loading settings, can not find valid setting")
    logging.warning(err_msg)

    #Load pushover settings from the config file
try:
    pushover_enabled = config.getboolean('PUSHOVER', 'enabled')
    app_token = config.get('PUSHOVER', 'app-token')
    user_token = config.get('PUSHOVER', 'user-token')
except ConfigParser.NoSectionError as err_msg:
    logging.warning("Encountered an error loading settings, can not find section")
    logging.warning(err_msg)
    pushover_enabled = False
except ConfigParser.NoOptionError as err_msg:
    logging.warning("Encountered an error loading settings, can not find valid setting")
    logging.warning(err_msg)
    pushover_enabled = False

#Load sickbeard settings from the config file
try:
    sb_enabled = config.getboolean('SICKBEARD', 'enabled')
    sickbeard_location = config.get('SICKBEARD', 'location')
    sb_host = config.get('SICKBEARD', 'host')
    sb_port = config.get('SICKBEARD', 'port')
    sb_username = config.get('SICKBEARD', 'username')
    sb_password = config.get('SICKBEARD', 'password')
    sb_ssl = config.get('SICKBEARD', 'ssl')
except ConfigParser.NoSectionError as err_msg:
    logging.warning("Encountered an error loading settings, can not find section")
    logging.warning(err_msg)
    sb_enabled = False
except ConfigParser.NoOptionError as err_msg:
    logging.warning("Encountered an error loading settings, can not find valid setting")
    logging.warning(err_msg)
    sb_enabled = False

#Load couchpotato settings from the config file
try:
    cp_enabled = config.getboolean('COUCHPOTATO', 'enabled')
    cp_api = config.get('COUCHPOTATO', 'api')
    cp_host = config.get('COUCHPOTATO', 'host')
    cp_port = config.get('COUCHPOTATO', 'port')
except ConfigParser.NoSectionError as err_msg:
    logging.warning("Encountered an error loading settings, can not find section")
    logging.warning(err_msg)
    cp_enabled = False
except ConfigParser.NoOptionError as err_msg:
    logging.warning("Encountered an error loading settings, can not find valid setting")
    logging.warning(err_msg)
    cp_enabled = False

log_type = ('logging.'+logging_level)
logging.basicConfig(format='%(asctime)s %(levelname)s:%(message)s', datefmt='%m/%d/%Y %I:%M:%S %p',filename='/var/log/dumpsite.log',level=logging.DEBUG)
logging.handlers.TimedRotatingFileHandler(filename='/var/log/dumpsite.log', when='midnight',backupCount=7, encoding=None, delay=False, utc=False)
logging.info('DumpSite service started')

def endprog():
    logging.info('DumpSite service stopping')


class DeviceAddedListener:
    def __init__(self):
        self.bus = dbus.SystemBus()
        self.hal_manager_obj = self.bus.get_object("org.freedesktop.Hal", "/org/freedesktop/Hal/Manager")
        self.hal_manager = dbus.Interface(self.hal_manager_obj, "org.freedesktop.Hal.Manager")
        self.hal_manager.connect_to_signal("DeviceAdded", self._filter)

    def _filter(self, udi):
        device_obj = self.bus.get_object ("org.freedesktop.Hal", udi)
        device = dbus.Interface(device_obj, "org.freedesktop.Hal.Device")

        if device.QueryCapability("volume"):  # if the dbus event is a device with a mountable volume lets use it
            return self.do_something(device)
    def do_something(self, volume):
        #getting the detected device's info
        device_file = volume.GetProperty("block.device")
        label = volume.GetProperty("volume.label")
        fstype = volume.GetProperty("volume.fstype")
        mounted = volume.GetProperty("volume.is_mounted")
        mount_point = volume.GetProperty("volume.mount_point")
        try:
            size = volume.GetProperty("volume.size")
        except:
            size = 0

        #log the detected devices info if debugging enabled
        logging.debug("New storage device detected:")
        logging.debug("  device_file: %s" % device_file)
        logging.debug("  label: %s" % label)
        logging.debug("  fstype: %s" % fstype)
        if mounted:
            logging.debug("  mount_point: %s" % mount_point)
        else:
            logging.debug("  not mounted")
        logging.debug("  size: %s (%.2fGB)" % (size, float(size) / 1024**3))

        #Lets try and mount the SOB, if it works we should get a return of 0
        logging.debug("mount command:  mount -t" + fstype + device_file + mount_location)
        return_code = subprocess.call(["mount", "-t", fstype, device_file, mount_location])

        if return_code == 0:
            logging.info('drive mounted successfully!')
            transfer_status, dirs_dumped, files_dumped = transfer.transferfiles(device_file, mount_location, folder_to_dump, dump_location,clean_dumptruck)
        #mount return/failure codes
        if return_code == 1:
            logging.warning('incorrect invocation or permissions')
        elif return_code == 2:
            logging.warning('system error, out of memory, cannot fork, no more loop devices')
        elif return_code == 4:
            logging.warning('internal mount bug or missing nfs support in mount')
        elif return_code == 8:
            logging.warning('user interrupt')
        elif return_code == 16:
            logging.warning('problems writing or locking /etc/mtab')
        elif return_code == 32:
            logging.warning('mount failure')
        elif return_code == 64:
            logging.warning('some mount succeded')
        else:
            logging.warning('mount failed for an unknown reason, mount code: ' + str(return_code))

        if transfer_status == 0:
            logging.info("done transfering files, see you next time")

            if pushover_enabled:
                try:
                    notifications.pushover(message="Successfully dumped "+str(dirs_dumped)+" folders and "+str(files_dumped) + " files to " + dump_location, token = app_token, user = user_token)
                    logging.debug('Notified Pushover successfully')
                except notifications.PushoverError, err:
                    logging.warning('Pushover encounted an error message not sent')
                    logging.warning(err)

            if sb_enabled:
                notifications.sickbeard(sickbeard_location, dump_location)

            if cp_enabled:
                notifications.couchpotato(dump_location,cp_host,cp_port,cp_api)

            if unmount_on_finish:
            #if user elected to unmount on finish then boot that drive out of the system
                subprocess.call(["umount", device_file])
                logging.info(device_file + " unmounted")

        if transfer_status == 1:
            #if the users wants an unmount on a soft fail then the dude abides
            logging.info("Found nothing to dump")
            if unmount_on_fail:
                subprocess.call(["umount", device_file])
                logging.info(device_file + " unmounted")

        if transfer_status == 2:
            #if the users wants an unmount on a soft fail then the dude abides
            logging.info("Found no folder to dump from")
            if unmount_on_fail:
                subprocess.call(["umount", device_file])
                logging.info(device_file + " unmounted")


if __name__ == '__main__':
    if testing:
        device_file = "this is only a test"
        transfer_status, dirs_dumped, files_dumped = transfer.transferfiles(device_file, mount_location, folder_to_dump, dump_location,clean_dumptruck)
        if transfer_status == 0:
            logging.info("done transfering files, see you next time")
            if pushover_enabled:
                try:
                    notifications.pushover(message="Successfully dumped "+str(dirs_dumped)+" folders and "+str(files_dumped) + " files to " + dump_location, token = app_token, user = user_token)
                    logging.debug('Notified Pushover successfully')
                except notifications.PushoverError, err:
                    logging.warning('Pushover encounted an error message not sent')
                    logging.warning(err)

            if sb_enabled:
                notifications.sickbeard(sickbeard_location, dump_location)

            if cp_enabled:
                notifications.couchpotato(dump_location,cp_host,cp_port,cp_api)

            if unmount_on_finish:
            #if user elected to unmount on finish then boot that drive out of the system
                subprocess.call(["umount", device_file])
                logging.info(device_file + " unmounted")
        if transfer_status == 1:
            #if the users wants an unmount on a soft fail then the dude abides
            logging.info("Found nothing to dump")
            if unmount_on_fail:
                subprocess.call(["umount", device_file])
                logging.info(device_file + " unmounted")
        if transfer_status == 2:
            #if the users wants an unmount on a soft fail then the dude abides
            logging.info("Found no folder to dump from")
            if unmount_on_fail:
                subprocess.call(["umount", device_file])
                logging.info(device_file + " unmounted")
    else:
        from dbus.mainloop.glib import DBusGMainLoop
        atexit.register(endprog)
        DBusGMainLoop(set_as_default=True)

        loop = gobject.MainLoop()
        DeviceAddedListener()
        loop.run()




