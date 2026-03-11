TravelGo
A simple Flask web application for travel booking using AWS services.

Features
User registration and login
Dashboard for booking
Email notifications via SNS
User data stored in DynamoDB
Setup

Install dependencies:

pip install -r requirements.txt
Configure AWS:

Install AWS CLI: pip install awscli
Configure credentials: aws configure
Or set environment variables: AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, AWS_DEFAULT_REGION
Create DynamoDB tables:

Run the setup script: python setup_dynamodb.py
Or manually create tables: Users (UserID), Bookings (BookingID), Transport (TransportID)
Create SNS topic:

Create an SNS topic for booking notifications
Set the ARN as environment variable: SNS_TOPIC_ARN=arn:aws:sns:region:account:topic-name


Environment Variables

SNS_TOPIC_ARN: ARN of the SNS topic for booking notifications (auto-set when using mocks)
AWS_ACCESS_KEY_ID: Your AWS access key (not needed with mocks)
AWS_SECRET_ACCESS_KEY: Your AWS secret key 
AWS_DEFAULT_REGION: AWS region (e.g., us-east-1)
Structure
app.py: Main Flask application
services/: AWS service integrations
templates/: HTML templates
requirements.txt: Python dependencies
