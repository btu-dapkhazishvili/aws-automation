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


def main():
    ec2_client = init_aws_clients()
    parser = argparse.ArgumentParser()
    parser.add_argument('--name', help='The name of the VPC.')
    parser.add_argument('--cidr_block', help='The CIDR block for the VPC.')
    parser.add_argument('--num_subnets', type=int, help='The number of subnets to create.')
    parser.add_argument('--num_public_subnets', type=int, help='The number of public subnets.')
    parser.add_argument('--subnet_cidr_blocks', nargs='+', help='The CIDR blocks for the subnets.')
    parser.add_argument('--availability_zone', help='The availability zone for the subnets.')
    args = parser.parse_args()

    vpc = create_vpc(args, ec2_client)
    igw = create_igw(args, vpc, ec2_client)
    subnets = create_subnets(args, vpc, ec2_client)

    print('VPC created: {}'.format(vpc['VpcId']))
    print('IGW created: {}'.format(igw['InternetGatewayId']))
    for i, subnet in enumerate(subnets):
        subnet_type = 'public' if i < args.num_public_subnets else 'private'
        print(f'{subnet_type} subnet created: {subnet["SubnetId"]}')


if __name__ == '__main__':
    main()