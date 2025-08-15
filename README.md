# SAAS---Data-privacy-and-compliance-report
takes in data from users and checks for ppi, ccpa and gdpa policy guidelines using aws macie and aws s3


-> the front end is static since it needs to be hosted on ec2

-> the upload page takes in a csv file and pushes it into aws s3 bucket

-> the aws macie is triggered whenever data enters that specific bucket using a aws lambda function

-> aws macie scans the data for ccpa/gdpa privacy policy

-> compliance report in the form of json is returned to the bucket

-> report is converted to pdf format and simple visualisation also can be done
# s3aws
