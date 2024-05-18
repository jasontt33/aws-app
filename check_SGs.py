# Description: This script will check all the SGs in the account and delete the ones that are not in use
import boto3

def check_SGs():
    ec2 = boto3.client('ec2', region_name='us-east-1')

    # Get a list of all security groups
    security_groups = ec2.describe_security_groups()['SecurityGroups']
    count = 0
    sec_groups = []
    ip_groups = []
    # Iterate over each security group and check if it is in use
    for sg in security_groups:
        # Get a list of all network interfaces associated with the security group
        network_interfaces = ec2.describe_network_interfaces(Filters=[
            {'Name': 'group-id', 'Values': [sg['GroupId']]}
        ])['NetworkInterfaces']

        # If there are no network interfaces associated with the security group, delete it
        if not network_interfaces:
            count+=1
            # print(f" security group {sg['GroupId']} is not in use. want to delete it?")
            response = ec2.describe_security_groups(GroupIds=[sg['GroupId']])
            # print("Describe Security Groups:")
            # print("response")
            # print(response)
            #sec_groups.append(response)
            group_name = response.get('SecurityGroups')[0].get('GroupName')
            sec_groups.append(group_name)
            ip_permissions = response.get('SecurityGroups')[0].get('IpPermissions')
            ip_groups.append(ip_permissions)
            # sec_groups.append(group_name + " " + str(ip_permissions))
            # print("")
            # print("Name of Group: " +response.get('SecurityGroups')[0].get('GroupName'))
            # print("")
            # print("Describe IpPermissions: " + str(response.get('SecurityGroups')[0].get('IpPermissions')))
            # # prompt = input("Do you want to delete this SG? (y/n): ")
            # if prompt == "y":
            #     print("Deleting security group " + sg['GroupId'])
            #     ec2.delete_security_group(GroupId=sg['GroupId'])
            # else:
            #     print("Skipping security group " + sg['GroupId'])
    # using dictionary comprehension
    # to convert lists to dictionary
    sg_groups_dict = {sec_groups[i]: ip_groups[i] for i in range(len(sec_groups))}
 
    return count, sg_groups_dict
         
    print("Total count for all SGs not attached ",count)