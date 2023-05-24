import argparse
import boto3
from utils.aws_init import init_aws_clients
def create_vpc(args, client):
    vpc = client.create_vpc(
        CidrBlock=args.cidr_block,
        TagSpecifications=[
            {
                'ResourceType': 'vpc',
                'Tags': [
                    {
                        'Key': 'Name',
                        'Value': args.name,
                    }
                ]
            }
        ]
    )
    return vpc

def create_igw(args, vpc, client):
    igw = client.create_internet_gateway()
    client.attach_internet_gateway(
        InternetGatewayId=igw['InternetGatewayId'],
        VpcId=vpc['VpcId']
    )
    return igw

def main():
    ec2_client = init_aws_clients()
    parser = argparse.ArgumentParser()
    parser.add_argument('--name', help='The name of the VPC.')
    parser.add_argument('--cidr_block', help='The CIDR block for the VPC.')
    args = parser.parse_args()

    vpc = create_vpc(args, ec2_client)
    igw = create_igw(args, vpc, ec2_client)

    print('VPC created: {}'.format(vpc['VpcId']))
    print('IGW created: {}'.format(igw['InternetGatewayId']))

if __name__ == '__main__':
    main()