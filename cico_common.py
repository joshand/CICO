import os

meraki_api_token = os.getenv("MERAKI_API_TOKEN")
meraki_org = os.getenv("MERAKI_ORG")
spark_api_token = os.getenv("SPARK_API_TOKEN")


def meraki_support():
    if meraki_api_token and meraki_org:
        return True
    else:
        return False


def spark_call_support():
    if spark_api_token:
        return True
    else:
        return False