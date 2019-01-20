from __future__ import print_function
import json, boto3

def verify_msg( incMsg ):
    for field in ["creator_name","type","environment"]:
        try:
            incMsg[field]
        except:
            return False
    return True

def parse_msg( incMsg ):
    types_map = {
        'simple-dev': 't3.nano',
        'big-dev': 't3.small'
    }

    madeBy = incMsg['creator_name']
    instType = types_map[ incMsg['type'] ]
    deployEnv = incMsg['environment']

    ec2_inst = boto3.client('ec2')

    resp = ec2_inst.run_instances(
        ImageId='ami-0b86cfbff176b7d3a',
        InstanceType=instType,
        MaxCount=1,
        MinCount=1,
        TagSpecifications=[{
            'ResourceType': 'instance',
            'Tags': [
                {"Key": "Name", "Value": deployEnv + "_" + madeBy }
            ]
        }]
    )


def proc_new_msg(event, context):

    for msg in event['Records']:
        msg_body = json.loads(msg['body'])
        if verify_msg(msg_body) == False:
            return {
                'statusCode': '502',
                'msg': 'Invalid Message'
            }
        print('---------------------------------------------')
        print('Received from ' + msg['eventSourceARN'] + ' ...')
        print('Creation initiated by ' + msg_body['creator_name'])
        print('Type of instance: ' + msg_body['type'])
        print('In environment: ' + msg_body['environment'])
        print('---------------------------------------------')

        parse_msg(msg_body)

    return {
        'statusCode': 200,
        'msg': 'OK'
    }
