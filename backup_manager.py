import os
import subprocess
import yaml
import argparse
import datetime
import re
import logging
from crontab import CronTab
CONFIG_LOCATION = "" # PLEASE SET THIS! (The program will error out if you don't ;))
LOG_LOCATION = "" # PLEASE ALSO SET THIS! (The program will also error out here if not set)

# Reads the configuration file and produces a dictionary that the rest of the program can use
class parsing:
    def __init__(self, config_location: str):
        self.__config_location = config_location
        self.__reading_file()
    
    def __reading_file(self):
        with open(self.__config_location, 'r') as file:
            self.__config = yaml.safe_load(file)
    
    # Checks section in user@host
    def __section_format_check(self):
        for section in self.__config:
            valid = re.findall(r"^\w+@\w+$", section)
            if not valid:
                raise ValueError("Section titles need to be of form user@host, yours is {SECTION}".format(SECTION=section))
    
    def __backup_format_check(self):
        for section in self.__config:
            for backup in self.__config.get(section):
                # Length check
                if len(backup) != 5:
                    raise ValueError("Backups need to have 5 variables, yours is {BACKUP}".format(BACKUP=backup))
                # Backup type check
                if backup[0] not in ["tar", "db", "dir", "file"]:
                    raise ValueError("The first backup section can only be tar,db,dir or file, yours is {BACKUP_SECTION}".format(BACKUP_SECTION=backup[0]))
                # File paths valid check
                valid = re.findall(r"^\/", backup[1])
                if not valid:
                    raise ValueError("The path on the foreign machine must be absolute, e.g starting with /, yours is {BACKUP_SECTION}".format(BACKUP_SECTION=backup[1]))
                valid = re.findall(r"^\/", backup[2])
                if not valid:
                    raise ValueError("The path on the local machine must be absolute, e.g starting with /, yours is {BACKUP_SECTION}".format(BACKUP_SECTION=backup[2]))
                # Frequency check
                valid = re.findall(r"^((cron: )|((\d+)(MONTH)?$))", str(backup[3]))
                if not valid:
                    raise ValueError("The frequency defined must have a be of the form int or intMONTH, yours is {BACKUP_SECTION}.".format(BACKUP_SECTION=backup[3]))
                # Iterations check
                valid = re.findall(r"^\d+$", str(backup[4]))
                if not valid:
                    raise ValueError("The number of iterations must be a positive integer, yours is {BACKUP_SECTION}".format(BACKUP_SECTION=backup[4]))
    
    def __syntax_check(self):
        self.__section_format_check()
        self.__backup_format_check()

    def GetReadFile(self) -> dict:
        self.__syntax_check()
        return self.__config

# Removes old iterations of backups according to a number specified in the config
class cleaning:
    def __init__(self, file:str, how_many: int):
        files = self.__finding_backup_locations(file)
        self.__sorting_into_types(files, file)
        self.__sorting_dates()
        self.__deleting_older_than_freq(file, how_many, files)

    def __finding_backup_locations(self, file: str) -> list:
        full_path = file.split("/")
        backup_location_list = full_path[:-1]
        self.__backup_location = "/".join(backup_location_list).strip()
        files = os.listdir(self.__backup_location)
        return files
        
    # Splits the directory into the files
    def __sorting_into_types(self, files: list, file: str):
        self.__collection: dict[str, list] = {}
        for i in files:
            if i.split(".")[0]+"."+i.split(".")[1] == file.split("/")[len(file.split("/"))-1]:
                date = i.split(".")[len(i.split("."))-1]
                date_in_format = datetime.datetime.strptime(date, "%d-%m-%Y")
                if (i.split(".")[0]+i.split(".")[1]) in self.__collection:
                    self.__collection[(i.split(".")[0]+i.split(".")[1])].append(date_in_format)
                else:
                    self.__collection[(i.split(".")[0]+i.split(".")[1])] = [date_in_format]

    def __sorting_dates(self):
        for file in self.__collection:
            self.__collection[file].sort(reverse=True)
    
    # With the sorted list of dates we just remove all that fall outside of the frequency asked for
    def __deleting_older_than_freq(self, file: str, how_many: int, files: list):
        deleted = self.__collection.get(file.split("/")[len(file.split("/"))-1].replace(".",""))[how_many:]
        for i in deleted:
            date = i.strftime("%d-%m-%Y")
            for j in files:
                if j == str(file.split("/")[len(file.split("/"))-1]+"."+date):
                    os.remove(self.__backup_location+"/"+j)

#  Manages the crontab
class cronning:
    def __init__(self, config: parsing):
        self.__config = config.GetReadFile()
        self.__cron = CronTab(user=True)

    # Removes all the cronjobs that the program has added to the crontab
    # It does this by the use of a comment, Added by backup_manager!, so it doesn't remove cronjobs it hasn't added
    def clear_crontab(self):
        for job in self.__cron.find_comment("Added by backup_manager!"):
            self.__cron.remove(job)

    # Writes to the crontab
    def write_to_crontab(self):
        for section in self.__config:
            for backup_i in range(0, len(self.__config.get(section))):
                job = self.__cron.new(command="/bin/python3 {THIS_FILE} execute {ARG1} {ARG2}".format(THIS_FILE=os.path.abspath(__file__), ARG1 = section, ARG2 = backup_i), comment="Added by backup_manager!")
                if "cron:" in self.__config.get(section)[backup_i][3]: # We can use this loose check due to syntax validation earlier
                    frequency = re.sub(r"cron:\s", "", self.__config.get(section)[backup_i][3])
                    job.setall(frequency)
                else:
                    if "MONTH" in self.__config.get(section)[backup_i][3]: # We can use this loose check due to syntax validation earlier
                        job.setall("0 0 1 */{MONTH} *".format(MONTH=self.__config.get(section)[backup_i][3][0])) # Month steps - 1'st of every month
                    else:
                        job.setall("0 0 */{DAY} * *".format(DAY=self.__config.get(section)[backup_i][3])) # Day steps - Midnight at the start of the day
        self.__cron.write_to_user()

class log_manager:
    def __init__(self):
        logging.basicConfig(filename=LOG_LOCATION, format="%(asctime)s:%(funcName)s - %(levelname)s - %(message)s")
    
    def handling_subprocess_results(self, result):
        if result.returncode != 0:
            logging.exception("\n command: {COMMAND} \n output (may be None): {OUT} \n error (may be None): {ERROR} \n".format(COMMAND=" ".join(result.args), OUT=result.stdout, ERROR=result.stderr))
            raise Exception("Check log for detailed error info.")
    
# The commands/processes that actually get run
class commands:
    def __init__(self, config: parsing):
        self.__config = config.GetReadFile()
    
    def __get_date(self) -> datetime:
        return datetime.datetime.now()

    # Starts the execution progress
    def execute(self, section: str, backup_id: int):
        backup = self.__find_backup_info(section, backup_id)
        host, user = self.__pulling_host_and_user(section)
        self.__commands_for_local(backup, host, user)
    
    def __pulling_host_and_user(self, section: str) -> tuple[str, str]:
        host = section.split("@")[1]
        user = section.split("@")[0]
        return (host, user)

    # Finds the specific backup being referred to in the arguments
    def __find_backup_info(self, section: str, backup_id: int) -> list:
        section = self.__config.get(section)
        return section[backup_id]
    
    def __pulling_filename_from_location(self, backup: list) -> str:
        location: str = backup[2]
        split_path: list[str] = location.split("/")
        return split_path[len(split_path)-1]
    
    # Specifies which commands can be run, also where new commands can be added to incoorporate different backups
    def __commands_for_vm(self, backup: list) -> str:
        match backup[0]:
            case "db":
                return "sqlite3 {FROM} \".backup /tmp/{DATE}.{SAVE_AS}\""
            case "tar":
                return "tar -czf /tmp/{DATE}.{SAVE_AS} {FROM}"
            case "dir":
                return "tar -cf /tmp/{DATE}.{SAVE_AS} {FROM}"
            case "file":
                return "cp {FROM} /tmp/{DATE}.{SAVE_AS}"
    
    # Executes the commands
    def __commands_for_local(self, backup: list, host: str, user: str) -> str:
        logger = log_manager()
        date = self.__get_date()
        vm_cmd = self.__commands_for_vm(backup)
        save_as = self.__pulling_filename_from_location(backup)
        logger.handling_subprocess_results(subprocess.run(["ssh", "{USER}@{HOST}".format(USER = user, HOST = host), "test -e {FROM}".format(FROM=backup[1])]))
        logger.handling_subprocess_results(subprocess.run(["ssh", "{USER}@{HOST}".format(USER = user, HOST = host), "{VMCMD}".format(VMCMD=vm_cmd.format(FROM=backup[1], SAVE_AS=save_as, DATE=date.strftime("%d-%m-%Y")))]))
        logger.handling_subprocess_results(subprocess.run(["scp", "{USER}@{HOST}:/tmp/{DATE}.{SAVE_AS}".format(USER = user, HOST = host, SAVE_AS=save_as, DATE=date.strftime("%d-%m-%Y")), "{TO}.{DATE}".format(TO=backup[2], DATE=date.strftime("%d-%m-%Y"))]))
        logger.handling_subprocess_results(subprocess.run(["ssh", "{USER}@{HOST}".format(USER = user, HOST = host), "rm", "/tmp/{DATE}.{SAVE_AS}".format(SAVE_AS=save_as, DATE=date.strftime("%d-%m-%Y"))]))
        cleaning(backup[2], backup[4]) # Cleaning files that are old now that the new backups are there
       
# Deals with the arguments and different functions that need to be called 
class command_functions:
    def crontab_func(args):
        parsed = parsing(CONFIG_LOCATION)
        parsed.GetReadFile()
        cron = cronning(parsed)
        cron.clear_crontab()
        cron.write_to_crontab()

    def execute_func(args):
        # This is a command operation
        parsed = parsing(CONFIG_LOCATION)
        command = commands(parsed)
        command.execute(args.section, int(args.id))

# Sets up the argument parsing and prints out explanations if there are wrong arguments
def main():
    if CONFIG_LOCATION == "": # The default value
        raise ValueError("Please provide the location of your config.yml file")
    if LOG_LOCATION == "":
        raise ValueError("Please specify the location of the log file")
    
    global_parser = argparse.ArgumentParser(prog="backup-util")
    subparsers = global_parser.add_subparsers(required=True)

    crontab = subparsers.add_parser("crontab", help="Update the crontab")
    crontab.set_defaults(func=command_functions.crontab_func)

    execute = subparsers.add_parser("execute", help="Execute a backup defined in the config.yml")
    execute.add_argument("section")
    execute.add_argument("id")
    execute.set_defaults(func=command_functions.execute_func)

    args = global_parser.parse_args()
    args.func(args)

if __name__ == "__main__":
    main()