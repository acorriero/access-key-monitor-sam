import boto3
from datetime import datetime
from dateutil.tz import tzutc
from dateutil.relativedelta import relativedelta


client = boto3.client('iam')
current_date = datetime.now(tzutc())


def get_old_keys(key_list):
    '''
    Returns user key data older than the specified time
    '''
    old_keys = []
    for key in key_list:
        time_difference = current_date - key['CreateDate']
        
        # Check if CreateDate is longer than 1 year for active keys.
        if key['Status'] == 'Active' and time_difference.days > 365:
            old_keys.append(key)
    
    return old_keys


def format_key_list(key_list):
    '''
    Prepares output for delivery
    '''
    total_list = []
    for keys in key_list:
        username = keys['UserName']
        status = keys['Status']
        createdate = keys['CreateDate']

        duration = relativedelta(current_date, createdate)
        total_days = duration.years * 365 + duration.months * 30 + duration.days
        
        total_list.append(
            f"User {username} has an {status} key that is {total_days} days old and needs to be rotated."
        )

    return total_list

def lambda_handler(event, context):
    # Pull list of all users in IAM
    all_iam_names = client.list_users(
        PathPrefix='/'
    )
    
    # Get all user access key data
    users_key_list = []
    for user in all_iam_names['Users']:
        
        iam_key_list = client.list_access_keys(
            UserName=user['UserName']
        )
    
        for user_keys in iam_key_list['AccessKeyMetadata']:
            users_key_list.append(user_keys)
    
    old_key_list = get_old_keys(users_key_list)
    formatted_key_list = format_key_list(old_key_list)
    
    # Convert to string
    formatted_key_list_str = "\n".join(formatted_key_list)
    
    # Create a new AWS SNS client
    sns_client = boto3.client('sns')
    
    # Specify the topic ARN or topic name where you want to publish the message
    topic_arn = 'arn:aws:sns:us-east-1:${{env.Account}}:access_key_age_check'
    
    # Publish the message to the specified SNS topic
    try:
        response = sns_client.publish(
            TopicArn=topic_arn,
            Subject='Access Keys Older Than 365 Days',
            Message=formatted_key_list_str
        )
        print("Message sent successfully!")
    except Exception as e:
        print(f"Error sending message: {e}")

