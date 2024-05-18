import boto3
import botocore
import time
from loginator import get_logger

## Setting up logging
logger = get_logger('run-ssm-command')

def send_command(instance_id, user_entered_command):
    ssm_client = boto3.client('ssm')

    instance_id = 'i-0c66e6914b09eeb02'
    user_entered_command = 'ls -la; sleep 10; ls -la'

    instance_ids = [instance_id]
    document_name = 'AWS-RunShellScript'
    command = user_entered_command
    parameters = {'commands': [command]}
# output_bucket = 'my-bucket'
# output_prefix = 'output/'

    response = ssm_client.send_command(
        InstanceIds=instance_ids,
        DocumentName=document_name,
        Parameters=parameters)
        # OutputS3BucketName=output_bucket,
        # OutputS3KeyPrefix=output_prefix


    logger.debug("user sent command "+ command + " to instance : {}".format(instance_id))

    command_id = response['Command']['CommandId']
    logger.debug("command id is : {}".format(command_id))

    # Wait for the command to complete
    while True:
        try:
            status = ssm_client.get_command_invocation(
                CommandId=command_id,
                InstanceId=instance_id,
            )['Status']
            if status in ['Pending', 'InProgress']:
                continue
            elif status == 'Success':
                output = ssm_client.get_command_invocation(
                    CommandId=command_id,
                    InstanceId=instance_id,
                )['StandardOutputContent']
                break
            else:
                output = ssm_client.get_command_invocation(
                    CommandId=command_id,
                    InstanceId=instance_id,
                )['StandardErrorContent']
                break
        except botocore.exceptions.ClientError as e:
            if e.response['Error']['Code'] == 'InvocationDoesNotExist':
                logger.debug("command not found yet, waiting 5 seconds")
                # Wait for command execution to start
                time.sleep(5)
            else:
                # Handle other errors
                logger.debug("error  with ssm command is : {}".format(e))
                raise

    logger.debug("command output is : {}".format(output))
    return output

