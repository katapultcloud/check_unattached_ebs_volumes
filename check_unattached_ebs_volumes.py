#!/usr/bin/env python3

# -*- coding: utf-8 -*-
# Copyright: (c) 2018, Stefan Roman <stefan.roman@katapult.cloud>
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

# import modules
import boto3
import os
import argparse
import json

# adding optional arguments
def resolve_arguments():
    aws_id = None
    aws_secret_key = None
    parser = argparse.ArgumentParser(
        description='Determine unused EC2 resources')
    # support for authentication using custom or default AWS profile
    parser.add_argument(
        '-p',
        '--profile',
        default='default',
        help='aws profile to use, "default" profile is used if not specified')
    # support for authentication using AWS access id and secret access key
    parser.add_argument(
        '-i', '--aws-id', default=None, help='aws access key id to use')
    parser.add_argument(
        '-k',
        '--aws-secret-key',
        default=None,
        help='aws secret access key to use')
    # support for authentication using environmental variables
    parser.add_argument(
        '-e',
        '--env',
        action='store_true',
        default=False,
        help='enable authentication using AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY environmental vars')
    # verbosity switch, by default this is turned off
    parser.add_argument(
        '-v',
        '--verbose',
        action='store_true',
        default=False,
        help='display verbose output including pricing for each storage type')
    # json switch, by default this is turned off
    parser.add_argument(
        '-j',
        '--json',
        action='store_true',
        default=False,
        help='display json output including pricing for each storage type')

    arguments = parser.parse_args()

    # if login from environmental variables was specified
    if arguments.env:
        aws_id = os.getenv('AWS_ACCESS_KEY_ID', None)
        aws_secret_key = os.getenv('AWS_SECRET_ACCESS_KEY', None)
    else:
        aws_id = arguments.aws_id
        aws_secret_key = arguments.aws_secret_key
    
    # adding mutual inclusivity for awd-id and secret-key-key
    if aws_id and not aws_secret_key:
        parser.error('aws-id requires aws-secret-key')
    elif not aws_id and aws_secret_key:
        parser.error('aws-secret-key requires aws-id')

    # build credentials dict
    credentials = {
        'profile': arguments.profile,
        'aws_access_key_id': aws_id,
        'aws_secret_access_key': aws_secret_key
    }

    json_mode = arguments.json
    verbose_mode = arguments.verbose

    return credentials, json_mode, verbose_mode


# get all AWS regions where EC2 service exists
def fetch_regions(creds):
    region_list = []
    # if credentials were specified with -k and -i option use them to authenticate
    if creds['aws_access_key_id'] and creds['aws_secret_access_key']:
        session = boto3.session.Session(
            aws_access_key_id=creds['aws_access_key_id'],
            aws_secret_access_key=creds['aws_secret_access_key'])
    # if not use specified profile or use "default" if not declared
    else:
        session = boto3.session.Session(profile_name=creds['profile'])

    ec2 = session.client('ec2')
    region_dict = ec2.describe_regions()
    for region_item in region_dict['Regions']:
        region_list.append(region_item['RegionName'])
    return region_list


def authenticate(region, creds):
    aws_pricing_region = "us-east-1"
    # if credentials were specified with -k and -i option use them to authenticate
    if creds['aws_access_key_id'] and creds['aws_secret_access_key']:
        session = boto3.session.Session(
            aws_access_key_id=creds['aws_access_key_id'],
            aws_secret_access_key=creds['aws_secret_access_key'])
    # if not use specified profile or use "default" if not declared
    else:
        session = boto3.session.Session(profile_name=creds['profile'])
    # return session for fetching EBS volumes from AWS API
    ebs_auth = session.resource('ec2', region_name=region)
    pricing_auth = session.client('pricing', region_name=aws_pricing_region)
    return ebs_auth, pricing_auth



# obtain all EBS volumes from a particular region form AWS API
def get_all_volumes(auth):
    # fetch all EBS volumes from AWS API
    ebs_volumes = auth.volumes.all()
    return ebs_volumes


# extract unused EBS volumes and add them up based on EBS type
def determine_unused_ebs(ebs_volumes):
    final_sizes = {"gp2": 0, "standard": 0, "sc1": 0, "io1": 0, "st1": 0}
    ebs_list = []
    unused_ebs = []
    # extract type, size, id and attachments from each EBS volume
    for volume in ebs_volumes:
        ebs_list.append({
            'id': volume.id,
            'attachments': volume.attachments,
            'type': volume.volume_type,
            'size': volume.size
        })
    # determine whether EBS has an attachment
    # if not it's added to the list and it's size added to the dict based on EBS type
    for ebs_volume in ebs_list:
        if ebs_volume['attachments'] == []:
            unused_ebs.append(ebs_volume['id'])
            final_sizes[ebs_volume[
                'type']] = final_sizes[ebs_volume['type']] + ebs_volume['size']
    return unused_ebs, final_sizes


def count_unused_ebs_sizes(unused_ebs_from_regions):
    final_sizes = {"gp2": 0, "standard": 0, "sc1": 0, "io1": 0, "st1": 0}
    for ebs_type_dict in unused_ebs_from_regions:
        for ebs_type in ebs_type_dict:
            final_sizes[ebs_type] = ebs_type_dict[ebs_type] + final_sizes[ebs_type]
    return final_sizes


# resolve a region to verbose region name (this is due to pricing API not using region codes e.g. eu-west-1)
def resolve_region(region):
    aws_region_map = {
        'ca-central-1': 'Canada (Central)',
        'ap-northeast-3': 'Asia Pacific (Osaka-Local)',
        'us-east-1': 'US East (N. Virginia)',
        'ap-northeast-2': 'Asia Pacific (Seoul)',
        'us-gov-west-1': 'AWS GovCloud (US)',
        'us-east-2': 'US East (Ohio)',
        'ap-northeast-1': 'Asia Pacific (Tokyo)',
        'ap-south-1': 'Asia Pacific (Mumbai)',
        'ap-southeast-2': 'Asia Pacific (Sydney)',
        'ap-southeast-1': 'Asia Pacific (Singapore)',
        'sa-east-1': 'South America (Sao Paulo)',
        'us-west-2': 'US West (Oregon)',
        'eu-west-1': 'EU (Ireland)',
        'eu-west-3': 'EU (Paris)',
        'eu-west-2': 'EU (London)',
        'us-west-1': 'US West (N. California)',
        'eu-central-1': 'EU (Frankfurt)'
    }
    
    resolved_region = aws_region_map[region]
    return resolved_region


# pull prices of EBS volume types relevant to the region specified 
def build_price_dict(auth, region):
    # EBS code to name is added since "pricing" endpoint does not understand EBS codes (same situation as regions)
    ebs_name_map = {
        'standard': 'Magnetic',
        'gp2': 'General Purpose',
        'io1': 'Provisioned IOPS',
        'st1': 'Throughput Optimized HDD',
        'sc1': 'Cold HDD'
    }

    price_dict = ebs_name_map

    # query get_products with a filter to loops through all EBS types in one specified region
    for ebs_code in ebs_name_map:
        response = auth.get_products(
            ServiceCode='AmazonEC2',
            Filters=[{
                'Type': 'TERM_MATCH',
                'Field': 'volumeType',
                'Value': ebs_name_map[ebs_code]
            }, 
            {
                'Type': 'TERM_MATCH',
                'Field': 'location',
                'Value': region
            }])

        # magic to get through complex dict returned from the get_products api to get to the price value
        for result in response['PriceList']:
            json_result = json.loads(result)
            for json_result_level_1 in json_result['terms'][
                    'OnDemand'].values():
                for json_result_level_2 in json_result_level_1[
                        'priceDimensions'].values():
                    for price_value in json_result_level_2[
                            'pricePerUnit'].values():
                        continue
        # fill in the dictionary with prices pulled from the get_products api
        price_dict[ebs_code] = float(price_value)
    return price_dict


# function to calculate prices of each individual EBS type based on price dictionary returned from get_products api
def calculate_prices(size_dict, price_dict):
    price_per_ebs_type = {}
    for ebs_type in size_dict:
        price_per_ebs_type[ebs_type] = size_dict[ebs_type] * price_dict[ebs_type]
    return price_per_ebs_type


# small function to add up all EBS prices together to create a total
def calculate_total_ebs_price(price_dict):
    total_price_per_region = 0
    for price in price_dict.values():
        total_price_per_region = total_price_per_region + price
    return total_price_per_region


# add up total price from every region
def count_all_prices_per_region(region_prices_list):
    total_price = 0
    if not region_prices_list == []:
        total_price = sum(number for number in region_prices_list)
        return total_price
    else:
        return False


def main():
    # get credentials, region and verbose mode setting from arguments
    credentials, json_mode, verbose_mode = resolve_arguments()
    prices_and_sizes_dict = {}
    prices_and_sizes_dict['regional_data'] = {}
    total_price_list = []
    all_regions = fetch_regions(credentials)
    
    # loop through all regions where EC2 service is available
    for region in all_regions:
        # authenticate against AWS API
        ebs_auth, price_auth = authenticate(region, credentials)
        # get all EBS volumes for particular region
        all_ebs_volumes = get_all_volumes(ebs_auth)
        # extract and add up all unused EBS volume sizes based on EBS volume type
        unused_ebs_volumes, unused_sizes = determine_unused_ebs(all_ebs_volumes)
        # adding verbosity when verbose mode is enabled
        if verbose_mode:
            print('\nchecking:', resolve_region(region))
        # if there are unused ebs volumes in the region
        if not unused_ebs_volumes == []:
            # adding verbosity when verbose mode is enabled
            if verbose_mode:
                print('found unused volumes!')
                for volume_id in unused_ebs_volumes:
                    print(volume_id)
            # disabling output when json mode is enabled as it should return just one json document 
            elif not json_mode:
                print('\n' + resolve_region(region))
                for volume_id in unused_ebs_volumes:
                    print(volume_id)

            # fetch ebs prices for a particular region
            pricing_dict = build_price_dict(price_auth, resolve_region(region))
            # calculate prices for each EBS type for a particular region
            price_per_ebs_type = calculate_prices(pricing_dict, unused_sizes)
            # count total price of unused ebs volumes in a region
            total_price_per_region = calculate_total_ebs_price(price_per_ebs_type)
            # add prices for each region into a list
            total_price_list.append(total_price_per_region)
            # build a json document that is output in json mode
            prices_and_sizes_dict['regional_data'][region] = {
                'friendly_name': resolve_region(region),
                'price_per_gb': pricing_dict,
                'price_per_ebs': price_per_ebs_type,
                'size_per_ebs': unused_sizes,
                'total_price': total_price_per_region,
                'unused_volumes': unused_ebs_volumes
            }
            # adding verbosity when verbose mode is enabled
            if verbose_mode:
                print('total price: $' + str(total_price_per_region))
        else:
            # adding verbosity when verbose mode is enabled
            if verbose_mode:
                print('no unused volumes found...')
    # calculate total price of unused EBS volumes in all regions # returns False when total_price_list list is empty
    total_price = count_all_prices_per_region(total_price_list)

    if total_price:
        # if json mode is enabled print built json document
        if json_mode:
            prices_and_sizes_dict['total_price'] = total_price
            print(json.dumps(prices_and_sizes_dict))
        else:
            print('\nTotal Price')
            print('-------------')
            print('$' + str(total_price))
    # if total_price is False print message
    else:
        print('no unused EBS volumes found')


if __name__ == "__main__":
    main()
