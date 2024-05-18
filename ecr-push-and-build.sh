#!/bin/bash

aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin 955254544426.dkr.ecr.us-east-1.amazonaws.com

docker rmi aws-app/aws-app
docker buildx build --platform linux/amd64 -t aws-app/aws-app .
docker tag aws-app/aws-app:latest 955254544426.dkr.ecr.us-east-1.amazonaws.com/aws-app/aws-app:latest
docker push 955254544426.dkr.ecr.us-east-1.amazonaws.com/aws-app/aws-app:latest
