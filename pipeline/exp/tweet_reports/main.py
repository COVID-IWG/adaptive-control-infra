from datetime import date

import tweepy
from google.cloud import secretmanager, storage

# cloud details
project_id = "adaptive-control"
bucket_name = "daily_pipeline"
bucket = storage.Client().bucket(bucket_name)
secrets = secretmanager.SecretManagerServiceClient()

tag_states = ["MH", "BR", "PB", "TN", "KL"]

state_code_lookup = {
    'AN'  : 'Andaman & Nicobar Islands',
    'AP'  : 'Andhra Pradesh',
    'AR'  : 'Arunachal Pradesh',
    'AS'  : 'Assam',
    'BR'  : 'Bihar',
    'CH'  : 'Chandigarh',
    'CT'  : 'Chhattisgarh',
    'DD'  : 'Daman & Diu', 
    'DDDN': 'Dadra & Nagar Haveli and Daman & Diu',
    'DL'  : 'Delhi',
    'DN'  : 'Dadra & Nagar Haveli',
    'GA'  : 'Goa',
    'GJ'  : 'Gujarat',
    'HP'  : 'Himachal Pradesh',
    'HR'  : 'Haryana',
    'JH'  : 'Jharkhand',
    'JK'  : 'Jammu & Kashmir',
    'KA'  : 'Karnataka',
    'KL'  : 'Kerala',
    'LA'  : 'Ladakh',
    'LD'  : 'Lakshadweep',
    'MH'  : 'Maharashtra',
    'ML'  : 'Meghalaya',
    'MN'  : 'Manipur',
    'MP'  : 'Madhya Pradesh',
    'MZ'  : 'Mizoram',
    'NL'  : 'Nagaland',
    'OR'  : 'Odisha',
    'PB'  : 'Punjab',
    'PY'  : 'Puducherry',
    'RJ'  : 'Rajasthan',
    'SK'  : 'Sikkim',
    'TG'  : 'Telangana',
    'TN'  : 'Tamil Nadu',
    'TR'  : 'Tripura',
    'TT'  : 'India',
    'UN'  : 'State Unassigned',
    'UP'  : 'Uttar Pradesh',
    'UT'  : 'Uttarakhand',
    'WB'  : 'West Bengal',
}
#  secret names
secret_names = ["COVID_IWG_twitter_API_key", "COVID_IWG_twitter_secret_key", "Twitter_API_access_token", "Twitter_API_access_secret"]

def get(request, key):
    request_json = request.get_json()
    if request.args and key in request.args:
        return request.args.get(key)
    elif request_json and key in request_json:
        return request_json[key]
    else:
        return None

def get_twitter_client():
    credentials = { 
        secret_name: secrets.access_secret_version({
            "name": f"projects/{project_id}/secrets/{secret_name}/versions/latest"}
        ).payload.data.decode("UTF-8")
        for secret_name in secret_names
    }
    auth = tweepy.OAuthHandler(credentials["COVID_IWG_twitter_API_key"], credentials["COVID_IWG_twitter_secret_key"])
    auth.set_access_token(credentials["Twitter_API_access_token"], credentials["Twitter_API_access_secret"])
    api = tweepy.API(auth, wait_on_rate_limit = True, wait_on_rate_limit_notify = True)
    api.verify_credentials()
    return api

def tweet_report(request):
    state_code = get(request, "state_code")
    state = state_code_lookup[state_code]
    print(f"Tweeting report for {state_code} ({state}).")

    bucket.blob(f"pipeline/rpt/{state_code}_Rt_timeseries.png").download_to_filename(f"/tmp/{state_code}_Rt_timeseries.png")
    bucket.blob(f"pipeline/rpt/{state_code}_Rt_choropleth.png").download_to_filename(f"/tmp/{state_code}_Rt_choropleth.png")
    bucket.blob(f"pipeline/rpt/{state_code}_Rt_top10.png")     .download_to_filename(f"/tmp/{state_code}_Rt_top10.png")
    
    hashtag = f"#COVIDmetrics{state_code}"
    tag     = "@anup_malani" if state_code in tag_states else ""

    twitter = get_twitter_client()
    media_ids = [twitter.media_upload(_).media_id for _ in (f"/tmp/{state_code}_Rt_timeseries.png", f"/tmp/{state_code}_Rt_choropleth.png", f"/tmp/{state_code}_Rt_top10.png")]
    today = date.today().strftime("%d %b %Y")
    twitter.update_status(
        status    = f"Rt report for {state}, {today} #covid #Rt #india {hashtag} {tag}", 
        media_ids = media_ids
    )
    return "OK!"
