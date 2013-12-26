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
import logging
import logging.handlers
import glob
import shutil


dirs_dumped = 0
files_dumped = 0

#routine that does the file transfers
def transferfiles(device_file, mount_location, folder_to_dump, dump_location,cleanup):
    dumpsource = mount_location+"/"+folder_to_dump
    global dirs_dumped
    global files_dumped
    if os.path.exists(dump_location):  # check if the mounted drive has a dump folder
        logging.debug('dump location exists')
    else:
        logging.debug('dump location doesnt exist, trying to create')
        try:
            os.makedirs(dump_location)
            logging.debug('dump locaion created successfully')
        except OSError as err_msg:
            logging.warning("Encountered an OSError, unable to create dump location")
            logging.warning(err_msg)

    if os.path.exists(mount_location + folder_to_dump):  # check if the mounted drive has a dump folder
        logging.info("Found a folder to dump from")
        number_to_dump = len(glob.glob(mount_location + "/" + folder_to_dump + "/*"))  # find the number of files in the folder to be dumped
        if number_to_dump > 0:  # if there are files lets dump em, otherwise what are we doing here?
            logging.info("there are " + str(number_to_dump) + " items to dump")  # log the number of files

            for dirname in os.walk(dumpsource).next()[1]:  # copy the dirs inside the folder to be dumped
                try:
                    logging.debug("copying folder: "+dirname + " to " + dump_location)  # call off the transfer with from and to
                    shutil.copytree(dumpsource+"/"+dirname+"/", dump_location+"/"+dirname) # copy folders
                    dirs_dumped += 1
                    if cleanup:
                    #if the user wants a clean dumptruck move the files, otherwise just copy the files
                         logging.debug("this doesnt do anything yet")

                # rutrow something went wrong...this is as good as it gets now, eventually better debugging
                except OSError as err_msg:
                    logging.warning("Encountered an OSError, unable to copy dir: " + dirname)
                    logging.warning(err_msg)
                except shutil.Error, err_msg:
                    logging.warning("Encountered an shutil error, unable to copy dir: " + dirname)
                    logging.warning(err_msg)
                except IOError, err_msg:
                    logging.warning("Encountered an IOError, unable to copy dir: " + dirname)
                    logging.warning(err_msg)

            for filename in os.walk(dumpsource).next()[2]: # copy the files inside the folder to be dumped
                logging.debug("copying file: "+filename + " to " + dump_location)  # call off the transfer with from and to
                #if the user wants a clean dumptruck move the files, otherwise just copy the files
                try:
                        logging.debug("copying file: "+filename+" to "+dump_location)  # call off the transfer with from and to
                        shutil.copy(mount_location + "/" + folder_to_dump  + "/" + filename , dump_location) # copy files
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

            #return 0 on successfully completing a dump
            return(0,dirs_dumped,files_dumped)

        else:
            #return a 1 if the dump failed because there were no files
            return(1,0,0)

    else:
        #return a 1 if the dump failed because the source folder wasnt found
        return(2,0,0)





