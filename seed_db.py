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

stXMLheaders = {'Content-Type': 'text/xml'}
stSOAPheaders = {'Content-Type': 'text/xml', 'SOAPAction': ""}

parser = etree.XMLParser(ns_clean=True, recover=True, encoding='utf-8')

if __name__ == "__main__":

    if not os.path.exists(output_path):
        os.makedirs(output_path)


    #Get recording info and put into text files in directories
    etLstRecording[0][0][0].text = siteID
    etLstRecording[0][0][1].text = userID
    etLstRecording[0][0][2].text = userPW
    rLstRecording = requests.post(vaNBRsvc, data=etree.tostring(etLstRecording), headers=stSOAPheaders)
    #print("rLstRecording= ", rLstRecording)
    docLstRecording = etree.fromstring(rLstRecording.text.encode('utf-8'), parser=parser)
    #print("docLstRecording= ", docLstRecording)

    for tag in docLstRecording.iter():
        if not len(tag) and tag.text is not None:
            try:
                cursor.execute('''INSERT INTO recordings(name) VALUES(?)''', (tag.text,))
                db.commit()
            except sqlite3.IntegrityError as e:
                print("Skipping duplicate entry: " + tag.text)
            
db.close()