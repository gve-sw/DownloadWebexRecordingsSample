"""
Copyright (c) 2020 Cisco and/or its affiliates.

This software is licensed to you under the terms of the Cisco Sample
Code License, Version 1.1 (the "License"). You may obtain a copy of the
License at

               https://developer.cisco.com/docs/licenses

All use of the material herein must be in accordance with the terms of
the License. All rights not expressly granted by the License are
reserved. Unless required by applicable law or agreed to separately in
writing, software distributed under the License is distributed on an "AS
IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express
or implied.
"""
import sys
import os
import sqlite3
import requests
from lxml import etree

db = sqlite3.connect('recordings.sqlite')
cursor = db.cursor()

from config import siteID ,userID ,userPW, webServiceP, output_path

# Webex NBR API URL
vaNBRstor = webServiceP+'/NBRStorageService'
vaNBRsvc = webServiceP+'/nbrXMLService'

etLstRecording = etree.parse('wbx.LstRecording.xml').getroot()
etNBRRecordIdList = etree.parse('wbx.getNBRRecordIdList.xml').getroot()
etStorageAccessTicket = etree.parse('wbx.getStorageAccessTicket.xml').getroot()
etDlNbrStorageFile = etree.parse('wbx.downloadNBRStorageFile.xml').getroot()

#structures for listing conf ids and extractin what is needed for deletion
etgetNBRConfIdList=etree.parse('wbx.getNBRConfIdList.xml').getroot()
etGetNBRStorageFile=etree.parse('wbx.GetNBRStorageFile.xml').getroot()
etdeleteNBRStorageFile=etree.parse('wbx.deleteNBRStorageFile.xml').getroot()
etMeetingTicket = etree.parse('wbx.getMeetingTicket.xml').getroot()



# initializing ConfIDList and recordingConfIDs to empty
confIDList=[]
recordingConfIDs={}
toDeleteRecordingsPaths={}
missingRecordingFilesPaths={}

stXMLheaders = {'Content-Type': 'text/xml'}
stSOAPheaders = {'Content-Type': 'text/xml', 'SOAPAction': ""}

parser = etree.XMLParser(ns_clean=True, recover=True, encoding='utf-8')

if __name__ == "__main__":

    # Get Meeting session Ticket
    etMeetingTicket[1][0][0].text = siteID
    etMeetingTicket[1][0][1].text = userID
    etMeetingTicket[1][0][2].text = userPW
    etMeetingTicket[1][0][3].text = 'MC'
    rMeetingTicket = requests.post(vaNBRsvc, data=etree.tostring(etMeetingTicket), headers=stSOAPheaders)
    rSATxml = etree.fromstring(rMeetingTicket.text.encode('utf-8'), parser=parser)
    sessionSAT = rSATxml[0][0][0].text

    # call getNBRConfIdList to get the list of conferences that have recordings, store in confIDList
    etgetNBRConfIdList[0][0][0].text = siteID
    etgetNBRConfIdList[0][0][1].text = sessionSAT

    rgetNBRConfIdList = requests.post(vaNBRsvc, data=etree.tostring(etgetNBRConfIdList), headers=stSOAPheaders)
    #print("rgetNBRConfIdList= ", rgetNBRConfIdList)
    docgetNBRConfIdList = etree.fromstring(rgetNBRConfIdList.text.encode('utf-8'), parser=parser)
    #print("docgetNBRConfIdList= ", docgetNBRConfIdList)

    for tag in docgetNBRConfIdList.iter():
        if not len(tag) and tag.text is not None:
            confIDList.append(tag.text)


    print("ConfID List = ",confIDList)


    # - for each conference ID, call GetNBRStorageFile and request all recording IDs. Create a Dict in memory indexed by
    #   recording ID with the ConfID that corresponds to it

    # Get Storage Access Ticket
    etStorageAccessTicket[1][0][0].text = siteID
    etStorageAccessTicket[1][0][1].text = userID
    etStorageAccessTicket[1][0][2].text = userPW
    rStorageAccessTicket = requests.post(vaNBRstor, data=etree.tostring(etStorageAccessTicket), headers=stSOAPheaders)
    rSSATxml = etree.fromstring(rStorageAccessTicket.text.encode('utf-8'), parser=parser)
    sessionSSAT = rSSATxml[0][0][0].text

    for confID in confIDList:
        #print("Checking recording IDs for conference ID = ",confID)


        # Build XML for request
        etGetNBRStorageFile[0][0][0].text = siteID
        etGetNBRStorageFile[0][0][1].text = confID
        etGetNBRStorageFile[0][0][2].text = sessionSSAT
        etGetNBRStorageFile[0][0][3].text = ''
        etGetNBRStorageFile[0][0][4].text = ''
        etGetNBRStorageFile[0][0][5].text = ''

        # Send API POST request
        rGetNBRStorageFile = requests.post(vaNBRstor, data=etree.tostring(etGetNBRStorageFile), headers=stSOAPheaders, stream=True)
        #print("rGetNBRStorageFile= ", rGetNBRStorageFile)
        docGetNBRStorageFile = etree.fromstring(rGetNBRStorageFile.text.encode('utf-8'), parser=parser)
        #print("docGetNBRStorageFile= ", docGetNBRStorageFile)

        for tag in docGetNBRStorageFile.iter():
            if not len(tag) and tag.text is not None:
                #print(tag.text)
                recordingID=tag.text
                # Here we need to find all text values within RecordId tags
                # and create Dict entries as such recordingConfIDs[RecordId]=confID
                recordingConfIDs[recordingID] = confID

    print("recordingConfIDs = ",recordingConfIDs)

    cursor.execute("SELECT name, meetingname, status FROM recordings WHERE status = ?", ('COMPLETED',))
    while True:
        record = cursor.fetchone()
        #print(record)
        try:
            #keep track of recording IDs of those that are COMPLETED and their paths are valid
            #to delete them all afterwards. If a file is missing, remove the COMPLETED status so it is
            #downloaded on the next run of the download script
            theRecordID=record[0]
            theRecordPath=record[1]

            if os.path.isfile(theRecordPath):
                #add to our dict to delete
                toDeleteRecordingsPaths[theRecordID]=theRecordPath
            else:
                #add to our dict to mark as missing file
                missingRecordingFilesPaths[theRecordID]=theRecordPath

        except TypeError:
            print("No records found for deletion")
            break

    print("About to mark the following recordings as missing for re-download:")
    for theRecID, theRecPath in missingRecordingFilesPaths.items():
        print(f"ID: {theRecID} Path: {theRecPath}")
    print('')
    print("and about to delete the following recordings:")
    for theRecID, theRecPath in toDeleteRecordingsPaths.items():
        print(f"ID: {theRecID} Path: {theRecPath}")

    if len(sys.argv[1:])>0:
        if sys.argv[1:][0]=='-i':
            if not input("Procced? (y/n): ").lower().strip()[:1] == "y": sys.exit(1)

    for theRecID, theRecPath in missingRecordingFilesPaths.items():
        # first mark records with missing files by setting status as NULL so it is downloaded again
        print(f"Recording file {theRecPath} for key {theRecID} not found!! Marking it as NULL in database so it is downloaded on the next run of the download script.")
        cursor.execute('''UPDATE recordings SET status = ? WHERE name = ? ''',(None, theRecID))
        db.commit()

    # Call deleteNBRStorageFile for all recording IDs marked for deletion in toDeleteRecordingsPaths
    # and corresponding ConfID
    for theRecID, theRecPath in toDeleteRecordingsPaths.items():
        if theRecID in recordingConfIDs:
            print(f"About to delete recording ID: {theRecID} with conf ID: {recordingConfIDs[theRecID]}")

            # Build XML for request
            etdeleteNBRStorageFile[0][0][0].text = siteID
            etdeleteNBRStorageFile[0][0][1].text = recordingConfIDs[theRecID]
            etdeleteNBRStorageFile[0][0][2].text = theRecID
            etdeleteNBRStorageFile[0][0][3].text = sessionSSAT


            # Send API POST request
            rdeleteNBRStorageFile = requests.post(vaNBRstor, data=etree.tostring(etdeleteNBRStorageFile), headers=stSOAPheaders,
                                               stream=True)
            print("rdeleteNBRStorageFile= ", rdeleteNBRStorageFile)
            docdeleteNBRStorageFile = etree.fromstring(rdeleteNBRStorageFile.text.encode('utf-8'), parser=parser)
            print("docdeleteNBRStorageFile= ", docdeleteNBRStorageFile)
            print(f"Recording with ID {theRecID} has been deleted and marked as SCRIPTDELETED in database. Recording file is still at {theRecPath} ")
            # Update recording status
            cursor.execute('''UPDATE recordings SET status = ? WHERE name = ? ''',
            ('SCRIPTDELETED', theRecID))
            db.commit()
        else:
            print(f"Recording with key {theRecID} not found in cloud!! Marking it as MANUALDELETED in database")
            cursor.execute('''UPDATE recordings SET status = ? WHERE name = ? ''',
            ('MANUALDELETED', theRecID))
            db.commit()


db.close()