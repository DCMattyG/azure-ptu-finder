import os
import re
import jwt
import time

import pandas as pd
import streamlit as st

from io import StringIO

from azure.identity import DefaultAzureCredential

from azure.storage.blob import BlobServiceClient

encoded_deploy_to_azure_url = "https://portal.azure.com/#create/Microsoft.Template/uri/https%3A%2F%2Fraw.githubusercontent.com%2FSeryioGonzalez%2Faz-openai-capacity-tracker%2Fmain%2Fazuredeploy.json"
region_data_start_column = 3

def get_credentials():
    credential = DefaultAzureCredential()

    return credential

def get_subscription_id(credential):
    credential_data = credential.get_token_info("https://management.azure.com/.default")
    token = credential_data.token
    alg = jwt.get_unverified_header(token)['alg']
    token_decode = jwt.decode(token, algorithms=[alg], options={ "verify_signature": False })
    resource_id = token_decode['xms_az_rid']
    sub_id = x = re.search("(?<=/subscriptions/)(.*)(?=/resourcegroups)", resource_id)

    return sub_id[0]

def read_ptu_data_from_blob(credential):
    stg_account = os.getenv("STORAGE_ACCOUNT")
    stg_container = os.getenv("STORAGE_CONTAINER")

    account_url = f"https://{stg_account}.blob.core.windows.net"

    # Create the BlobServiceClient object
    blob_service_client = BlobServiceClient(account_url, credential=credential)

    blob_client = blob_service_client.get_blob_client(container=stg_container, blob="ptu_data.csv")

    blob_download = blob_client.download_blob()
    blob_content = blob_download.readall().decode("utf-8")

    blob_creation_time = blob_client.get_blob_properties().creation_time
    blob_last_modified = blob_client.get_blob_properties().last_modified

    blob_obj = {
        "content": blob_content,
        "creation_time": blob_creation_time,
        "last_modified": blob_last_modified
    }

    return blob_obj

def highlight_capacity(row):
    # We need to return a list with the same length as the DataFrame row

    non_capacity_cell_style     = 'color: black; font-weight: bold; text-align: center; background-color: lightblue'    
    capacity_in_region_style    = 'color: green; font-weight: bold; text-align: center; background-color: lightgreen'
    no_capacity_in_region_style = 'color: red;   font-weight: bold; text-align: center; background-color: #F0A8BF'

    region_capacity_columns = row.index[region_data_start_column:]
    
    styles = []
    # Apply no style to the first two columns
    styles.append(non_capacity_cell_style)  # No style for 'Model Name'
    styles.append(non_capacity_cell_style)  # No style for 'Model Version'
    styles.append(non_capacity_cell_style)  # No style for 'Min PTUs Needed'

    # Apply conditional formatting to the remaining columns
    for region_capacity_column in region_capacity_columns:
        value = row[region_capacity_column]
        # Ensure the value is a string before checking for 'href'
        if isinstance(value, str) and 'href' in value:
            styles.append(capacity_in_region_style)
        else:
            styles.append(no_capacity_in_region_style)
    
    return styles

def reload_ptu_data():
    print("Refreshing...")

def make_clickable_if_sufficient_capacity(row):
    min_ptus_needed = row['Min PTUs Needed']
    for region in row.index[region_data_start_column:]:  # Assuming region columns start from the 4th column
        capacity = row[region]
        if capacity >= min_ptus_needed:
            row[region] = f'<a href="{encoded_deploy_to_azure_url}" target="_blank">{capacity}</a>'
        else:
            row[region] = capacity
    return row

def render_ptu_page():
    credential = get_credentials()
    subscription_id = get_subscription_id(credential)
    csv_obj = read_ptu_data_from_blob(credential)

    # Read CSV file
    file_creation_time_formatted = time.strftime('%Y-%m-%d %H:%M:%S %Z', time.localtime(csv_obj['last_modified'].timestamp()))

    df = pd.read_csv(StringIO(csv_obj['content']))
    df = df.reset_index(drop=True)

    # All regions in the DataFrame. These are dinamycally obtained
    all_regions = df.columns[3:].sort_values()

    # These regions have been offering capacity in the past
    region_subset_proposal = ['eastus', 'eastus2', 'swedencentral', 'uksouth', 'westus', 'westus3']

    # We just make sure classical AzOps regions are still offerinc capacity
    region_subset = [region for region in region_subset_proposal if region in all_regions]

    ### PAGE RENDERING
    st.title("Azure OpenAI PTU Capacity Finder")
    col1, col2 = st.columns([0.7, 0.3])
    with col1:
        st.markdown(f" **Subscription ID:** {subscription_id}")
        st.markdown(f" **Capacity data at:** {file_creation_time_formatted}")
    # with col2:
    #     refresh_capacity_button = st.button("Refresh capacity data")

    # if refresh_capacity_button:
    #     reload_ptu_data()
    #     st.rerun()

    # Multiselect widget for users to choose which regions to display
    selected_regions = st.multiselect('Select regions to display:', all_regions, default=region_subset)
    st.markdown("**If capacity available, click and deploy to Azure**")
    # Based on user selection, filter the DataFrame and apply conditional formatting
    df_filtered = df[['Model Name', 'Model Version', 'Min PTUs Needed'] + selected_regions]
    df_filtered = df_filtered.apply(make_clickable_if_sufficient_capacity, axis=1)
    df_styled = df_filtered.style.apply(highlight_capacity, axis=1)

    #st.table(df_filtered)
    st.markdown(df_styled.to_html(escape=False, index=False), unsafe_allow_html=True)

    # Add a button in order to refresh the page
    st.write("")

if __name__ == "__main__":
    render_ptu_page()
