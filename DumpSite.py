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
import os
import subprocess
import sys
import logging
import logging.handlers
import datetime
import glob
import shutil
import atexit

debug_level = "DEBUG" #DEBUG or INFO
enable_pushover = True  #Enable pushover support to send a notification when completed
app_token   = ""  #Pushover app api key, must create your own api key
user_token  = ""  #Pushover user key, get this from your account page
unmount_on_fail = True    #if true unmounts the drive if there is a failure (no download folder, no files to dump, etc)
unmount_on_finish = True  #If true nmounts the drive after all files have been dumped
mount_location = "/mnt/external"  #Location you want the drive mounted to when connected
folder_to_dump = "Downloads"  #Path to folder to dump relative to mount point
dump_location = "/storage/Downloads"  #aboslute location to dump files to
clean_dumptruck = False #If true source folder will be emptied, If false a copy will remain in the source folder

def endprog():
	logging.info('DumpSite service stopping')

logging.basicConfig(format='%(asctime)s %(levelname)s:%(message)s', datefmt='%m/%d/%Y %I:%M:%S %p',filename='/var/log/dumpsite.log',level=logging.DEBUG)
logging.handlers.TimedRotatingFileHandler(filename='/var/log/dumpsite.log', when='midnight',backupCount=7, encoding=None, delay=False, utc=False)
logging.info('DumpSite service started')
dumpsource = mount_location+"/"+folder_to_dump
dirs_dumped = 0
files_dumped = 0

#routine that does the file transfers	
def transfer(device_file):
	global dirs_dumped
	global files_dumped
	
	if os.path.exists(mount_location + "/" + folder_to_dump): #check if the mounted drive has a folder to get stuff from
		logging.info("Found a folder to dump from") 
		number_to_dump = len(glob.glob(mount_location + "/" + folder_to_dump + "/*"))  #find the number of files in the folder to be dumped
		if number_to_dump > 0:  #if there are files lets dump em, otherwise what are we doing here?
			logging.info("there are " + str(number_to_dump) + " items to dump")  #log the number of files
			
			for dirname in os.walk(dumpsource).next()[1]: #copy the dirs inside the folder to be dumped
				try:
					logging.debug("copying folder: "+dirname +" to " + dump_location) #call off the transfer with from and to
					shutil.copytree(dumpsource+"/"+dirname+"/",dump_location+"/"+dirname) #copy folders
					dirs_dumped += 1
				#rutrow something went wrong...this is as good as it gets now, eventually better debugging
				except OSError as err_msg:
					logging.warning("Encountered an OSError, unable to copy dir: " + dirname)
					logging.warning(err_msg)
				except shutil.Error, err_msg:
					logging.warning("Encountered an shutil error, unable to copy dir: " + dirname)
					logging.warning(err_msg)
				except IOError, err_msg:
					logging.warning("Encountered an IOError, unable to copy dir: " + dirname)
					logging.warning(err_msg)
			
			for filename in os.walk(dumpsource).next()[2]: #copy the files inside the folder to be dumped
				logging.debug("copying file: "+filename +" to " + dump_location) #call off the transfer with from and to
				#if the user wants a clean dumptruck move the files, otherwise just copy the files
				try:
						logging.debug("copying file: "+filename+" to "+dump_location) #call off the transfer with from and to
						shutil.copy(mount_location + "/" + folder_to_dump  + "/" + filename , dump_location) #copy files
						files_dumped += 1
				except shutil.Error, err_msg:
				#rutrow something went wrong...this is as good as it gets now, eventually better debugging
					logging.warning("Unable to copy file: " + dirname)
					logging.warning(err_msg)
				except IOError, err_msg:
				#rutrow something went wrong...this is as good as it gets now, eventually better debugging
					logging.warning("Unable to copy file: " + dirname)
					logging.warning(err_msg)

			logging.info("done transfering files, see you next time")
			#pushover(True,dirs_dumped,files_dumped)
			pushover.pushover(message="Successfully dumped "+str(dirs_dumped)+" folders and "+str(files_dumped)+" files to "+ dump_location,token = app_token,user = user_token,)
			
			if clean_dumptruck:
			#if the user wants a clean dumptruck move the files, otherwise just copy the files
				logging.debug("this doesnt do anything yet")
			
			if unmount_on_finish:  
			#if user elected to unmount on finish then boot that drive out of the system
				subprocess.call(["umount",device_file])
				logging.info(device_file + " unmounted")
				
		else:
			#if the users wants an unmount on a soft fail then the dude abides
			logging.info("Found nothing to dump")
			if unmount_on_fail:
				subprocess.call(["umount",device_file])
				logging.info(device_file + " unmounted")
			
	else:
		#if the users wants an unmount on a soft fail then the dude abides
		logging.info("Found no folder to dump from")
		if unmount_on_fail:
			subprocess.call(["umount",device_file])
			logging.info(device_file + " unmounted")

class DeviceAddedListener:
	def __init__(self):
		self.bus = dbus.SystemBus()
		self.hal_manager_obj = self.bus.get_object("org.freedesktop.Hal","/org/freedesktop/Hal/Manager")
		self.hal_manager = dbus.Interface(self.hal_manager_obj,"org.freedesktop.Hal.Manager")
		self.hal_manager.connect_to_signal("DeviceAdded", self._filter)

	def _filter(self, udi):
		device_obj = self.bus.get_object ("org.freedesktop.Hal", udi)
		device = dbus.Interface(device_obj, "org.freedesktop.Hal.Device")

		if device.QueryCapability("volume"): #if the dbus event is a device with a mountable volume lets use it
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




