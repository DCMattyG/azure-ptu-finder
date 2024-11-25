import asyncio

import os
import re
import jwt
import pandas as pd

from collections import defaultdict

from azure.identity.aio import DefaultAzureCredential

from azure.mgmt.cognitiveservices.aio import CognitiveServicesManagementClient
from azure.storage.blob.aio import BlobServiceClient

from azure.core.rest import HttpRequest

from azure.core.pipeline import AsyncPipeline
from azure.core.pipeline.policies import UserAgentPolicy, AsyncRedirectPolicy, AsyncBearerTokenCredentialPolicy
from azure.core.pipeline.transport import AioHttpTransport

async def get_credentials():
    credential = DefaultAzureCredential()

    return credential

async def get_subscription_id(credential):
    credential_data = await credential.get_token_info("https://management.azure.com/.default")
    token = credential_data.token
    alg = jwt.get_unverified_header(token)['alg']
    token_decode = jwt.decode(token, algorithms=[alg], options={ "verify_signature": False })
    resource_id = token_decode['xms_az_rid']
    sub_id = x = re.search("(?<=/subscriptions/)(.*)(?=/resourcegroups)", resource_id)

    return sub_id[0]

async def get_locations(credentials, subscription_id):
    client = CognitiveServicesManagementClient(
        credential=credentials,
        subscription_id=subscription_id,
    )

    response = client.resource_skus.list()

    locations  = { x.locations[0].lower() async for x in response }

    await client.close()

    return locations

async def get_skus(credentials, subscription_id,  locations):
    client = CognitiveServicesManagementClient(
        credential=credentials,
        subscription_id=subscription_id,
    )

    models = []

    for loc in locations:
        response = client.models.list(
            location=loc,
        )

        model_data = []

        try:
            async for item in response:
                if item.kind == "OpenAI":
                    if any(x.name == "ProvisionedManaged" for x in item.model.skus):
                        ptu_sku_data = next((x for x in item.model.skus if x.name == "ProvisionedManaged"), None)

                        ptu_obj = {
                            "name": item.model.name,
                            "version": item.model.version,
                            "ptu_sku": ptu_sku_data.capacity.as_dict()
                        }

                        model_data.append(ptu_obj)

            models.append({
                "region": loc,
                "model_data": model_data
            })
        except:
            pass

    await client.close()

    return models

async def azure_api_request(credentials, url):
    scope = "https://management.azure.com/.default"

    request = HttpRequest("GET", url)
    policies = [
        UserAgentPolicy("myuseragent"),
        AsyncRedirectPolicy(),
        AsyncBearerTokenCredentialPolicy(credentials, scope)
    ]

    async with AsyncPipeline(AioHttpTransport(), policies=policies) as pipeline:
        response = await pipeline.run(request)

    return response.http_response.json()['value']

async def get_model_capacity(credentials, subscription_id, model_name, model_version):
    request_url=f"https://management.azure.com/subscriptions/{subscription_id}/providers/Microsoft.CognitiveServices/modelcapacities?api-version=2024-04-01-preview&modelformat=OpenAI&modelname={model_name}&modelversion={model_version}"

    capacity_obj = {
        # 'model_name': model_name,
        # 'model_version': model_version,
        'model_name_version': f"{model_name}_{model_version}",
        'capacity': [
            {
                'location': item['location'],
                'capacity': item['properties']['availableCapacity']
            }
            for item in await azure_api_request(credentials, request_url) if item['name'] == "ProvisionedManaged"
        ]
    }

    return capacity_obj

async def convert_data_model(credentials, subscription_id, REGIONAL_PTU_MODEL_INFO):
    # Dictionary to hold the aggregated results
    ptu_model_info_with_regions = defaultdict(lambda: {'regions': [], 'ptu_sku': {}})

    # Iterate over each region and its model data
    for region_data in REGIONAL_PTU_MODEL_INFO:
        region = region_data['region']
        for model in region_data['model_data']:
            key = (model['name'], model['version'])
            ptu_model_info_with_regions[key]['ptu_sku'] = model['ptu_sku']
            ptu_model_info_with_regions[key]['regions'].append(region)

    # Convert the dictionary to the desired list format
    ptu_capable_model_info = [
        {
            'model_name': name,
            'model_version': version,
            'min_ptus': details['ptu_sku']['minimum'],
        }
        for (name, version), details in ptu_model_info_with_regions.items()
    ]

    tasks = []

    for model_info in ptu_capable_model_info:
        model_name = model_info['model_name']
        model_version = model_info['model_version']

        r = tasks.append(get_model_capacity(credentials, subscription_id, model_name, model_version))

    regional_ptu_capacity_per_model_version = await asyncio.gather(*tasks)

    # Capacity before is 'capacity': [{'location': 'brazilsouth', 'capacity': 11}, {'location': 'eastus', 'capacity': 2},
    # We want a simpler structure with the location as the key and the capacity as the value
    for item in regional_ptu_capacity_per_model_version:
        item['capacity'] = {entry['location']: entry['capacity'] for entry in item['capacity']}

    # regional_ptu_capacity_per_model_version is a list of dictionaries with the following format:
    # {"gpt-35-turbo-1106": { "australiaeast": 0,...}, "gpt-35-turbo-0125": { "australiaeast": 0,...}}
    regional_ptu_capacity_per_model_version_DICT = {item['model_name_version']: item['capacity'] for item in regional_ptu_capacity_per_model_version}

    all_ptu_capable_regions = set()
    for subdict in regional_ptu_capacity_per_model_version_DICT.values():
        # Add the keys of each subdictionary to the set
        all_ptu_capable_regions.update(subdict.keys())

    # Sort the regions alphabetically
    all_ptu_capable_regions = sorted(all_ptu_capable_regions)

    model_ptu_availability = []
    # ptu_capable_model_info has the model name, version and the minimum PTU needed
    for model_index, model in enumerate(ptu_capable_model_info):
        model_availability = {}
        model_availability['model_name'] = model['model_name']
        model_availability['model_version'] = model['model_version']
        model_availability['min_ptus_needed'] = model['min_ptus']
        model_availability['regional_capacity'] = {}

        # This is the key we used in the batch call per model and version
        model_name_version = f"{model['model_name']}_{model['model_version']}"
        
        for region in all_ptu_capable_regions:
            # We need to initialize the dictionary for the model name and version
            if region in regional_ptu_capacity_per_model_version_DICT[model_name_version]:
                model_availability['regional_capacity'][region] = regional_ptu_capacity_per_model_version_DICT[model_name_version][region]
            else:
                model_availability['regional_capacity'][region] = 0
            #model_ptu_availability[model['model_name']][model['model_version']]['regional_capacity'] = {}
                
            #model_ptu_availability[model['model_name']][model['model_version']]['regional_capacity'][region] = regions_for_this_model[region]
        model_ptu_availability.append(model_availability)

    # model_ptu_availability is a dict {'gpt-35-turbo': {'1106': {'min_ptus_needed': 50, 'regional_capacity': {'australiaeast': 0, 'brazilsouth': 50, 'westus': 100, 'southcentralus': 100...

    # Prepare a list to hold the rows for the DataFrame
    rows = []

    # Iterate through the data to create rows for the DataFrame
    for entry in model_ptu_availability:
        # Create a row dictionary with model_name, model_version, min_ptus_needed
        row = {
            'Model Name': entry['model_name'],
            'Model Version': entry['model_version'],
            'Min PTUs Needed': entry['min_ptus_needed'],
        }
        # Add the entire regional_capacity dictionary as individual columns
        row.update(entry['regional_capacity'])
        
        # Append the row to the list of rows
        rows.append(row)
    # Create a DataFrame from the list of rows
    df = pd.DataFrame(rows)

    return df

async def export_to_csv(data):
    # Export DataFrame to CSV
    return data.to_csv(index=False)

async def save_to_blob(credentials, data):
    stg_account = os.getenv("STORAGE_ACCOUNT")
    stg_container = os.getenv("STORAGE_CONTAINER")

    account_url = f"https://{stg_account}.blob.core.windows.net"

    # Create the BlobServiceClient object
    blob_service_client = BlobServiceClient(account_url, credential=credentials)

    blob_client = blob_service_client.get_blob_client(container=stg_container, blob="ptu_data.csv")
    upload_data = data.encode('utf-8')

    await blob_client.upload_blob(upload_data, overwrite=True)

    await blob_service_client.close()

async def export_ptu_data():
    credentials = await get_credentials()
    subscription_id = await get_subscription_id(credentials)
    locations = await get_locations(credentials, subscription_id)
    skus = await get_skus(credentials, subscription_id, locations)
    data_model = await convert_data_model(credentials, subscription_id, skus)
    csv_data = await export_to_csv(data_model)

    await save_to_blob(credentials, csv_data)

    await credentials.close()

# async def main():
#     await export_ptu_data()

# if __name__ == "__main__":
#     asyncio.run(main())
