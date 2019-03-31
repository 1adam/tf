from __future__ import print_function
import json, boto3, os
from botocore.exceptions import ClientError

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
    valid_fields = ['creator_name','type','environment']
    valid_values = {
      'creator_name': [ '1adam' ],
      'type': ['simple-dev','simple-stg'],
      'environment': ['dev','stg']
    }

    for field in valid_fields:
      try:
          incMsg[field]
      except:
          return False
      else:
        if incMsg[field] not in valid_values[field]:
          return False
    return True

def inst_exist_by_name( instName ):
    ec2_exist = boto3.resource('ec2').instances.filter(
      Filters=[{'Name': 'instance-state-name', 'Values': ['running'] }, {'Name': 'tag:Name', 'Values': [ instName ] } ])
    for inst_exist in ec2_exist:
        return instName
    return False

def parse_msg( incMsg ):
    inst_types_map = {
      'simple-dev': 't3.nano',
      'simple-stg': 't3.nano'
    }

    madeBy = incMsg['creator_name']
    instType = inst_types_map[ incMsg['type'] ]
    deployEnv = incMsg['environment']

    ec2_exist = inst_exist_by_name( deployEnv+'_'+madeBy )

    if ec2_exist == deployEnv+'_'+madeBy:
        print('found existing vm called ', deployEnv+"_"+madeBy)
        return 2

    ec2_inst = boto3.client('ec2')

    try:
      ec2_kp = ec2_inst.create_key_pair( KeyName="devbot-key-"+deployEnv )
    except ClientError as e:
      if "InvalidKeyPair.Duplicate" in e.message:
        pass
      else:
        raise
    else:
      print(ec2_kp)

    subnets = ec2_inst.describe_subnets(
      Filters=[{
          'Name': 'tag:Name',
          'Values': [deployEnv+"-pub-sub"]
        }])

    secgroups = ec2_inst.describe_security_groups(
      Filters=[{
        'Name': 'group-name',
        'Values': [ 'allow-ssh-'+deployEnv ]
      }])

    latest_bionic_ami = find_latest_bionic_ami()

    custUserData = '''#!/bin/bash
git clone https://github.com/1adam/spinup.git
find /spinup/bashing -type f -name "*.sh" -exec chmod 755 '{}' \;
/spinup/bashing/devbot-%s.sh 2>&1 > /devbot-spinup.log\
''' % (deployEnv)

    resp = ec2_inst.run_instances(
        ImageId=latest_bionic_ami,
        InstanceType=instType,
        MaxCount=1,
        MinCount=1,
        KeyName='devbot-key-'+deployEnv,
        TagSpecifications=[{
            'ResourceType': 'instance',
            'Tags': [
                {"Key": "Name", "Value": deployEnv+"_"+madeBy },
                {"Key": "Creator", "Value": madeBy }
            ]
        }],
        SubnetId=subnets['Subnets'][0]['SubnetId'],
        SecurityGroupIds=[secgroups['SecurityGroups'][0]['GroupId']],
        UserData=custUserData
    )
    return 0

def proc_new_msg(event, context):

    retCodeMsgMap = [
      'OK',
      'NOT_OK',
      'OK_EXISTS'
    ]

    print(os.environ['BRAINBUCKET'])

    for msg in event['Records']:
        retCode = 0
        msg_body = json.loads(msg['body'])
        if verify_msg(msg_body) == False:
            print('Invalid Message')
            return {
                'statusCode': '400',
                'msg': 'Invalid Message'
            }
        print('---------------------------------------------')
        print('Received from ' + msg['eventSourceARN'] + ' ...')
        print('Creation initiated by ' + msg_body['creator_name'])
        print('Type of instance: ' + msg_body['type'])
        print('In environment: ' + msg_body['environment'])
        print('---------------------------------------------')

        retCode = parse_msg(msg_body)

        if retCode != 0:
          print('Error number {0}'.format(retCode) )
          return { 'statusCode': 200, 'msg': retCodeMsgMap[retCode] }

    finalResult = {
        'statusCode': 200,
        'msg': retCodeMsgMap[retCode]
    }
    print(finalResult)
    return finalResult
