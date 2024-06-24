import os
import subprocess
import argparse
import datetime
import re
import logging

import yaml
from crontab import CronTab

# CONSTANTS
CONFIG_LOCATION = ""  # PLEASE SET THIS! (The program will error out if you don't ;))
LOG_LOCATION = ""  # PLEASE ALSO SET THIS! (The program will also error out here if not set)


class Parsing:
    """This class manages the parsing of the config file along with syntax checking
    Note: The read config is accessed through the get_read_file() method
    """
    def __init__(self):
        """Sets up the config file for reading and calls the reading function
        
        Args:
            none
        Returns:
            none 
        Raises:
            none

        """
        self.__config_location = CONFIG_LOCATION
        self.__reading_file()

    def __reading_file(self):
        """Opens the file and uses pyyaml to read it"""
        with open(self.__config_location, "r", encoding="utf-8") as file:
            self.__config = yaml.safe_load(file)

    # Checks section in user@host
    def __section_format_check(self):
        """Checks the format of the section headers"""
        for section in self.__config:
            valid = re.findall(r"^\w+@\w+$", section)
            if not valid:
                raise ValueError(f"Section titles need to be of form user@host, yours is {section}")

    def __backup_format_check(self):
        """Uses REGEX to analyse the config file and raises appropriate exceptions

        Raises:
            ValueError: when the regex fails thus the config file isn't valid
        
        """
        for section in self.__config:
            for backup in self.__config.get(section):
                # Length check
                if len(backup) != 5:
                    raise ValueError(f"Backups need to have 5 variables, yours is {backup}")

                # Backup type check
                if backup[0] not in ["tar", "db", "dir", "file"]:
                    raise ValueError(f"The first backup section can only be tar,db,dir or file, yours is {backup[0]}")

                # File paths valid check
                valid = re.findall(r"^\/", backup[1])
                if not valid:
                    raise ValueError(f"The path on the foreign machine must be absolute, e.g starting with /, yours is {backup[1]}")
                valid = re.findall(r"^\/", backup[2])
                if not valid:
                    raise ValueError(f"The path on the local machine must be absolute, e.g starting with /, yours is {backup[2]}")

                # Frequency check
                valid = re.findall(r"^((cron: )|((\d+)(MONTH)?$))", str(backup[3]))
                if not valid:
                    raise ValueError(f"The frequency defined must have a be of the form int or intMONTH, yours is {backup[3]}.")

                # Iterations check
                valid = re.findall(r"^\d+$", str(backup[4]))
                if not valid:
                    raise ValueError(f"The number of iterations must be a positive integer, yours is {backup[4]}")

    def __syntax_check(self):
        """Calls the two syntax checks defined above"""
        self.__section_format_check()
        self.__backup_format_check()

    def get_read_file(self) -> dict:
        """Syntax checks the file and then returns it if it is valid (it hasn't errored)
        
        Returns:
            self.__config: The config file in a dictionary format provided by pyyaml

        """
        self.__syntax_check()
        return self.__config


class Cleaning:
    """This class manages the cleaning of old iterations of backups
    
    Args:
        file: as the cleaning class is initialised after every commit the file that needs to be cleaned is passed in
        how_many: defines how many iterations of each file is to be kept, consistent among files

    Note:
        The init function completes all of the classes functionality, may be an idea to provide a few more pub methods
    """
    def __init__(self, file: str, how_many: int):
        """Calls all of the cleaning functions to remove old iterations"""
        files = self.__finding_backup_locations(file)
        self.__sorting_into_types(files, file)
        self.__sorting_dates()
        self.__deleting_older_than_freq(file, how_many, files)

    def __finding_backup_locations(self, file: str) -> list:
        """Scans all of the directories defined in the config and calls ls and returns it files"""
        full_path = file.split("/")
        backup_location_list = full_path[:-1]
        self.__backup_location = "/".join(backup_location_list).strip()
        files = os.listdir(self.__backup_location)
        return files

    def __sorting_into_types(self, files: list, file: str):
        """"""
        self.__collection: dict[str, list] = {}
        for i in files:
            file_in_dir = i.split(".")[0] + "." + i.split(".")[1]
            file_wanted = file.split("/")[len(file.split("/")) - 1]
            if file_in_dir == file_wanted:
                file_new_format = i.split(".")[0] + i.split(".")[1]
                date = i.split(".")[len(i.split(".")) - 1]
                date_in_format = datetime.datetime.strptime(date, "%d-%m-%Y")
                if file_in_dir in self.__collection: # Already stored
                    self.__collection[file_new_format].append(date_in_format)
                else:
                    self.__collection[file_new_format] = [date_in_format]

    def __sorting_dates(self):
        for file in self.__collection.items():
            file.sort(reverse=True)

    # With the sorted list of dates we just remove all that fall outside of the frequency asked for
    def __deleting_older_than_freq(self, file: str, how_many: int, files: list):
        deleted = self.__collection.get(file.split("/")[len(file.split("/")) - 1].replace(".", ""))[how_many:] # Takes the file name out of the full path
        for i in deleted:
            date = i.strftime("%d-%m-%Y")
            for j in files:
                if j == str(file.split("/")[len(file.split("/")) - 1] + "." + date):
                    os.remove(self.__backup_location + "/" + j)


#  Manages the crontab
class Cronning:
    """Completes all of the crontab management of the program

    Args:
        config: a parsing object from which cronning can pull all the config file from
    Note:
        public methods are massive here due to this being a key danger point in the program hence I would prefer each method is called manually,
        this means they aren't just bundled into init leaving a bit of danger.
        also this is the only point at which the python-crontab module is used

    """
    def __init__(self, config: Parsing):
        self.__config = config.get_read_file()
        self.__cron = CronTab(user=True)

    def clear_crontab(self):
        """Clears the crontab of cron jobs it has added

        Note:
            It does this by the use of a comment appended to each job it adds

        """
        for job in self.__cron.find_comment("Added by backup_manager!"):
            self.__cron.remove(job)

    def write_to_crontab(self):
        """This writes the new jobs to the crontab, using the comment on the cronjobs again just for identification
        
        Note:
            Due to the dangerous nature of this method I will explain it in detail:
                First of all we iterate through all of the jobs through the use of two for loops
                Then we initialise a job with the current file path of this script, the arguments that it needs to be called with and the comment
                Then it detects whether cron syntax is being used, if so it just sets the cron time to the provided time in the config 
                If not it detects if its months or days and uses steps accordingly

        """
        for section in self.__config:
            for backup_i in range(0, len(self.__config.get(section))):
                job = self.__cron.new(
                    command=f"/bin/python3 {os.path.abspath(__file__)} execute {section} {backup_i}",
                    comment="Added by backup_manager!",
                )
                if "cron:" in self.__config.get(section)[backup_i][3]:  # We can use this loose check due to syntax validation earlier
                    frequency = re.sub(
                        r"cron:\s", "", self.__config.get(section)[backup_i][3]
                    )
                    job.setall(frequency)
                else:
                    if "MONTH" in self.__config.get(section)[backup_i][3]:  # We can use this loose check due to syntax validation earlier
                        job.setall(
                            f"0 0 1 */{self.__config.get(section)[backup_i][3][0]} *"
                        )  # Month steps - 1'st of every month
                    else:
                        job.setall(
                            f"0 0 */{self.__config.get(section)[backup_i][3]} * *"
                        )  # Day steps - Midnight at the start of the day
        self.__cron.write_to_user()

class Logmanager:
    """This class manages logging for the program

    Note:
        It is currently only in effect for subprocess failures but may be extended in the future

    """
    def __init__(self):
        """This init function sets up the logging"""
        logging.basicConfig(
            filename=LOG_LOCATION,
            format="%(asctime)s:%(funcName)s - %(levelname)s - %(message)s",
        )

    def handling_subprocess_results(self, result):
        """This public function is the one called for each subprocess
        
        Args:
            result: this is the return variable of the subprocess function, it provides information about the command

        Raises:
            RuntimeError: if there has been a failure (exit code != 0) the program fails
        
        Note:
            the use of old style python string formatting is intentional due to its lazy nature (pylint told me off)

        """
        if result.returncode != 0:
            logging.exception(
                "\n command: %s\n output (may be None): %s \n error (may be None): %s \n", ' '.join(result.args), result.stdout, result.stderr
            )
            raise RuntimeError("Check log for detailed error info.")


class Commands:
    """The commands class manages the commands that get ran to perform backups

    Args:
        config: a parsing object from which cronning can pull all the config file from

    Note:
        while the class in theory manages the execution the execute function manages the bulk of it
    """
    def __init__(self, config: Parsing):
        self.__config = config.get_read_file()

    def __get_date(self) -> datetime:
        return datetime.datetime.now()

    def execute(self, section: str, backup_id: int):
        """This manages the execution process

        Args:
            section: the section in the config where the backup is found
            backup_id: the index within the section where the precise backup is found

        """
        backup = self.__find_backup_info(section, backup_id)
        host, user = self.__pulling_host_and_user(section)
        self.__commands_for_local(backup, host, user)

    def __pulling_host_and_user(self, section: str) -> tuple[str, str]:
        host = section.split("@")[1]
        user = section.split("@")[0]
        return (host, user)

    def __find_backup_info(self, section: str, backup_id: int) -> list:
        section: list = self.__config.get(section)
        return section[backup_id]

    def __pulling_filename_from_location(self, backup: list) -> str:
        location: str = backup[2]
        split_path: list[str] = location.split("/")
        return split_path[len(split_path) - 1]

    def __commands_for_vm(self, backup: list) -> str:
        """Specifies how commands should be run to prepare backups
        
        Note:
            this is where it is easy to extend the program and add new commands, just make sure you update the regex!

        """
        match backup[0]:
            case "db":
                return 'sqlite3 {FROM} ".backup /tmp/{DATE}.{SAVE_AS}"'
            case "tar":
                return "tar -czf /tmp/{DATE}.{SAVE_AS} {FROM}"
            case "dir":
                return "tar -cf /tmp/{DATE}.{SAVE_AS} {FROM}"
            case "file":
                return "cp {FROM} /tmp/{DATE}.{SAVE_AS}"
            case _:
                return ""

    def __commands_for_local(self, backup: list, host: str, user: str):
        """Defines and runs the commands on the local machine

        Args:
            backup: the line from the config of which backup is being performed
            host: the host (maybe ip) of the machine to be ssh'd into
            user: the user you are ssh'ing into the host as
        Returns:
            none
        Raises:
            RuntimeError: if one of the commands fails it the logger calls an exception
        Notes:
            Check is turned off due to my own logging functionality

        """
        logger = Logmanager()
        date = self.__get_date()
        vm_cmd = self.__commands_for_vm(backup)
        save_as = self.__pulling_filename_from_location(backup)
        logger.handling_subprocess_results(
            subprocess.run(
                [
                    "ssh",
                    f"{user}@{host}",
                    f"test -e {backup[1]}",
                    "# To check if the file exists",
                ],
                check=False
            )
        )
        logger.handling_subprocess_results(
            subprocess.run(
                [
                    "ssh",
                    f"{user}@{host}",
                    "{VMCMD}".format(
                        VMCMD=vm_cmd.format(
                            FROM=backup[1],
                            SAVE_AS=save_as,
                            DATE=date.strftime("%d-%m-%Y"),
                        )
                    ),
                    "# To tell the machine to prepare the dir/file",
                ],
                check=False
            )
        )
        logger.handling_subprocess_results(
            subprocess.run(
                [
                    "scp",
                    f"{user}@{host}:/tmp/{date.strftime('%d-%m-%Y')}.{save_as}",
                    f"{backup[2]}.{date.strftime('%d-%m-%Y')}",
                    "# To pull the file from the machine",
                ],
                check=False
            )
        )
        logger.handling_subprocess_results(
            subprocess.run(
                [
                    "ssh",
                    f"{user}@{host}",
                    "rm",
                    f"/tmp/{date.strftime('%d-%m-%Y')}.{save_as}",
                    "# To delete the file placed in tmp from the machine",
                ],
                check=False
            )
        )
        Cleaning(backup[2], backup[4])  # Cleaning files that are old now that the new backups are there


class Commandfunctions:
    """This class was required due to how argument parsing is done

    crontab_func is called if the program is called with the crontab argument and likewise with the execute function

    """
    def crontab_func(self, args):
        """Parses the config, gets the parsed config, passes the config into cronning
        calls dangerous public methods 
        """
        parsed = Parsing()
        parsed.get_read_file()
        cron = Cronning(parsed)
        cron.clear_crontab()
        cron.write_to_crontab()

    def execute_func(self, args):
        """Parses the config, tells command to read the config and then tells it to execute"""
        parsed = Parsing()
        command = Commands(parsed)
        command.execute(args.section, int(args.id))


def main():
    """Sets up the program, e.g. erroring out with empty values and argument parsing"""
    if CONFIG_LOCATION == "":
        raise ValueError("Please provide the location of your config.yml file")
    if LOG_LOCATION == "":
        raise ValueError("Please specify the location of the log file")

    global_parser = argparse.ArgumentParser(prog="backup-util")
    subparsers = global_parser.add_subparsers(required=True)

    crontab = subparsers.add_parser("crontab", help="Update the crontab")
    crontab.set_defaults(func=Commandfunctions.crontab_func)

    execute = subparsers.add_parser(
        "execute", help="Execute a backup defined in the config.yml"
    )
    execute.add_argument("section")
    execute.add_argument("id")
    execute.set_defaults(func=Commandfunctions.execute_func)

    args = global_parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
