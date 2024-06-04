#!/bin/bash
export DATE=$(date +'%y-%m-%d-%H-%M')
export USERINVM='***YOUR USER IN THE VIRTUAL MACHINE***'
export BACKUPLOCATION='***WHERE YOU ARE STORING THE BACKUPS***'
export BACKUPMANAGERPATH='***THE PATH TO THE BACKUP MANAGER SCRIPT***'

ssh ${USERINVM}@s2p 'sqlite3 /home/s2p/staff2proj/db.sqlite3 ".backup "/home/'${USERINVM}'/database_backup.'${DATE}'.sq3.baq""; sha256sum /home/'${USERINVM}'/database_backup.'${DATE}'.sq3.baq > /home/'${USERINVM}'/database_backup.sq3.baq.CHECKSUM'
scp ${USERINVM}@s2p:"/home/'${USERINVM}'/database_backup.${DATE}.sq3.baq" ${BACKUPLOCATION}/database_backup.${DATE}.sq3.baq
scp ${USERINVM}@s2p:/home/${USERINVM}/database_backup.sq3.baq.CHECKSUM ${BACKUPLOCATION}/database_backup.${DATE}.sq3.CHECKSUM
ssh ${USERINVM}@s2p "rm /home/'${USERINVM}'/database_backup."${DATE}".sq3.baq"
ssh ${USERINVM}@s2p "rm /home/'${USERINVM}'/database_backup.sq3.baq.CHECKSUM"

export CHECKSUM=$(grep -Eo '^\S+' ${BACKUPLOCATION}/database_backup.${DATE}.sq3.CHECKSUM)

echo "${CHECKSUM} ${BACKUPLOCATION}/database_backup.${DATE}.sq3.baq" | sha256sum -c

if [ $? != 0 ]; then
    echo "CHECKSUM FAILED"
    
else
    echo "CHECKSUM OK"
fi

if hash python3 2>/dev/null; then
    python3 ${BACKUPMANAGERPATH}
else 
    echo "Python3 is needed to run the backup manager script - backups will not be cleaned"
fi
