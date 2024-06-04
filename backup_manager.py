# Want to remove oldest backup if num of backups is less than 3
import os
BACKUP_LOCATION = "***LOCATION OF YOUR BACKUPS***"

# To sort by dates
def sorter(input: tuple[str,int]) -> int:
    return input[0]

# Read the backup directory
backups: list[str] = os.listdir(BACKUP_LOCATION)

# Create two lists for storing the backup dates
database_backup_dates: list[str, int] = []
full_backup_dates: list[str, int] = []

# Adding the backups to the x_backup_dates lists along with their position in the list for later removal
for i in range(len(backups)):
    date: str = backups[i].split(".")[1]
    full_backup: bool = (backups[i].split(".")[0] == "full_backup")
    date_no_dashes: str = date.replace("-", "")
    if full_backup:
        full_backup_dates.append((date_no_dashes, i))
    else:
        database_backup_dates.append((date_no_dashes, i))

# Sorting the lists with the latest first
full_backup_dates.sort(key=sorter, reverse=True)
database_backup_dates.sort(key=sorter, reverse=True)

# Stripping to first three elements
full_backup_dates = full_backup_dates[:3]
database_backup_dates = database_backup_dates[:3]

# Creating a list of indexes in backups that we want
backups_wanted: list[int] = []
for i in full_backup_dates:
    backups_wanted.append(i[1])
for i in database_backup_dates:
    backups_wanted.append(i[1]) 

# Deleting elements not in the latest 3
for i in range(len(backups)):
    if i not in(backups_wanted):
        os.remove((BACKUP_LOCATION+backups[i]))
