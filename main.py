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


def create_subnet(args, vpc, client, cidr_block, is_public):
    subnet_type = 'public' if is_public else 'private'
    subnet = client.create_subnet(
        VpcId=vpc['VpcId'],
        CidrBlock=cidr_block,
        AvailabilityZone=args.availability_zone
    )
    client.create_tags(
        Resources=[subnet['SubnetId']],
        Tags=[
            {
                'Key': 'Name',
                'Value': f'{args.name}_{subnet_type}_subnet_{len(vpc["Subnets"]) + 1}'
            }
        ]
    )
    if is_public:
        client.modify_subnet_attribute(
            SubnetId=subnet['SubnetId'],
            MapPublicIpOnLaunch={'Value': True}
        )
    return subnet


def create_subnets(args, vpc, client):
    num_subnets = args.num_subnets
    if num_subnets <= 0 or num_subnets > 200:
        raise ValueError("Number of subnets should be between 1 and 200.")

    subnet_cidr_blocks = args.subnet_cidr_blocks
    if len(subnet_cidr_blocks) != num_subnets:
        raise ValueError("Number of subnet CIDR blocks should match the number of subnets.")

    subnets = []
    for i in range(num_subnets):
        is_public = (i < args.num_public_subnets)
        subnet_cidr_block = subnet_cidr_blocks[i]
        subnet = create_subnet(args, vpc, client, subnet_cidr_block, is_public)
        subnets.append(subnet)

    return subnets


def create_security_group(args, vpc, client):
    security_group = client.create_security_group(
        GroupName=args.security_group_name,
        Description=args.security_group_description,
        VpcId=vpc['VpcId']
    )

    client.authorize_security_group_ingress(
        GroupId=security_group['GroupId'],
        IpPermissions=[
            {
                'IpProtocol': 'tcp',
                'FromPort': 80,
                'ToPort': 80,
                'IpRanges': [{'CidrIp': '0.0.0.0/0'}]
            },
            {
                'IpProtocol': 'tcp',
                'FromPort': 22,
                'ToPort': 22,
                'IpRanges': [{'CidrIp': args.source_ip + '/32'}]
            }
        ]
    )

    return security_group


def create_key_pair(args, client):
    key_pair = client.create_key_pair(KeyName=args.key_pair_name)
    with open(args.key_pair_file, 'w') as f:
        f.write(key_pair['KeyMaterial'])

    return key_pair


def launch_instance(args, vpc, subnet, security_group, key_pair, client):
    instance = client.run_instances(
        ImageId=args.image_id,
        InstanceType=args.instance_type,
        MinCount=1,
        MaxCount=1,
        KeyName=args.key_pair_name,
        NetworkInterfaces=[
            {
                'SubnetId': subnet['SubnetId'],
                'DeviceIndex': 0,
                'AssociatePublicIpAddress': True,
                'Groups': [security_group['GroupId']]
            }
        ],
        BlockDeviceMappings=[
            {
                'DeviceName': '/dev/sda1',
                'Ebs': {
                    'VolumeSize': 10,
                    'VolumeType': 'gp2'
                }
            }
        ]
    )

    return instance['Instances'][0]


def main():
    ec2_client = init_aws_clients()
    parser = argparse.ArgumentParser()
    parser.add_argument('--vpc_id', help='The ID of the VPC.')
    parser.add_argument('--subnet_id', help='The ID of the subnet.')
    parser.add_argument('--security_group_name', help='The name of the security group.')
    parser.add_argument('--security_group_description', help='The description of the security group.')
    parser.add_argument('--source_ip', help='The source IP address for SSH access.')
    parser.add_argument('--key_pair_name', help='The name of the key pair.')
    parser.add_argument('--key_pair_file', help='The file path to save the key pair.')
    parser.add_argument('--image_id', help='The ID of the AMI.')
    parser.add_argument('--instance_type', help='The type of EC2 instance.')
    args = parser.parse_args()

    client = ec2_client['ec2']
    vpc = client.describe_vpcs(VpcIds=[args.vpc_id])['Vpcs'][0]
    subnet = client.describe_subnets(SubnetIds=[args.subnet_id])['Subnets'][0]

    security_group = create_security_group(args, vpc, client)
    key_pair = create_key_pair(args, client)
    instance = launch_instance(args, vpc, subnet, security_group, key_pair, client)

    print('Security group created: {}'.format(security_group['GroupId']))
    print('Key pair created: {}'.format(key_pair['KeyName']))
    print('Instance launched: {}'.format(instance['InstanceId']))


if __name__ == '__main__':
    main()