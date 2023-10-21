import requests
import json
import time
import os
from datetime import datetime
import pytz
import logging
from dotenv import load_dotenv

load_dotenv()

NOTION_API_TOKEN = os.getenv("NOTION_API_TOKEN")
DEPLOYMENT_DB_ID = os.getenv("DEPLOYMENT_DB_ID")
DISCORD_WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL")

DEPLOYMENT_DB_OUTPUT_DATA_FILE = "deployment_db_raw_data.json"


def get_current_datetime():
    ist = pytz.timezone('Asia/Calcutta')
    current_datetime = datetime.now(ist)

    formatted_datetime = current_datetime.strftime('%d-%m-%Y %H:%M:%S')

    return formatted_datetime


def send_message_to_discord(username, message):
    try:
        headers = {
            "Content-Type": "application/json"
        }
        payload = {
            "content": message,
            "username": username,
        }

        response = requests.post(url=DISCORD_WEBHOOK_URL, data=json.dumps(payload), headers=headers)

        return response.text

    except Exception as e:
        logging.error(e)
        return None


def write_data_to_json_file(data, filename):
    with open(filename, 'a', encoding='utf8') as file:
        json.dump(data, file, indent=4)


def read_notion_deployments_database(database_id):
    try:
        headers = {
            "Authorization": "Bearer " + NOTION_API_TOKEN,
            "Content-Type": "application/json",
            "Notion-Version": "2022-02-22"
        }

        api_url = f"https://api.notion.com/v1/databases/{database_id}/query"
        res = requests.request("POST", api_url, headers=headers)

        response_data = res.json()

        return response_data

    except Exception as e:
        logging.error(e)
        return None


def extract_data_from_notion_response(response_data):
    results = response_data["results"]

    extracted_data = []

    for result in results:
        properties = result["properties"]
        extracted_data.append({
            "name": properties["Project Name"]["title"][0]["plain_text"],
            "label": properties["Label"]["status"]["name"],
            "link": properties["Link"]["rich_text"][0]["plain_text"],
            "notion_page_id": get_pageid_from_notion_url(result["url"]),
        })

    return extracted_data


def check_project_deployment_status(project_link, max_retries=3):
    try:
        for i in range(max_retries):
            response = requests.get(project_link, allow_redirects=True)
            if response.status_code == 200:
                return True
            else:
                time.sleep(2)
        return False

    except Exception as e:
        logging.error(e)
        return False


def get_deployment_status(deployment_db):
    deployment_status_data_list = []

    for entry in deployment_db:
        try:
            deployment_status = {
                "Project Name": entry["name"],
                "Status": check_project_deployment_status(entry["link"], max_retries=3)
            }
            deployment_status_data_list.append(deployment_status)

        except Exception as e:
            logging.error(e)
            pass

    return deployment_status_data_list


def get_discord_message_payload(deployment_status_data):
    payload = ""
    payload += f"Checked at: {get_current_datetime()}\n"

    for entry in deployment_status_data:
        payload += f"{entry['Project Name']}: {'✅' if entry['Status'] else '❌'}\n"

    return payload


def set_logging_config():
    logging.basicConfig(filename='deployment-tracker.log', level=logging.INFO,
                        format='%(asctime)s:%(levelname)s:%(message)s')


def get_old_new_status(deployments_db_data, deployment_statuses_data):
    for status in deployment_statuses_data:
        if status["Status"]:
            status["Status"] = "Healthy"
        else:
            status["Status"] = "Down"

    status_dict = {status["Project Name"]: status for status in deployment_statuses_data}

    changes = []

    for db_data in deployments_db_data:
        corresponding_status = status_dict.get(db_data["name"])

        if corresponding_status:
            changes.append({
                "name": db_data["name"],
                "old_status": db_data["label"],
                "new_status": corresponding_status["Status"],
                "notion_page_id": db_data["notion_page_id"],
            })

    return changes


def update_notion_deployments_database(deployments_data, deployments_data_new):
    final_statuses_data = get_old_new_status(deployments_data, deployments_data_new)

    for entry in final_statuses_data:
        if entry["old_status"] != entry["new_status"]:
            update_status_in_project_page(entry["notion_page_id"], entry["new_status"])
            logging.info(f"Updated {entry['name']} from {entry['old_status']} to {entry['new_status']}")
        else:
            logging.info(f"No Change in {entry['name']}")


def update_status_in_project_page(page_id, new_status):
    try:
        headers = {
            "Authorization": "Bearer " + NOTION_API_TOKEN,
            "Content-Type": "application/json",
            "Notion-Version": "2022-02-22"
        }

        update_data_payload = {
            "properties": {
                "Label": {
                    "status": {
                        "name": new_status
                    }
                }
            }
        }

        api_url = f"https://api.notion.com/v1/pages/{page_id}"

        response = requests.request("PATCH", api_url, headers=headers, data=json.dumps(update_data_payload))

        return response.status_code

    except Exception as e:
        logging.error(e)
        return None


def get_pageid_from_notion_url(notion_url):
    return notion_url.split("-")[-1]


if __name__ == "__main__":
    try:
        set_logging_config()

        # Getting Deployment DB Data
        deployment_db_raw_data = read_notion_deployments_database(DEPLOYMENT_DB_ID)
        deployment_db_data = extract_data_from_notion_response(deployment_db_raw_data)
        logging.info(f"Deployment DB Data: {deployment_db_data}")

        # Checking Deployment Health Status for each entry in DB
        deployment_statuses = get_deployment_status(deployment_db_data)
        logging.info(f"Deployment Statuses: {deployment_statuses}")

        # Send Status Report/Alert to Discord
        message_payload = get_discord_message_payload(deployment_statuses)
        send_message_to_discord("Deployments Tracker", message_payload)
        logging.info(f"Message Payload: {message_payload}")

        # Update Notion Database
        update_notion_deployments_database(deployment_db_data, deployment_statuses)

    except Exception as e:
        logging.error(e)
        ERROR_MESSAGE = f"Error occurred while checking deployments at {get_current_datetime()}\n\n{e}"
        send_message_to_discord("Deployment Monitoring Alert", ERROR_MESSAGE)
