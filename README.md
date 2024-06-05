# Backup manager
Backup manager is a simplistic backup solution that reads a configuration file (written in yaml) and performs the backups specified periodically with the use of crontab.

## How does it work ❓
* Put simply, there are two modes, crontab mode and execute mode
  * crontab modes updates the crontab with references to the indexes in the config.yml
  * execute mode performs the operations specified in the config.yml (the crontab calls execute mode!)

## Running it 🏃
* Get the `backup_manager.py` script and the `config.yml` files in the same directory on your local machine
  * They should preferably not be moved around much as the crontab needs to be regenerated each time they change location
  * One way to do this is through a quick git clone command:
```bash
git clone https://github.com/NCAS-CMS/backup-utils.git && cd backup-utils
```
* Edit the config.yml file to your liking
  * Note that the section groups are only for easy categorisation for the user and have no impact on how the program runs
  * Also note that every time the config is updated, the crontab needs to be regenerated
* Run the program in crontab mode:
```bash
python3 backup_manager.py crontab
# This will update your crontab with all the backups specified in the config file
```
* Done!
