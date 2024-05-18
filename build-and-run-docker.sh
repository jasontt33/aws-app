#!/bin/bash

docker build -t aws-app .

docker run -v ~/.aws/:/root/.aws -p 5050:5050 aws-app
