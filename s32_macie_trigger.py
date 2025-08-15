import json
import boto3
import uuid
import time

s3_client = boto3.client('s3')
macie_client = boto3.client('macie2')
sts_client = boto3.client('sts')

def lambda_handler(event, context):
    print("Received Event:", json.dumps(event, indent=2))

    try:
        # Extract bucket name and file name
        record = event['Records'][0]
        bucket_name = record['s3']['bucket']['name']
        file_name = record['s3']['object']['key']
        
        print(f"New file uploaded: {file_name} in {bucket_name}")

        # Get AWS Account ID dynamically
        account_id = sts_client.get_caller_identity()["Account"]
        print(f"Account ID: {account_id}")

        # Generate a unique job name and client token
        timestamp = int(time.time())
        job_name = f"MacieScanJob_{timestamp}"
        client_token = str(uuid.uuid4())

        print(f"Creating Macie Job: {job_name}")

        # Start a Macie classification job
        response = macie_client.create_classification_job(
            name=job_name,
            description="Scan uploaded CSV for sensitive data",
            s3JobDefinition={
                "bucketDefinitions": [
                    {
                        "accountId": account_id,
                        "buckets": [bucket_name]
                    }
                ]
            },
            jobType="ONE_TIME",
            customDataIdentifierIds=[],
            initialRun=True,
            clientToken=client_token
        )

        print("Macie Job Started Successfully:", json.dumps(response, indent=2))

        return {
            "statusCode": 200,
            "body": f"Macie Job '{job_name}' Triggered Successfully"
        }

    except Exception as e:
        print(f"Error: {str(e)}")
        return {
            "statusCode": 500,
            "body": f"Error: {str(e)}"
        }
