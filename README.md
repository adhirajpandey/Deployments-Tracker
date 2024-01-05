# Deployments-Tracker
## Description
This applicaation helps in tracking uptime of your project deployments and regulary sends updates.
Uses Notion API to fetch deployment details and Discord API to send status notification to discord channel.

## Usage
0. Create a custom notion integration, [reference](https://developers.notion.com/docs/create-a-notion-integration)
1. Make a page in Notion which containes deployment details like : Project Name, URL to check, Current Status. Check attached Screenshot for reference.
2. Share this created page with your custom integration.
3. Clone the project to your local system using: `git clone https://github.com/adhirajpandey/Deployments-Tracker`
4. Create a virtual environment and activate it: `python -m venv venv && source venv/bin/activate`
5. Install the required dependencies: `pip install -r requirements.txt`
6. Rename `.env.example` to `.env` add your Notion API key, Project Deployments Page ID and discord webhook URL.
7. Schedule the script using cron, or you use Github Actions for same functionality.

## Note
Make sure you have done appropriate setup before deploying the script.
