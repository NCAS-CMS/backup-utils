#!/bin/bash
export DATE=$(date +'%y-%m-%d-%H-%M')
export USERINVM='***YOUR USER IN THE VIRTUAL MACHINE***'
export BACKUPLOCATION='***WHERE YOU ARE STORING THE BACKUPS***'
export BACKUPMANAGERPATH='***THE PATH TO THE BACKUP MANAGER SCRIPT***'

ssh ${USERINVM}@s2p 'tar -cf /home/'${USERINVM}'/full_backup.'${DATE}'.tar /home/s2p/staff2proj; sha256sum /home/'${USERINVM}'/full_backup.'${DATE}'.tar > /home/'${USERINVM}'/full_backup.tar.CHECKSUM'
scp ${USERINVM}@s2p:"/home/${USERINVM}/full_backup.${DATE}.tar" ${BACKUPLOCATION}/full_backup.${DATE}.tar
scp ${USERINVM}@s2p:/home/max/full_backup.tar.CHECKSUM ${BACKUPLOCATION}/full_backup.${DATE}.tar.CHECKSUM
ssh ${USERINVM}@s2p 'rm /home/'${USERINVM}'/full_backup.'${DATE}'.tar'
ssh ${USERINVM}@s2p 'rm /home/'${USERINVM}'/full_backup.tar.CHECKSUM'

export CHECKSUM=$(grep -Eo '^\S+' ${BACKUPLOCATION}/full_backup.${DATE}.tar.CHECKSUM)

echo "${CHECKSUM} ${BACKUPLOCATION}/full_backup.${DATE}.tar" | sha256sum -c

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