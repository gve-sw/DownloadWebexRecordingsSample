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
import datetime
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
etgetMeetingXml=etree.parse('wbx.getMeetingXml.xml').getroot()



# initializing ConfIDList and recordingConfIDs to empty
confIDList=[]
recordingConfIDs={}

#cloudRecordingsLocalDBBool is used to keep track of all cloud recording IDs, but the values in this dict
#indicate if they are in the local DB
cloudRecordingsLocalDBBool={}

#recordingsConfDetails is indexed by recordingID and each value is a Dict with all several parameters in the XML
recordingsConfDetails={}

stXMLheaders = {'Content-Type': 'text/xml'}
stSOAPheaders = {'Content-Type': 'text/xml', 'SOAPAction': ""}

parser = etree.XMLParser(ns_clean=True, recover=True, encoding='utf-8')

def initConfDetails():
    aConfIDDetails={}
    for theKey in ['LocalDBStatus','DownloadedPath','RecFileStatus','ModeratorName', 'MeetingName', 'StartTimeUTC',
                   'EndTimeUTC', 'ModeratorEmail','ModeratorLoginName','ModeratorJoinUTC','ModeratorLeaveUTC']:
        aConfIDDetails[theKey]=''
    return aConfIDDetails


if __name__ == "__main__":

    #Get recording IDs from cloud
    etLstRecording[0][0][0].text = siteID
    etLstRecording[0][0][1].text = userID
    etLstRecording[0][0][2].text = userPW
    rLstRecording = requests.post(vaNBRsvc, data=etree.tostring(etLstRecording), headers=stSOAPheaders)
    #print("rLstRecording= ", rLstRecording)
    docLstRecording = etree.fromstring(rLstRecording.text.encode('utf-8'), parser=parser)
    #print("docLstRecording= ", docLstRecording)

    #fill out cloudRecordingsLocalDBBool as if none where in the DB for now and change if found there
    for tag in docLstRecording.iter():
        if not len(tag) and tag.text is not None:
            cloudRecordingsLocalDBBool[tag.text]=False




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

    #print("ConfID List = ",confIDList)


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

    #print("recordingConfIDs = ",recordingConfIDs)

    #Now that we have all the conference IDs for recordings found in the cloud
    #extract the MeetingXML for each to report

    # call getMeetingXML on each conference for which there are recordings, store the
    # values in recordingsConfDetails[recordingID] (one Dict per recording)
    for theRecID, theValue in cloudRecordingsLocalDBBool.items():
        #initialize empty dict with initial values not handled in this loop to put conference details
        aConfIDDetails=initConfDetails()

        #obtain the confID we need to make the call
        confID=recordingConfIDs[theRecID]
        #print(f"Calling getMeetingXml for Conf ID {confID} due to recording ID {theRecID}")
        #fill out the XML to make the getMeetingXML call
        etgetMeetingXml[0][0][0].text = siteID
        etgetMeetingXml[0][0][1].text = confID
        etgetMeetingXml[0][0][2].text = sessionSAT
        #make the call
        rgetMeetingXml = requests.post(vaNBRsvc, data=etree.tostring(etgetMeetingXml), headers=stSOAPheaders)
        # print("rgetMeetingXml= ", rgetMeetingXml)
        docgetMeetingXml = etree.fromstring(rgetMeetingXml.text.encode('utf-8'), parser=parser)
        # print("docgetMeetingXml= ", docgetMeetingXml)

        #initialize temp variables to hold the Join and Leave UTC of moderator as well as their LoginName
        theMLeaveUTC=''
        theMJoinUTC=''
        theMLoginName=''
        for tag in docgetMeetingXml.iter():
            if not len(tag) and tag.text is not None:
                #print(f"Tag: {tag.tag} Text: {tag.text}")
                #extract the fixed top level keys we want to keep
                if tag.tag in ['ModeratorName','MeetingName','StartTimeUTC','EndTimeUTC','ModeratorEmail']:
                    aConfIDDetails[tag.tag]=tag.text
                #for the moderator Join and Leave time we need to check all participant info that comes across
                #comparing with ModeratorEmail, if exists
                if tag.tag=='LoginName':
                    theMLoginName=tag.text
                if tag.tag=='JoinDateTimeUTC':
                    theMJoinUTC=tag.text
                if tag.tag=='LeaveDateTimeUTC':
                    theMLeaveUTC=tag.text
                #if the ModeratorMail matches the CorporateEmailID of the entry being evaluated
                #consider it the moderator and store away the most recent LoginName, JoinUTC and LeaveUTC
                #since they should correspond to it based on the order in which the XML is parsed
                if tag.tag=='CorporateEmailID':
                    if 'ModeratorEmail' in aConfIDDetails:
                        if tag.text==aConfIDDetails['ModeratorEmail']:
                            aConfIDDetails['ModeratorLoginName']=theMLoginName
                            aConfIDDetails['ModeratorJoinUTC']=theMJoinUTC
                            aConfIDDetails['ModeratorLeaveUTC']=theMLeaveUTC
        #print("Details for this conference:")
        #print(aConfIDDetails)
        #assign conf details to top level dictionary with all recordings
        recordingsConfDetails[theRecID]=aConfIDDetails

    #print('')
    #print("All recordings information: ")
    #print(recordingsConfDetails)
    #print('')

    # Check for recording IDs stored in the Database so we can report
    # on which have been downloaded and which have not.
    cursor.execute("SELECT name, meetingname, status FROM recordings")
    while True:
        record = cursor.fetchone()
        #print(record)
        try:
            #keep track of recording IDs in the DB and their paths if already downloaded
            theRecordID=record[0]
            theRecordPath=record[1]
            theRecordStatus=record[2]

            #first check to see if the DB record is no longer in the cloud, if so, initialize the proper
            #entry in recordingsConfDetails.
            if theRecordID not in recordingsConfDetails:
                aConfIDDetails = initConfDetails()
                recordingsConfDetails[theRecordID]=aConfIDDetails

            if theRecordStatus == None:
                recordingsConfDetails[theRecordID]['LocalDBStatus'] = 'SEEDED'
            else:
                recordingsConfDetails[theRecordID]['LocalDBStatus'] = theRecordStatus
            recordingsConfDetails[theRecordID]['DownloadedPath'] = theRecordPath

            #mark recordings that where listed in the cloud and also show up in the DB as such
            if theRecordID in cloudRecordingsLocalDBBool:
                cloudRecordingsLocalDBBool[theRecordID]=True
            if theRecordPath != None:
                if os.path.isfile(theRecordPath):
                    #add to our dict to delete
                    recordingsConfDetails[theRecordID]['RecFileStatus'] = 'PRESENT'
                    #downloadedRecordingsPaths[theRecordID]=theRecordPath
                else:
                    #add to our dict to mark as missing file
                    #missingRecordingFilesPaths[theRecordID]=theRecordPath
                    recordingsConfDetails[theRecordID]['RecFileStatus'] = 'MISSING'

        except TypeError:
            #print("No records found in database.")
            break

    #Print out the consolidated list of recording information gathered
    doOnce=True
    for theRecKey, theRecValue in recordingsConfDetails.items():
        if doOnce:
            doOnce=False
            print("RecordingID",end="\t")
            for theKey, theValue in theRecValue.items():
                print(theKey,end="\t")
            print('')
        print(theRecKey,end="\t")
        for theKey, theValue in theRecValue.items():
            if 'UTC' in theKey and theValue!='':
                print(datetime.datetime.fromtimestamp(int(theValue)/1000).strftime('%Y-%m-%d %H:%M'),end="\t")
            else:
                print(theValue,end="\t")
        print('')
db.close()