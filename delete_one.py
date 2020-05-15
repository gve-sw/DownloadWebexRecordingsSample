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
import sqlite3
import requests
from lxml import etree

db = sqlite3.connect('recordings.sqlite')
cursor = db.cursor()
delRecordID = "999999999"

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
    print("rgetNBRConfIdList= ", rgetNBRConfIdList)
    docgetNBRConfIdList = etree.fromstring(rgetNBRConfIdList.text.encode('utf-8'), parser=parser)
    print("docgetNBRConfIdList= ", docgetNBRConfIdList)

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
        print("Checking recording IDs for conference ID = ",confID)


        # Build XML for request
        etGetNBRStorageFile[0][0][0].text = siteID
        etGetNBRStorageFile[0][0][1].text = confID
        etGetNBRStorageFile[0][0][2].text = sessionSSAT
        etGetNBRStorageFile[0][0][3].text = ''
        etGetNBRStorageFile[0][0][4].text = ''
        etGetNBRStorageFile[0][0][5].text = ''

        # Send API POST request
        rGetNBRStorageFile = requests.post(vaNBRstor, data=etree.tostring(etGetNBRStorageFile), headers=stSOAPheaders, stream=True)
        print("rGetNBRStorageFile= ", rGetNBRStorageFile)
        docGetNBRStorageFile = etree.fromstring(rGetNBRStorageFile.text.encode('utf-8'), parser=parser)
        print("docGetNBRStorageFile= ", docGetNBRStorageFile)

        for tag in docGetNBRStorageFile.iter():
            if not len(tag) and tag.text is not None:
                print(tag.text)
                recordingID=tag.text
                # Here we need to find all text values within RecordId tags
                # and create Dict entries as such recordingConfIDs[RecordId]=confID
                recordingConfIDs[recordingID] = confID

    print("recordingConfIDs = ",recordingConfIDs)

    # - Call deleteNBRStorageFile using the recordingID and corresponding ConfID
    if delRecordID in recordingConfIDs:
        print(f"About to delete recording ID: {delRecordID} with conf ID: {recordingConfIDs[delRecordID]}")
        if not input("Procced? (y/n): ").lower().strip()[:1] == "y": sys.exit(1)

        # Build XML for request
        etdeleteNBRStorageFile[0][0][0].text = siteID
        etdeleteNBRStorageFile[0][0][1].text = recordingConfIDs[delRecordID]
        etdeleteNBRStorageFile[0][0][2].text = delRecordID
        etdeleteNBRStorageFile[0][0][3].text = sessionSSAT


        # Send API POST request
        rdeleteNBRStorageFile = requests.post(vaNBRstor, data=etree.tostring(etdeleteNBRStorageFile), headers=stSOAPheaders,
                                           stream=True)
        print("rdeleteNBRStorageFile= ", rdeleteNBRStorageFile)
        docdeleteNBRStorageFile = etree.fromstring(rdeleteNBRStorageFile.text.encode('utf-8'), parser=parser)
        print("docdeleteNBRStorageFile= ", docdeleteNBRStorageFile)

        print(f"Recording with ID {delRecordID} has been deleted.")
    else:
        print(f"Recording with key {delRecordID} not found.")


db.close()