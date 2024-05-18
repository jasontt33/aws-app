import boto3


def find_ec2_with_no_owner_tags():
    instances = [i for i in boto3.resource('ec2', region_name='us-east-1').instances.all()]

    first_pass = []
    # Print instance_id of instances that do not have a Tag of Key='Foo'
    for i in instances:
        if i.tags is not None and 'owner' not in [t['Key'] for t in i.tags]:
            print(i.instance_id)
            print(i.tags)
            first_pass.append(i)

    for i in first_pass:
        if i.tags is not None and 'Owner' not in [t['Key'] for t in i.tags]:
            print(i.instance_id)
            print(i.tags)


def find_ec2_with_no_project_tags():
    instances = [i for i in boto3.resource('ec2', region_name='us-east-1').instances.all()]

    first_pass = []
    # Print instance_id of instances that do not have a Tag of Key='Foo'
    for i in instances:
        if i.tags is not None and 'project' not in [t['Key'] for t in i.tags]:
            print(i.instance_id)
            print(i.tags)
            first_pass.append(i)

    for i in first_pass:
        if i.tags is not None and 'Project' not in [t['Key'] for t in i.tags]:
            print(i.instance_id)
            print(i.tags)

if __name__ == '__main__':
    #find_ec2_with_no_owner_tags()
    find_ec2_with_no_project_tags()


