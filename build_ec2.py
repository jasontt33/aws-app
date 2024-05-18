import boto3
import sys, json
from botocore.exceptions import ClientError
import argparse
from loginator import get_logger

logger = get_logger('build_ec2')

def create_ec2_instance(server_type, owner, server_name):
    # Set the region and credentials
    ec2 = boto3.resource('ec2')
    logger.debug("ec2 client created")
    # Get the VPC ID
    vpc_id = 'vpc-090abe61ae804970e'
    logger.debug("vpc_id set to {}".format(vpc_id))

    # Create a security group and authorize inbound SSH traffic
    sec_group = ec2.create_security_group(
        GroupName=server_name + "-SG", Description=server_name + "-SG", VpcId=vpc_id)
    sec_group.authorize_ingress(
        IpPermissions=[
        {
                'IpProtocol': 'tcp',
                'FromPort': 22,
                'ToPort': 22,
                'IpRanges': [
                    {
                        'CidrIp': '209.133.27.66/32',
                        'Description': 'VPN IP address'
                    },
                ],
            },
        ],
    )
    logger.debug("security group created for SSH access")
    # roger Ts IP address
    sec_group.authorize_ingress(
        IpPermissions=[
        {
                'IpProtocol': 'tcp',
                'FromPort': 22,
                'ToPort': 22,
                'IpRanges': [
                    {
                        'CidrIp': '76.100.185.142/32',
                        'Description': 'roger Ts IP address'
                    },
                ],
            },
        ],
    )
    logger.debug("security group created for SSH access")


    # set tag specifications
    tag_specifications = [
        {
            'ResourceType': 'instance',
            'Tags': [
                {
                    'Key': 'Name',
                    'Value': server_name
                },
                {
                    'Key': 'Owner',
                    'Value': owner
                },
                {
                    'Key': 'CreatedBy',
                    'Value': 'AWS-APP-TOOL'
                }
            ]
        }
    ]

    # set user data script
    # set the nameserver to Google b/c the default is not working
    user_data_script = """#!/bin/bash
    echo "nameserver 8.8.8.8" | tee /etc/resolv.conf > /dev/null
    """
    # Prevent the resolv.conf file from being modified
    # write protect the resolv.conf file
    user_data_script_two = """#!/bin/bash chattr +i /etc/resolv.conf """
    user_data_memory_check = '''#!/bin/bash
    sudo yum update -y
    sudo yum install -y amazon-cloudwatch-agent

    # Configure the CloudWatch Agent
    sudo tee /etc/amazon/cloudwatch-agent.json > /dev/null <<EOF
    {
        "metrics": {
            "metrics_collected": {
                "mem": {
                    "measurement": [
                        "mem_used_percent"
                    ],
                    "metrics_collection_interval": 60
                },
                "swap": {
                    "measurement": [
                        "swap_used_percent"
                    ],
                    "metrics_collection_interval": 60
                }
            }
        }
    }
    EOF

    # Start the CloudWatch Agent
    sudo /opt/aws/amazon-cloudwatch-agent/bin/amazon-cloudwatch-agent-ctl -a fetch-config -m ec2 -s -c file:/etc/amazon/cloudwatch-agent.json
    '''

    # Create a new key pair
    key_pair_name = server_name+ '-key'
    response = ec2.create_key_pair(KeyName=key_pair_name)

    key_file = key_pair_name+ '.pem'
    # Save the private key to a file
    private_key = response.key_material
    with open(key_file, 'w') as f:
        f.write(private_key)

    # Set appropriate permissions on the private key file
    import os
    os.chmod(key_file, 0o400)
    with open(key_file, 'r') as file:
        # Read the file contents and store them in a variable
        key_contents = file.read()

    # send the pem key to the email address
    lambda_client = boto3.client('lambda')
    pem_key_event = {"sender": "customsolutions@roger.org","recipient": "customsolutions@roger.org","subject": "ec2 created with a new pem key  "+server_name,"body": key_contents}

    response = lambda_client.invoke(
    FunctionName='emailer-test',
    Payload=json.dumps(pem_key_event),
    )
    logger.debug("key created and email sent, email response ")
    logger.debug("pem key sent to cloud and custom solutions email address")

    # Launch a t3a.micro instance
    try:
        instance = ec2.create_instances(
            ImageId='ami-005f9685cb30f234b',
            InstanceType=server_type,
            MaxCount=1,
            MinCount=1,
            KeyName = key_pair_name,
            UserData=user_data_script+user_data_script_two + user_data_memory_check,
            TagSpecifications=tag_specifications,
            NetworkInterfaces=[
                {
                    'DeviceIndex': 0,
                    'SubnetId': 'subnet-07ef73d81b0a3789e',
                    'AssociatePublicIpAddress': True,
                    'Groups': [sec_group.group_id]
                }
            ]
        )[0]
        logger.debug("instance created usgin ami-005f9685cb30f234b and subnet-07ef73d81b0a3789e")
    except ClientError as e:
        logger.error(e)
        sys.exit(1)
    # Wait for the instance to be running
    instance.wait_until_running()
    logger.debug("instance is running")
    instance_id = instance.instance_id
    logger.debug("instance id is {}".format(instance_id))
    instance_name = server_name
    logger.debug("instance name is {}".format(instance_name))
   
    # Return the instance ID and name for use in the next function
    return instance_id, instance_name, key_contents

def create_cloudwatch_alarm(instance_id, instance_name):
    sns = boto3.client('sns')
    logger.debug("sns client created")
    response = sns.create_topic(Name=instance_id +'_'+ instance_name +'-CPU-alarm')
    topic_arn = response['TopicArn']
    logger.debug("topic arn created for CPU alarm")

    sns = boto3.client('sns')
    response = sns.create_topic(Name=instance_id +'_'+ instance_name +'-disk-use-alarm')
    topic_arn_disk = response['TopicArn']
    logger.debug("topic arn created for disk alarm")

    sns = boto3.client('sns')
    response = sns.create_topic(Name=instance_id +'_'+ instance_name +'-excessive-memory-use-alarm')
    topic_arn_memory = response['TopicArn']
    logger.debug("topic arn created for memory alarm")

    cloudwatch = boto3.client('cloudwatch')
    logger.debug("cloudwatch client created")

    metric_filter = {
    "MetricName": "CPUUtilization",
    "Namespace": "AWS/EC2",
    "Dimensions": [
        {
            "Name": "InstanceId",
            "Value": instance_id
        }
    ],
    "Period": 60,
    "Stat": "Average"
    }

    alarm_name = instance_id + '_' + instance_name + '_CPU Utilization'
    alarm_description = instance_id + '_' + instance_name + '_CPU Utilization'
    alarm_threshold = 90.0
    alarm_actions = [topic_arn]

    try:
        response_cloudwatch = cloudwatch.put_metric_alarm(
            AlarmName=alarm_name,
            AlarmDescription=alarm_description,
            ActionsEnabled=True,
            OKActions=[],
            AlarmActions=alarm_actions,
            MetricName=metric_filter['MetricName'],
            Namespace=metric_filter['Namespace'],
            Statistic=metric_filter['Stat'],
            Dimensions=metric_filter['Dimensions'],
            Period=metric_filter['Period'],
            EvaluationPeriods=1,
            Threshold=alarm_threshold,
            ComparisonOperator='GreaterThanThreshold'
    )
        logger.debug("cloudwatch alarm created for CPU for instance {}".format(instance_id))
 
    except ClientError as e:
        logger.error(e)
        sys.exit(1)

    
    metric_filter = {
    "Namespace": "CWAgent",
    "MetricName": "disk_used_percent",
    "Dimensions": [
        {
            "Name": "InstanceId",
            "Value": instance_id
        }
    ]
    }

    alarm_actions_disk = [topic_arn_disk]
    alarm_name = instance_id + ' ' + instance_name + ' Disk Space Utilization'
    alarm_description = instance_id + ' ' + instance_name + ' Disk Space Utilization'
    
    try:
        response_cloudwatch = cloudwatch.put_metric_alarm(
            AlarmName=alarm_name,
            AlarmDescription=alarm_description,
            ActionsEnabled=True,
            OKActions=[],
            AlarmActions=alarm_actions_disk,
            MetricName=metric_filter['MetricName'],
            Namespace=metric_filter['Namespace'],
            Statistic='Average',
            Dimensions=metric_filter['Dimensions'],
            Period=300,
            EvaluationPeriods=1,
            Threshold=90.0,
            ComparisonOperator='GreaterThanThreshold'
    )
        logger.debug("cloudwatch alarm created for disk for instance {}".format(instance_id))
    except ClientError as e:
        logger.error(e)
        sys.exit(1)

    # return topic_arn, topic_arn_disk, topic_arn_memory for use in the next function
    return topic_arn, topic_arn_disk, topic_arn_memory

def subscribe_to_alarm(topic_arn, topic_arn_disk, topic_arn_memory):

    sns = boto3.client('sns')
    logger.debug("sns client created")

    response = sns.subscribe(
        TopicArn=topic_arn,
        Protocol='email', # or 'sms'
        Endpoint='customsolutions@roger.org' # or your phone number
    )
    
    response = sns.subscribe(
        TopicArn=topic_arn,
        Protocol='email', # or 'sms'
        Endpoint='smotlani@roger.org' # or your phone number
    )
    logger.debug("subscribed to topic arn for CPU alarm")
    response = sns.subscribe(
        TopicArn=topic_arn_disk,
        Protocol='email', # or 'sms'
        Endpoint='customsolutions@roger.org' # or your phone number
    )

    response = sns.subscribe(
        TopicArn=topic_arn_disk,
        Protocol='email', # or 'sms'
        Endpoint='smotlani@roger.org' # or your phone number
    )
    logger.debug("subscribed to topic arn for disk alarm")

    response = sns.subscribe(
        TopicArn=topic_arn_memory,
        Protocol='email', # or 'sms'
        Endpoint='customsolutions@roger.org' # or your phone number
    )

    response = sns.subscribe(
        TopicArn=topic_arn_memory,
        Protocol='email', # or 'sms'
        Endpoint='smotlani@roger.org' # or your phone number
    )
    logger.debug("subscribed to topic arn for memory alarm")



# def main():
#     # create argument parser
#     parser = argparse.ArgumentParser(description='Build EC2 instance and Cloudwatch alarm. This script takes 3 arguemnts, server type, owner, and server name, in that order. Example: python3 create_ec2_instance.py t3a.micro owner server_name')
#     # parse arguments
#     args = parser.parse_args()
#     print(args)
#     # The first argument (index 0) is the name of the script itself
#     # create argument parser
#     if len(sys.argv) == 4:
#         server_type = sys.argv[1]
#         owner = sys.argv[2]
#         server_name = sys.argv[3]
#         # at least one command line argument was passed
#         argument = sys.argv[3]
#         # do something with the argument
#         print("Server Type:", server_type)
#         print("Owner:", owner)
#         print("Server Name:", server_name)
#         instance_id, instance_name = create_ec2_instance(server_type, owner, server_name)
#         topic_arn, topic_arn_two = create_cloudwatch_alarm(instance_id, instance_name)
#         subscribe_to_alarm(topic_arn, topic_arn_two)
#         print('Public IP address of server:', instance_id.public_ip_address)
        
#     elif len(sys.argv) == 2 or len(sys.argv) == 1 or len(sys.argv) > 3:
#         # no command line arguments were passed
#         print("Please provide THREE arguments, 1. server type, e.g. t3a.micro and 2. owner or person creating this VM, e.g. roger roger, 3. add a server name, e.g. devo-test-server.")

# if __name__ == "__main__":
#     main()