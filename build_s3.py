#!/usr/bin/env python3
import boto3
import argparse
import sys
import os


def create_bucket(bucket_name, owner):
    # Initialize S3 client
    s3 = boto3.client('s3', region_name='us-east-1')

    # Define bucket name and tags
    bucket_name = bucket_name
    owner_tag = {'Key': 'Owner', 'Value': owner}
    environment_tag = {'Key': 'Environment', 'Value': 'non-prod'}

    # Create the bucket
    session = boto3.session.Session()
    current_region = session.region_name
    if current_region == 'us-east-1':
        try:
            response = s3.create_bucket(Bucket=bucket_name)
            print(response)
            print('Bucket created in us-east-1' + bucket_name)
        except Exception as error:
            print(error)
    else:
        try:
            response = s3.create_bucket(Bucket=bucket_name, CreateBucketConfiguration={'LocationConstraint': current_region})
            print(response)
            print('Bucket created in ' + current_region + ' ' + bucket_name)
        except Exception as error:
            print(error)
    # Add the tags to the bucket
    s3.put_bucket_tagging(
    Bucket=bucket_name,
    Tagging={'TagSet': [owner_tag, environment_tag]}
    )
    # set the bucket to private
    response_public = s3.put_public_access_block(
        Bucket=bucket_name,
        PublicAccessBlockConfiguration={
            'BlockPublicAcls': True,
            'IgnorePublicAcls': True,
            'BlockPublicPolicy': True,
            'RestrictPublicBuckets': True
        },
    )


