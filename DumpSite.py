import pushover
import dbus
import gobject
import os
import subprocess
import sys
import logging
import datetime
import glob
import shutil

debug_level = "DEBUG" #DEBUG or INFO
enable_pushover = True  #Enable pushover support to send a notification when completed
app_token   = "agGk4JzbsDRb98W6YtXLsCMuuZ78GC"  #Pushover app api key, must create your own api key
user_token  = "upTA78BinTDeivWZxLQnorhCijPnHE"  #Pushover user key, get this from your account page
unmount_on_fail = True    #if true unmounts the drive if there is a failure (no download folder, no files to dump, etc)
unmount_on_finish = True  #If true nmounts the drive after all files have been dumped
mount_location = "/mnt/external"  #Location you want the drive mounted to when connected
folder_to_dump = "Downloads"  #Path to folder to dump relative to mount point
dump_location = "/storage/Downloads"  #aboslute location to dump files to
clean_dumptruck = False #If true source folder will be emptied, If false a copy will remain in the source folder

#pushover.pushover(message="Hello, world",token = app_token,user = user_token,)
logging.basicConfig(format='%(asctime)s %(levelname)s:%(message)s', datefmt='%m/%d/%Y %I:%M:%S %p',filename='/var/log/dumpsite.log',level=logging.DEBUG)
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

		if device.QueryCapability("volume"):
			return self.do_something(device)
	def do_something(self, volume):
		device_file = volume.GetProperty("block.device")
		label = volume.GetProperty("volume.label")
		fstype = volume.GetProperty("volume.fstype")
		mounted = volume.GetProperty("volume.is_mounted")
		mount_point = volume.GetProperty("volume.mount_point")
		try:
			size = volume.GetProperty("volume.size")
		except:
			size = 0
			
		print "New storage device detectec:"
		print "  device_file: %s" % device_file
		print "  label: %s" % label
		print "  fstype: %s" % fstype
		if mounted:
			print "  mount_point: %s" % mount_point
		else:
			print "  not mounted"
		print "  size: %s (%.2fGB)" % (size, float(size) / 1024**3)

		return_code = subprocess.call(["mount", "-t" , fstype, device_file, mount_location])
		print(str(return_code))
		if return_code == 0:
			logging.info('drive mounted successesfully!')
			if os.path.exists(mount_location + "/" + folder_to_dump):
				logging.info("Found a folder to dump from")
				
				number_to_dump = len(glob.glob(mount_location + "/" + folder_to_dump + "/*"))  #find the number of files in the folder to be dumped
				logging.info("there are " + str(number_to_dump) + " items to dump")  #log the number of files
				source = os.listdir(mount_location+"/"+folder_to_dump+"/")
				for files in source:
					logging.debug("copying " + mount_location+"/"+folder_to_dump+"/"+files +" to " + dump_location)
					try:
						if clean_dumptruck  == True:
							print("move")#move files instead of copy
						elif clean_dumptruck == False:
							shutil.copy(mount_location + "/" + folder_to_dump + "/" + files ,dump_location)
					except IOError, e:
						logging.warning("Unable to copy file. %s" %e)
				#	except shutil.Error, exc:
				#		errors = exc.args[0]
				#		for error in errors:
				#			src, dst, msg = error
				if unmount_on_finish:
					subprocess.call(["umount",device_file])
					logging.debug(device_file + " unmounted")
					pushover.pushover(message= str(number_to_dump) + "successfully dumped to " + dump_location,token = app_token,user = user_token,)

			else:
				logging.info("Found no folder to dump from")
				if unmount_on_fail:
					subprocess.call(["umount",device_file])
					logging.debug(device_file + " unmounted")
				
		if return_code == 1:
			logging.debug('incorrect invocation or permissions')
		elif return_code == 2:
			logging.debug('system error, out of memory, cannot fork, no more loop devices')
		elif return_code == 4:
			logging.debug('internal mount bug or missing nfs support in mount')
		elif return_code == 8:
			logging.debug('user interrupt')
		elif return_code == 16:
			logging.debug('problems writing or locking /etc/mtab')
		elif return_code == 32:
			logging.info('mount failure')
		elif return_code == 64:
			logging.debug('some mount succeded')
		else:
			logging.warning('mount failed for an unknown reason, mount code: ' + str(return_code))
			
if __name__ == '__main__':
	from dbus.mainloop.glib import DBusGMainLoop
	DBusGMainLoop(set_as_default=True)
	loop = gobject.MainLoop()
	DeviceAddedListener()
	loop.run()