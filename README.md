# Getting Started

1. Set environment variables with .env file emailed out
2. Launch application with `python3 main.py`
3. Until a server is set up to permanently host this, use `ngrok` to create an endpoint for Slack to communicate to this with
4. Update the "event subscriptions" https://api.slack.com/apps/A02Q4RR4G1H/event-subscriptions to point to this `ngrok` https address.

Until a server is created to host this, because Slack will need to go through Ngrok only one developer can actively test 
it at a time.