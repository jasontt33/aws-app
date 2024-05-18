# README #

This is a utility application for building and maintaining AWS infrastructure, using python flask and AWS boto3 SDK. The idea is to standardize how we build things in AWS and to improve the speed at which we can deploy infrastrucuture. This app is intended to make building infrascture easy for developers and cloud practioners.  

### What is this repository for? ###

* Used to build AWS infrastructure
* Feel free to contribute
* This may one day be replaced with a more traditional IaC 
* I think it is posssible for us to both use the CDK and SDK in this repo


### How do I get set up? ###

* pip3 install -r requirements.txt
* python3 app.py to run the app as a dev instance. Gunicorn should be used with production deployments
* must have a full admin AWS CLI user creds in aws configure. This is how it connects to various aws services to create things
* This app uses AWS cognito and you'll need to add a user to the user pool to be able to log in. Go to cognito in non-prod and choose aws_tools user pool to add your user account. 


### Contribution guidelines ###

* Work in the dev branch, the push to the repo, then create PR to be merged into prod
* 

### Who do I talk to? ###

* Jason Thompson / Custom Solutions
