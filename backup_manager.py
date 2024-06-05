import os
import subprocess
import yaml
import argparse
import datetime
from crontab import CronTab

class parsing:
    def __init__(self, config_location: str):
        self.__config_location = config_location
        self.__reading_file()
    
    def __reading_file(self):
        with open(self.__config_location, 'r') as file:
            self.__config = yaml.safe_load(file)
    
    def __syntax_check(self):
        pass # TODO
    
    def GetReadFile(self) -> dict:
        return self.__config

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
        
    def __sorting_into_types(self, files: list, file: str):
        self.__collection: dict[str, list] = {}
        for i in files:
            date = i.split(".")[len(i.split("."))-1]
            date_in_format = datetime.datetime.strptime(date, "%d%m%Y")
            if i.split(".")[0]+"."+i.split(".")[1] == file.split("/")[len(file.split("/"))-1]:
                if (i.split(".")[0]+i.split(".")[1]) in self.__collection:
                    self.__collection[(i.split(".")[0]+i.split(".")[1])].append(date_in_format)
                else:
                    self.__collection[(i.split(".")[0]+i.split(".")[1])] = [date_in_format]

    def __sorting_dates(self):
        for file in self.__collection:
            self.__collection[file].sort(reverse=True)
    
    def __deleting_older_than_freq(self, file: str, how_many: int, files: list):
        deleted = self.__collection.get(file.split("/")[len(file.split("/"))-1].replace(".",""))[how_many:]
        for i in deleted:
            date = i.strftime("%d%m%Y")
            for j in files:
                if j == str(file.split("/")[len(file.split("/"))-1]+"."+date):
                    os.remove(self.__backup_location+"/"+j)


class cronning:
    def __init__(self, config: parsing):
        self.__config = config.GetReadFile()
        self.__cron = CronTab(user=True)

    def clear_crontab(self):
        for job in self.__cron.find_comment("Added by backup_manager!"):
            self.__cron.remove(job)

    def write_to_crontab(self):
        for section in self.__config:
            for backup_i in range(0, len(self.__config.get(section))):
                job = self.__cron.new(command="/bin/python3 {THIS_FILE} execute {ARG1} {ARG2}".format(THIS_FILE=os.path.abspath(__file__), ARG1 = section, ARG2 = backup_i), comment="Added by backup_manager!")
                if "MONTH" in self.__config.get(section)[backup_i][5]:
                    job.setall("0 0 1 */{MONTH} *".format(MONTH=self.__config.get(section)[backup_i][5][0]))
                else:
                    job.setall("0 0 */{DAY} * *".format(DAY=self.__config.get(section)[backup_i][5]))
        self.__cron.write_to_user()

class commands:
    def __init__(self, config: parsing):
        self.__config = config.GetReadFile()
    
    def __get_date(self) -> datetime:
        return datetime.datetime.now()

    def execute(self, section: str, backup_id: int):
        backup = self.__find_backup_info(section, backup_id)
        self.__commands_for_local(backup)

    def __find_backup_info(self, section: str, backup_id: int) -> list:
        section = self.__config.get(section)
        return section[backup_id]
    
    def __pulling_filename_from_location(self, backup: list) -> str:
        location: str = backup[4]
        split_path: list[str] = location.split("/")
        return split_path[len(split_path)-1]
    
    def __commands_for_vm(self, backup: list) -> str:
        match backup[0]:
            case "db":
                return "sqlite3 {FROM} \".backup /tmp/{DATE}.{SAVE_AS}\""
            case "tar":
                return "tar -cf /tmp/{DATE}.{SAVE_AS} {FROM}"
            case "dir":
                return "tar -cf /tmp/{DATE}.{SAVE_AS} {FROM}"
            case "file":
                return "cp {FROM} /tmp/{DATE}.{SAVE_AS}"
    
    def __commands_for_local(self, backup: list) -> str:
        date = self.__get_date()
        vm_cmd = self.__commands_for_vm(backup)
        save_as = self.__pulling_filename_from_location(backup)
        subprocess.run(["ssh", "{USER}@{HOST}".format(USER = backup[2], HOST= backup[1]), "{VMCMD}".format(VMCMD=vm_cmd.format(FROM=backup[3], SAVE_AS=save_as, DATE=date.strftime("%d%m%Y")))])
        subprocess.run(["scp", "{USER}@{HOST}:/tmp/{DATE}.{SAVE_AS}".format(USER = backup[2], HOST= backup[1], SAVE_AS=save_as, DATE=date.strftime("%d%m%Y")), "{TO}.{DATE}".format(TO=backup[4], DATE=date.strftime("%d%m%Y"))])
        subprocess.run(["ssh", "{USER}@{HOST}".format(USER = backup[2], HOST= backup[1]), "rm", "/tmp/{DATE}.{SAVE_AS}".format(SAVE_AS=save_as, DATE=date.strftime("%d%m%Y"))])
        cleaning(backup[4], backup[6])
        

class command_functions:
    def crontab_func(args):
        parsed = parsing("./config.yml")
        cron = cronning(parsed)
        cron.clear_crontab()
        cron.write_to_crontab()

    def execute_func(args):
        # This is a command operation
        parsed = parsing("./config.yml")
        command = commands(parsed)
        command.execute(args.section, int(args.id))

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