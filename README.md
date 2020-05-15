# Webex recordings download sample

This sample code uses the Webex NBR XML/SOAP API: https://developer.cisco.com/docs/webex-meetings/#!nbr-web-services-api/overview

You need to request the Web service url and Site ID that correspond to your webex site by writing to: devsupport@webex.com
as specified here:  https://developer.cisco.com/docs/webex-meetings/#!nbr-web-services-api/soap-api-requests

Original repository: https://github.com/sloan58/webex-nbr-api 
This version has been updated to Python 3 and assumes mp4 recordings on the site. 

## Installation 

Make sure you have Python 3 and SQLLite installed.

Download the code into the local directory of the machine from where you will execute the code. 

Install dependencies needed for the scripts:

``` pip install -r requirements.txt ```



## Configuration

Copy the config_default.py file to config.py and 
assign values to the specified variables:  

siteID:  ID provided by the response you obtain writing to devsupport@webex.com that refers to the Webex site you have admin access to

userID: Email address of admin account for the site

userPW: Password for the userID specified above

webServiceP: Main Web service URL provided by the response you obtain writing to devsupport@webex.com that refers to the Webex site you have admin access to

webServiceB = Backup Web service URL provided by the response you obtain writing to devsupport@webex.com that refers to the Webex site you have

output_path = Path to local or network shared folder where the recordings that are downloaded should be saved.


## Runing the code

The code sample is divided into 4 python scripts that can be run independently:

- **create_db.py** Creates the the SQL Lite dabatase in a local file named "recordings.sqlite" and adds an empty "recordings" table
- **seed_db.py** Makes NBR API calls into the Webex cloud to extract the id of all the recordings it can find in the site and populates the "recordings" table in the database so the main application knows what to download
- **download_one.py** Downloads just one recording specified in the "recordID" variable within the script. This is just a testing script to make sure your environment is setup correctly and it can download and store to the output folder
- **download_all.py** Main script that looks for entries in the "recordings" table in the database and for any that do not have "COMPLETED" in the status field it will download to the output folder and update the status in the table. It will also update the meetingname field with the path to the downloaded recordings in mp4 format
- **delete_one.py** Deletes just one recording from the Webex cloud specified in the "delRecordID" variable within the script. This is just a testing script to make sure your environment is setup correctly and it can delete recordings
- **delete_all.py** Script that looks for entries in the "recordings" table in the database that are marked "COMPLETED" and checks that the file that was downloaded and specified in the meetingname field is still in existence. If the file is missing, it marks the status field in the recordings table as NULL so that it is downloaded the next time that **download_all.py** runs. 
 If a record in the DB that has status COMPLETED is already missing from the cloud, the status field is changed to MANUALDELETED. Otherwise, the script deletes it from the cloud and the status field is set to SCRIPTDELETED
 This script supports the ```-i```  argument to make it "interactive" and prompt before performing any deletions on the cloud or changes of status in the DB. 

The usual sequence is to run **create_db.py** upon installation or re-initialization of the code:

```python create_db.py```

Then you run **seed_db.py** to check for existing/new recordings, usually on a daily basis:

```python seed_db.py```

Right after **seed_db.py** completes, you run **download_all.py** to download the missing recordings:

```python download_all.py```

When you have verified that you have all the recordings you need downloaded to the destination folder,
you can run **delete_all.py** to remove them from the cloud. Use the ```-i``` option the first times you run it to validate what it is about to do: 

```python delete_all.py -i```

Afterwards, for it to run without prompting, you can just omit that argument as such: 

```python delete_all.py```

NOTE: If you wish to leave recordings in the cloud and still run these scripts, independent of if you let the script download it for the first time or not, 
just manually set the status field in the database for that recording to "SKIP" or any other string other than NULL or "COMPLETED" so that none of the scripts attempt to
download or delete the recording from the cloud. You do need to run **seed_db.py** to be able to create the entried in the table 
if they were not there already and if you mark it as "SKIP" before running **download_all.py** it will never download it.


You might want to run the above sequence on weekly basis to give ample time for recordings to be verified before erasing them. 
Only recordings that the **download_all.py** has downloaded before will deleted and only if the recording file is still present,
so any on-going meetings when the script is running or those meetings for which the recording just became available will not be 
considered for deletion. 

To automate the running of the scripts using the example timeframes described above and after ample testing,
we recommend you create a daily CRON job for running **seed_db.py** and **download_all.py** in sequence and also a separate weekly CRON job to run **delete_all.py** (without the -i option so it does not stop and ask for confirmation while running unattended)
