import os
import json
import spotipy.util


os.environ['SPOTIPY_CLIENT_ID'] = 'your_client_id'
os.environ['SPOTIPY_CLIENT_SECRET'] = 'your_client_secret'
os.environ['SPOTIPY_REDIRECT_URI'] = 'your_redirect_uri'
# Get the directory of the current script
current_dir = os.path.dirname(__file__)

# Define relative paths to JSON files
oas_path = os.path.join(current_dir, "configs", "oas", "spotify_oas.json")
config_path = os.path.join(current_dir,"configs", "spotify_config.json")

# Load the Spotify OAS JSON file to retrieve scopes
with open(oas_path) as f:
    raw_api_spec = json.load(f)

# Extract scopes and get the access token
scopes = list(raw_api_spec['components']['securitySchemes']['oauth_2_0']['flows']['authorizationCode']['scopes'].keys())
access_token = spotipy.util.prompt_for_user_token(username="me", scope=','.join(scopes))

# Load or initialize the configuration JSON file
if os.path.exists(config_path):
    with open(config_path, "r") as f:
        config_data = json.load(f)
else:
    config_data = {}

# Update the "token" field in the configuration data
config_data["token"] = access_token

# Write the updated configuration data back to the JSON file
with open(config_path, "w") as f:
    json.dump(config_data, f, indent=4)

print(f'Access Token saved to spotify_config.json')

