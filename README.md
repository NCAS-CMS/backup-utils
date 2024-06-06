# Backup manager
Backup manager is a simplistic backup solution that reads a configuration file (written in yaml) and performs the backups specified periodically with the use of crontab.

## How does it work ❓
* Put simply, there are two modes, crontab mode and execute mode
  * crontab modes updates the crontab with references to the indexes in the config.yml
  * execute mode performs the operations specified in the config.yml (the crontab calls execute mode!)
* Here is a sequence diagram explaining how the functions/classes interract:
![use-case-diagram](http://www.plantuml.com/plantuml/proxy?cache=no&src=https://raw.githubusercontent.com/NCAS-CMS/backup-utils/dev/diagrams/sequence-diagram.iuml)

## Running it 🏃
* Get the `backup_manager.py` script and the `config.yml` files
  * They should preferably not be moved around much as the crontab needs to be regenerated `backup_manager.py` changes location
  * One way to do this is through a quick git clone command:
```bash
git clone https://github.com/NCAS-CMS/backup-utils.git && cd backup-utils
```
* Edit the config.yml file to your liking
  * Note that the section groups specify the host and the username used
  * Also note that every time the config is updated, the crontab needs to be regenerated
* Fill in the constant at the start of the program `CONFIG_LOCATION` with the location of the config
  * This is relative to the location of `backup_manager.py` however it is always safest to use an absolute path
* Run the program in crontab mode:
```bash
python3 backup_manager.py crontab
# This will update your crontab with all the backups specified in the config file
```
* Here is a use-case diagram explaining how a sysadmin would set this up:
![use-case-diagram](http://www.plantuml.com/plantuml/proxy?cache=no&src=https://raw.githubusercontent.com/NCAS-CMS/backup-utils/dev/diagrams/use-case-diagram.iuml)

## The config ⚙️
* Ah yes the bane of every program - it's config, hopefully this section can help explain it!
* The start of every section - in the provided config as `user@host` - is where you put the ssh address and user you will ssh in as
  * This will be used for every backup in the section - so if you need to use different users, make a new section!
  * Currently only backups that require ssh'ing into a different machine are supported but we aim to add local backups in the future as well
*  Now onto the backups:
  * The first section is used to show which backup option you are using:
    * db - uses sqlite3's backup command to backup a database
    * tar - compresses a directory into a tar file (using gzip)
    * dir - puts a directory into a tar file but doesn't compress it, e.g. for large files
    * file - only backs up a single file
  * The second section shows where the file/dir is on the foreign machine
    * Note a full path is required (starting with `/home/` usually)
  * The third section shows where the file/dir will be stored locally
    * A full path is also required here
    * Make sure the file name is included, e.g. ending with `/backup.tar`, or the programme may misbehave
  * The fourth section displays the frequency of the backup
    * This is so the crontab can be configured correctly
    * Note the syntax used in the example for specifying months
    * This is in leaps, e.g. `"1"` means every day
    * To just provide your own cron time scheme simple prefix it with cron:
      * e.g. `"cron: * * * * *` 
  * The fifth and final section shows how many iterations you would like to keep
    * For example you may want to take a full backup every month only keeping the most recent version
      * Hence you would use `1` in this section and `1MONTH` in the fourth section