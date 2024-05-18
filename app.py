import build_ec2
import boto3
import config as cfg
import creds as cf
import time
import json

from build_alarms_for_ec2 import create_sns_topic, create_cloudwatch_alarm
from build_s3 import create_bucket
from check_SGs import check_SGs
from flask import Flask, render_template, request, redirect, session, url_for, flash
from flask_cognito_lib import CognitoAuth
from flask_cognito_lib.decorators import (
    auth_required,
    cognito_login,
    cognito_login_callback,
    cognito_logout,
)
from loginator import get_logger
from run_ssm_command import send_command
from werkzeug.exceptions import HTTPException
from wtforms import Form, StringField, SelectField
from wtforms.validators import InputRequired

## Setting up logging
logger = get_logger('app')

# Initialize the Flask application
app = Flask(__name__)
app.secret_key = cf.get_it.secret_key

# Configure Cognito authentication
cognito_settings = cfg.get_cognito_settings().split(",")
region = cognito_settings[0]
pool_id = cognito_settings[1]
client_id = cognito_settings[2]
redirect_url = cognito_settings[3]
logout_url = cognito_settings[4]
domain = cognito_settings[5]

#Configure Cognito authentication
app.config["AWS_REGION"] = region
app.config["AWS_COGNITO_USER_POOL_ID"] = pool_id
app.config["AWS_COGNITO_USER_POOL_CLIENT_ID"] = client_id
app.config["AWS_COGNITO_REDIRECT_URL"] = redirect_url
app.config["AWS_COGNITO_LOGOUT_URL"] = logout_url
app.config["AWS_COGNITO_USER_POOL_CLIENT_SECRET"] = cf.get_it.cognito_secret
app.config["AWS_COGNITO_DOMAIN"] = domain

auth = CognitoAuth(app)

def get_instance_ids_with_names():
    # Get all instances
    ec2 = boto3.client('ec2', region_name='us-east-1')
    response = ec2.describe_instances()

    # Initialize an empty list to store instances that match the filter criteria
    filtered_instances = []

    # Loop through all instances and filter by operating system type
    for reservation in response['Reservations']:
        for instance in reservation['Instances']:
            if instance['PlatformDetails'].startswith('Linux') and instance['ImageId'].startswith('ami-0'):
                instance
                # Append the instance ID and name to the filtered instances list
                filtered_instances.append({
                    'InstanceId': instance['InstanceId'].replace("'","").replace("[", "").replace("]", ""),
                    'Name': [tag['Value'] for tag in instance['Tags'] if tag['Key'] == 'Name'][0]
                })

    return filtered_instances

def get_server_types():
    #TODO add more types later
    instance_types = ["t3a.nano", "t3a.micro", "t3a.small", "t3a.medium", "t3a.large", "t3a.xlarge", 
                       "t3a.2xlarge", "t2.nano", "t2.micro", "t2.small", "t2.medium", "t2.large", "t2.xlarge", "t2.2xlarge"]
    instance_types.sort()

    # return the list of instance types
    return instance_types

class Ec2Form(Form):
    server_type = SelectField('Server Type: ', choices=get_server_types(), validators=[InputRequired()])
    owner = StringField('Owner', validators=[InputRequired()])
    server_name = StringField('Server Name', validators=[InputRequired()])
    def generate_csrf_token(self, csrf_context):
        return super(Ec2Form, self).generate_csrf_token(csrf_context)

class s3Form(Form):
    bucket_name = StringField('Bucket Name: ', validators=[InputRequired()])
    owner = StringField('Owner: ', validators=[InputRequired()])
    def generate_csrf_token(self, csrf_context):
        return super(s3Form, self).generate_csrf_token(csrf_context)

class alarmsForm(Form):
    instance_id = StringField('Instance ID: ', validators=[InputRequired()])
    def generate_csrf_token(self, csrf_context):
        return super(alarmsForm, self).generate_csrf_token(csrf_context)
    
class commandForm(Form):
    instances = SelectField('Instance ID: ', choices=get_instance_ids_with_names(), validators=[InputRequired()])
    command = StringField('Command: ', validators=[InputRequired()])
    def generate_csrf_token(self, csrf_context):
        return super(commandForm, self).generate_csrf_token(csrf_context)

# redirect on 403
@app.errorhandler(HTTPException)
def page_not_found(e):
    return redirect(url_for("login"))

## health check endpoint
# this is used by the load balancer to check if the app is up
@app.route("/health")
def health():
    return "Server is up! OK!" 


# Login endpoint
@app.route("/", methods=["GET", "POST"])
@auth_required()
def index():
    return render_template("index.html")
    
# login for cognito
@app.route("/login")
@cognito_login
def login():
    ## By default, routes to the cognito hosted login UI
    pass

#this is where cognito sends you back to when authenticated
@app.route("/postlogin")
@cognito_login_callback
def postlogin():
    #routes to actual page
    return redirect("/")

# Home endpoint
@app.route("/ec2_create", methods=["GET", "POST"])
@auth_required()
def ec2_create():
    email = session["user_info"].get('email')
    logger.debug("user accessed the home page : {}".format(email))
    key = ""
    form = Ec2Form(request.form)
    if request.method == 'POST' and form.validate():
        server_type = form.server_type.data
        owner = form.owner.data
        server_name = form.server_name.data
        logger.debug("user defined variables passed into the creation of EC2 : {}".format(server_name) + " " + "{}".format(server_type) + " " + "{}".format(owner))
        instance_id, instance_name, key = build_ec2.create_ec2_instance(server_type, owner, server_name)
        topic_arn, topic_arn_disk, topic_arn_memory = build_ec2.create_cloudwatch_alarm(instance_id=instance_id, instance_name=instance_name)
        build_ec2.subscribe_to_alarm(topic_arn=topic_arn, topic_arn_disk=topic_arn_disk, topic_arn_memory=topic_arn_memory)
        
        print(key)
        flash('EC2 instance created: '+instance_id+ ' with name: '+ server_name, 'success')
        logger.debug("user created EC2 instance : {}".format(instance_id))
        return render_template("ec2_create.html", form=form, email=email, key=key)
    else:
        return render_template("ec2_create.html", form=form, email=email, key=key)
    

# s3 endpoint
@app.route("/s3_create", methods=["GET", "POST"])
@auth_required()
def s3_create():
    email = session["user_info"].get('email')
    logger.debug("user accessed the s3_create page : {}".format(email))
      
    form = s3Form(request.form)
    if request.method == 'POST' and form.validate():
        bucket_name = form.bucket_name.data
        owner = form.owner.data
        logger.debug("user defined variables passed into the creation of s3 : {}".format(bucket_name) + " " + "{}".format(owner))
        create_bucket(bucket_name, owner)
        flash('s3 bucket creation successful with name: '+bucket_name, 'success')
        logger.debug("user created  s3 bucket : {}".format(bucket_name))
        return redirect(url_for("s3_create"))
       
    else:
        return render_template("s3_create.html", form=form, email=email)
    
    return render_template('s3_create.html', form=form)

# configure alarm 4 ec2 endpoint
@app.route("/config_alarms", methods=["GET", "POST"])
@auth_required()
def config_alarms():
    email = session["user_info"].get('email')
    logger.debug("user accessed the config alarms page : {}".format(email))
      
    form = alarmsForm(request.form)
    if request.method == 'POST' and form.validate():
        instance_id = form.instance_id.data
        logger.debug("user defined variables passed into the creation of cloudwatch alarms : {}".format(instance_id))
        topic_arn_cpu, topic_arn_memory, topic_arn_disk_use = create_sns_topic(instance_id)
        create_cloudwatch_alarm(instance_id, topic_arn_cpu, topic_arn_memory, topic_arn_disk_use)
        flash('SNS Topic creation successful with name: '+topic_arn_cpu+ ' '+ topic_arn_disk_use+ ' ' +topic_arn_memory, 'success')
        flash('CW alarm creation successful with name: '+instance_id, 'success')
        logger.debug("user created CW Alarms for : {}".format(instance_id))
        return redirect(url_for("config_alarms"))
       
    else:
        return render_template("config_alarms.html", form=form, email=email)
    
    return render_template('config_alams.html', form=form)

# SGs endpoint
@app.route("/sgs", methods=["GET", "POST", "DELETE"])
@auth_required()
def sgs():
    email = session["user_info"].get('email')
    logger.debug("user accessed the Security Groups page : {}".format(email))
    
    if request.method == 'POST':
        # Start the long running function in a separate thread
        
        progress = 0
        while progress < 100:
            count, sg_groups_dict = check_SGs()
            progress += 10
            time.sleep(1)
        #return 'SGs checked!'
        #print(sg_groups_dict)
        #print(sg_groups_dict.values())
        # Convert the list of JSON objects to a list of dictionaries
         # = json.dumps(security_groups)
        #data = json.loads(data)
        sg_names = sg_groups_dict.keys()


        logger.debug(email + " checked security groups : {}".format(email))
        return render_template('sgs.html', email=email, count=count, sg_names=sg_names)
    
    else:
        return render_template('sgs.html', email=email)
    
    
@app.route("/sgs_del/<sg_name>", methods=["GET", "POST", "DELETE"])
@auth_required()
def sgs_del(sg_name):
    email = session["user_info"].get('email')
    logger.debug("user accessed the Security Groups DELETE function : {}".format(email))
    ec2 = boto3.client('ec2')
    print(sg_name)
    print(request.method)
    if request.method == 'POST':
        # Get the security group ID from the name
        response = ec2.describe_security_groups(
            Filters=[
                {'Name': 'group-name', 'Values': [sg_name]}
            ]
        )
        security_group_id = response['SecurityGroups'][0]['GroupId']
        print(security_group_id)
        
        # Delete the security group
        response = ec2.delete_security_group(GroupId=security_group_id)
        print(response)
        return render_template('sgs.html', email=email, sg_name=sg_name, security_group_id=security_group_id)
    else:
        return render_template('sgs.html', email=email, sg_name=sg_name)

@app.route("/command", methods=["GET", "POST"])
@auth_required()
def command():
    email = session["user_info"].get('email')
    logger.debug("user accessed the command page : {}".format(email))
    form = commandForm(request.form)
    if request.method == 'POST' and form.validate():
        instance_id = form.instances.data
        print(instance_id)
        command = form.command.data
        print(command)
        logger.debug("user defined variables passed into the command function : {}".format(instance_id) + " " + "{}".format(command))
        send_command(instance_id, command)
        flash('command execution successful with name: '+command, 'success')
        logger.debug("user executed command : {}".format(command))
        return redirect(url_for("command"))
       
    else:
        return render_template("command.html", form=form, email=email)
    
       
# logout function
@app.route("/logout")
@cognito_logout
def logout():
    # Logout of the Cognito User pool and delete the cookies that were set
    # on login.
    # No logic is required here as it simply redirects to Cognito
    pass
    
# after logout, redirect to index
@app.route("/postlogout")
def postlogout():
    # This is the endpoint Cognito redirects to after a user has logged out,
    # handle any logic here, like returning to the homepage.
    # This route must be set as one of the User Pool client's Sign Out URLs.8
    return redirect("/")


if __name__ == "__main__":
    app.run(host="0.0.0.0", port="5000",  debug=True)

