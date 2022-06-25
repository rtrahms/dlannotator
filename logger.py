import os
from datetime import datetime
import os

class Logger:
    def __init__(self, log_file_dir):

        self.log_file_dir = "unknown"
        self.log_file_prefix = "dlannotator_log_"
        self.logging_enabled = False

        # check if event log dir is not assigned
        if log_file_dir != "Event Log File Path Unassigned":
            self.logging_enabled = True

            # check if directory exists, if not, create it
            if os.path.isdir(log_file_dir) == False:
                os.mkdir(log_file_dir)

            # assemble full path for filename and store it
            timestamp = datetime.now()
            self.log_file_full_path = log_file_dir + "/" + self.log_file_prefix + timestamp.strftime("%m-%d-%Y_%H-%M-%S") + ".txt"

            self.log_filestream = None

    def log(self, event_string):

        if self.logging_enabled == False:
            return

        self.log_filestream = open(self.log_file_full_path,"a")
        timestamp = datetime.now()
        self.log_filestream.write(timestamp.strftime("%m-%d-%Y_%H:%M:%S") + ": " + event_string + "\n")
        self.log_filestream.close()


    def close(self):

        if self.logging_enabled == False:
            return

        self.log_filestream.close()
        return
