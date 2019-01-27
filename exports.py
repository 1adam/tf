from __future__ import print_function
import json, boto3

def find_latest_bionic_ami():
  client = boto3.client('ec2')
  resp = client.describe_images(
    Filters=[
      { 'Name': 'architecture', 'Values': ['x86_64'] },
      { 'Name': 'owner-id', 'Values': ['099720109477'] },
      { 'Name': 'name', 'Values': ['ubuntu/images/hvm-ssd/ubuntu-bionic-18.04*'] },
      { 'Name': 'description', 'Values': ['*LTS*'] }
    ])
  for ami in resp['Images']:
    final = sorted(resp['Images'], key=lambda x: x['CreationDate'], reverse=True)
    return final[0]['ImageId']

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

    ec2_exist = boto3.resource('ec2').instances.filter(
      Filters=[{'Name': 'instance-state-name', 'Values': ['running'] }, {'Name': 'tag:Name', 'Values': [deployEnv + "_" + madeBy]} ])
    for inst_exist in ec2_exist:
        print('found existing vm called ', deployEnv+"_"+madeBy)
        return 2

    ec2_inst = boto3.client('ec2')

    latest_bionic_ami = find_latest_bionic_ami()

    resp = ec2_inst.run_instances(
        ImageId=latest_bionic_ami,
        InstanceType=instType,
        MaxCount=1,
        MinCount=1,
        TagSpecifications=[{
            'ResourceType': 'instance',
            'Tags': [
                {"Key": "Name", "Value": deployEnv+"_"+madeBy }
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
