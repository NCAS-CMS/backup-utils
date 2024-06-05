# Backup manager
Backup manager is a simplistic backup solution that reads a configuration file (written in yaml) and performs the backups specified periodically with the use of crontab.

## How does it work ❓
* Put simply, there are two modes, crontab mode and execute mode
  * crontab modes updates the crontab with references to the indexes in the config.yml
  * execute mode performs the operations specified in the config.yml (the crontab calls execute mode!)
* Here is a sequence diagram explaining how the functions/classes interract:
![use-case-diagram](http://www.plantuml.com/plantuml/proxy?cache=no&src=https://raw.githubusercontent.com/NCAS-CMS/backup-utils/dev/diagrams/sequence-diagram.iuml?token=GHSAT0AAAAAACTFT7ARH7X3JRCE5YKE3JHEZTAMOUQ)

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
* Here is a use-case diagram explaining how a sysadmin would set this up:
![use-case-diagram](http://www.plantuml.com/plantuml/proxy?cache=no&src=https://raw.githubusercontent.com/NCAS-CMS/backup-utils/dev/diagrams/use-case-diagram.iuml?token=GHSAT0AAAAAACTFT7AQXQDCKW76757FRGMGZTAMNVA)

<!-- Note the UML diagrams have to have their tokens updated due to this being a private git repository as of now - it should not be an issue if we go public -->
