import boto3


def get_instance_ids_with_names():
    # Get all instances
    ec2 = boto3.client('ec2')
    response = ec2.describe_instances()
    # Initialize an empty list to store instances that match the filter criteria
    filtered_instances = []
    # Loop through all instances and filter by operating system type
    for reservation in response['Reservations']:
        for instance in reservation['Instances']:
            print(instance)
            if instance['PlatformDetails'].startswith('Linux') and instance['ImageId'].startswith('ami-0'):
                print("*************************************")
                print(instance['InstanceId'], instance['ImageId'], instance['PlatformDetails'])
                # Append the instance ID and name to the filtered instances list
                filtered_instances.append({
                    'InstanceId': instance['InstanceId'],
                    'Name': [tag['Value'] for tag in instance['Tags'] if tag['Key'] == 'Name'][0]
                })

    # Print the filtered instances list
    print(filtered_instances)
    return filtered_instances

if __name__ == '__main__':
    get_instance_ids_with_names()