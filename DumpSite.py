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
import pushover
import dbus
import gobject
import subprocess
import logging
import logging.handlers
import atexit
import transfer

debug_level = "DEBUG" #DEBUG or INFO


def endprog():
    logging.info('DumpSite service stopping')

logging.basicConfig(format='%(asctime)s %(levelname)s:%(message)s', datefmt='%m/%d/%Y %I:%M:%S %p',filename='/var/log/dumpsite.log',level=logging.DEBUG)
logging.handlers.TimedRotatingFileHandler(filename='/var/log/dumpsite.log', when='midnight',backupCount=7, encoding=None, delay=False, utc=False)
logging.info('DumpSite service started')


class DeviceAddedListener:
    def __init__(self):
        self.bus = dbus.SystemBus()
        self.hal_manager_obj = self.bus.get_object("org.freedesktop.Hal","/org/freedesktop/Hal/Manager")
        self.hal_manager = dbus.Interface(self.hal_manager_obj,"org.freedesktop.Hal.Manager")
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
        return_code = subprocess.call(["mount", "-t" , fstype, device_file, mount_location])

        if return_code == 0:
            logging.info('drive mounted successesfully!')
            transfer(device_file,label,fstype,mounted,mount_point,size)
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

if __name__ == '__main__':
    from dbus.mainloop.glib import DBusGMainLoop
    atexit.register(endprog)
    DBusGMainLoop(set_as_default=True)
    loop = gobject.MainLoop()
    DeviceAddedListener()
    loop.run()




