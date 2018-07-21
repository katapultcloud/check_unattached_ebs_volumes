# check_unattached_ebs_volumes
This script provides a pricing and capacity summary of unattached EBS volumes in all regions where EC2 service is available.

## How it works
The script fetches all regions with EC2 service enabled, then loops through all of them and fetches all unattached EBS volumes adds them into categories based on EBS type. Then the script fetches current EBS prices from AWS Pricing API for specified region and calculates EBS monthly expenditures for unattached EBS volumes per type. 

## Requirements
* boto3
* os
* argparse
* json

## Options
This is the help output from the script. 
```
$ ./check_unattached_ebs_volumes.py --help
usage: check_unattached_ebs_volumes.py [-h] [-p PROFILE] [-i AWS_ID]
                                       [-k AWS_SECRET_KEY] [-e] [-v] [-j]

Determine unused EC2 resources

optional arguments:
  -h, --help            show this help message and exit
  -p PROFILE, --profile PROFILE
                        aws profile to use, "default" profile is used if not
                        specified
  -i AWS_ID, --aws-id AWS_ID
                        aws access key id to use
  -k AWS_SECRET_KEY, --aws-secret-key AWS_SECRET_KEY
                        aws secret access key to use
  -e, --env             enable authentication using AWS_ACCESS_KEY_ID and
                        AWS_SECRET_ACCESS_KEY environmental vars
  -v, --verbose         display verbose output including pricing for each
                        storage type
  -j, --json            display json output including pricing for each storage
                        type
```

### Authentication
The script is able to utilise multiple authentication methods, first using profiles from `~/.aws/credentials` (preffered) and second using direct credentials as arguments to the script (not preffered). Third method is using environmental variables `AWS_ACCESS_KEY_ID` and `AWS_SECRET_ACCESS_KEY` (not preffered).

## Examples

Using the script in non-verbose mode with `default` profile.
```
$ ./check_unattached_ebs_volumes.py

EU (Ireland)
vol-02d1ed6d9f4a37cf3

Asia Pacific (Seoul)
vol-02f4546ce9c041e02
vol-0a26780232630b716

Canada (Central)
vol-04c69735fab373103

Total Price
-------------
$12.328

```

Using the script in json mode with different AWS profile. JSON output is parsed with `jq` for show.
```
$ ./check_unattached_ebs_volumes.py --json | jq .
{
  "regional_data": {
    "eu-west-1": {
      "friendly_name": "EU (Ireland)",
      "price_per_gb": {
        "standard": 0.055,
        "gp2": 0.11,
        "io1": 0.138,
        "st1": 0.05,
        "sc1": 0.028
      },
      "price_per_ebs": {
        "standard": 0,
        "gp2": 11,
        "io1": 0,
        "st1": 0,
        "sc1": 0
      },
      "size_per_ebs": {
        "gp2": 100,
        "standard": 0,
        "sc1": 0,
        "io1": 0,
        "st1": 0
      },
      "total_price": 11,
      "unused_volumes": [
        "vol-02d1ed6d9f4a37cf3"
      ]
    },
    "ap-northeast-2": {
      "friendly_name": "Asia Pacific (Seoul)",
      "price_per_gb": {
        "standard": 0.08,
        "gp2": 0.114,
        "io1": 0.1278,
        "st1": 0.051,
        "sc1": 0.029
      },
      "price_per_ebs": {
        "standard": 0,
        "gp2": 0.228,
        "io1": 0,
        "st1": 0,
        "sc1": 0
      },
      "size_per_ebs": {
        "gp2": 2,
        "standard": 0,
        "sc1": 0,
        "io1": 0,
        "st1": 0
      },
      "total_price": 0.228,
      "unused_volumes": [
        "vol-02f4546ce9c041e02",
        "vol-0a26780232630b716"
      ]
    },
    "ca-central-1": {
      "friendly_name": "Canada (Central)",
      "price_per_gb": {
        "standard": 0.055,
        "gp2": 0.11,
        "io1": 0.138,
        "st1": 0.05,
        "sc1": 0.028
      },
      "price_per_ebs": {
        "standard": 0,
        "gp2": 1.1,
        "io1": 0,
        "st1": 0,
        "sc1": 0
      },
      "size_per_ebs": {
        "gp2": 10,
        "standard": 0,
        "sc1": 0,
        "io1": 0,
        "st1": 0
      },
      "total_price": 1.1,
      "unused_volumes": [
        "vol-04c69735fab373103"
      ]
    }
  },
  "total_price": 12.328
}
```

Using the script in verbose mode with different AWS profile.
```
$ ./check_unattached_ebs_volumes.py --verbose

checking: Asia Pacific (Mumbai)
no unused volumes found...

checking: EU (Paris)
no unused volumes found...

checking: EU (London)
no unused volumes found...

checking: EU (Ireland)
found unused volumes!
vol-02d1ed6d9f4a37cf3
total price: $11.0

checking: Asia Pacific (Seoul)
found unused volumes!
vol-02f4546ce9c041e02
vol-0a26780232630b716
total price: $0.228

checking: Asia Pacific (Tokyo)
no unused volumes found...

checking: South America (Sao Paulo)
no unused volumes found...

checking: Canada (Central)
found unused volumes!
vol-04c69735fab373103
total price: $1.1

checking: Asia Pacific (Singapore)
no unused volumes found...

checking: Asia Pacific (Sydney)
no unused volumes found...

checking: EU (Frankfurt)
no unused volumes found...

checking: US East (N. Virginia)
no unused volumes found...

checking: US East (Ohio)
no unused volumes found...

checking: US West (N. California)
no unused volumes found...

checking: US West (Oregon)
no unused volumes found...

Total Price
-------------
$12.328
```

## Recommendations
Utilize profile or access keys with minimal privileges to AWS resources. Following priviliges are required to make this work.
```
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "ec2:DescribeVolumes",
                "ec2:DescribeRegions",
                "pricing:GetProducts"
            ],
            "Resource": "*"
        }
    ]
}
```

## Licence
GPL-v3

## Author Information
Stefan Roman (stefan.roman@katapult.cloud)
