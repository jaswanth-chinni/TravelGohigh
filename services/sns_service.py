import os
import boto3

REGION = os.getenv('AWS_DEFAULT_REGION', 'ap-south-1')
SNS_TOPIC_ARN = os.getenv('SNS_TOPIC_ARN', '')

def get_sns_client():
    return boto3.client('sns', region_name=REGION)

def send_notification(email, message, subject="TravelGo Notification"):
    """Send SNS notification. In production, SNS topic with email subscription."""
    sns = get_sns_client()
    if SNS_TOPIC_ARN:
        sns.publish(
            TopicArn=SNS_TOPIC_ARN,
            Message=message,
            Subject=subject,
            MessageAttributes={
                'email': {
                    'DataType': 'String',
                    'StringValue': email
                }
            }
        )
    else:
        print(f"[SNS Skipped - No ARN] To: {email} | Subject: {subject}")
        print(f"Message: {message}")
