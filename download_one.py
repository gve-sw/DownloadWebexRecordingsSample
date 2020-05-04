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


# SQLite connector
db = sqlite3.connect('recordings.sqlite')
cursor = db.cursor()



# Webex API Auth
from config import siteID ,userID ,userPW, webServiceP, output_path
# Webex NBR API URL
vaNBRstor = webServiceP+'/NBRStorageService'
vaNBRsvc = webServiceP+'/nbrXMLService'

# API XML templates
etNBRRecordIdList = etree.parse('wbx.getNBRRecordIdList.xml').getroot()
etStorageAccessTicket = etree.parse('wbx.getStorageAccessTicket.xml').getroot()
etDlNbrStorageFile = etree.parse('wbx.downloadNBRStorageFile.xml').getroot()

# Soap headers
stXMLheaders = {'Content-Type': 'text/xml'}
stSOAPheaders = {'Content-Type': 'text/xml', 'SOAPAction': ""}

# SOAP parser
parser = etree.XMLParser(ns_clean=True, recover=True, encoding='utf-8')

if __name__ == "__main__":

    # Create the output dir if it doesn't exist
    if not os.path.exists(output_path):
        os.makedirs(output_path)
    
    recordID = "xxxxxxxxxxx"

    # Create output files
    base_output_file = output_path+'/tmp_' + recordID + '.mp4'
    new_output_file = output_path+'/' + recordID + '.mp4'

    #Get Storage Access Ticket
    etStorageAccessTicket[1][0][0].text = siteID
    etStorageAccessTicket[1][0][1].text = userID
    etStorageAccessTicket[1][0][2].text = userPW
    rStorageAccessTicket = requests.post(vaNBRstor, data=etree.tostring(etStorageAccessTicket), headers=stSOAPheaders)
    rSATxml = etree.fromstring(rStorageAccessTicket.text.encode('utf-8'), parser=parser)
    sessionSAT = rSATxml[0][0][0].text

    # Build XML for request
    etDlNbrStorageFile[1][0][0].text = siteID
    etDlNbrStorageFile[1][0][1].text = recordID
    etDlNbrStorageFile[1][0][2].text = sessionSAT

    # Send API POST request
    rDlNbrStorageFile = requests.post(vaNBRstor, data=etree.tostring(etDlNbrStorageFile), headers=stSOAPheaders, stream=True)
    dlFile = open(base_output_file, 'wb')

    # Save file to disk
    for chunk in rDlNbrStorageFile.iter_content(chunk_size=512):
        if chunk:
            dlFile.write(chunk)
    
    # Split utf-8 and binary data from response
    f = open(base_output_file, 'rb').read().split(str.encode('\r\n\r\n'))
    mp4 = open(new_output_file, 'wb')

    print(f[2].splitlines()[0].replace(str.encode(" "), str.encode("_")))
    
    # Save binary recording
    try:
        mp4.write(f[3])
    except IndexError:
        print(recordID + ": Recording does not exist")
        os.remove(base_output_file)
        os.remove(new_output_file)
        exit()

    # Remove tmp output file that had utf-8 and binary
    os.remove(base_output_file)

    print(recordID + ": Complete")