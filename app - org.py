from flask import Flask, redirect, url_for, session, request
from flask import render_template
import requests
import os
from functools import wraps

app = Flask(__name__)
app.secret_key = 'your_secret_key'  # Make sure to change this

# Dictionary to translate state and city names to Korean
state_translation = {
    "Seoul": "서울",
    "Gyeonggi-do": "경기도",
    "Busan": "부산",
    "Incheon": "인천",
    # Add more as needed
}

city_translation = {
    "Seoul": "서울",
    "Suwon": "수원",
    "Busan": "부산",
    "Incheon": "인천",
    # Add more as needed
    "Gwangju-si": "광주시",
    "Jongno-gu": "종로구", 
    "Seongnam Si": "성남시",
    "Seongnam-si": "성남시",
    "Yangpyeong": "양평시"
}

# Strava API credentials
CLIENT_ID = '138076'
CLIENT_SECRET = 'b33a4f38208e8ec3fed86116148050033b9ab55d'
REDIRECT_URI = 'http://localhost:5000/authorization'

# Strava OAuth URL
auth_url = f'https://www.strava.com/oauth/authorize?client_id={CLIENT_ID}&response_type=code&redirect_uri={REDIRECT_URI}&approval_prompt=force&scope=activity:read_all'

# Authentication check decorator
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'access_token' not in session:  # Check if user is authenticated
            #return redirect(url_for('/'))  # Redirect to the login page if not authenticated
            return redirect(url_for('home'))
        return f(*args, **kwargs)
    return decorated_function

@app.route('/')
def home():
    return f'<a href="{auth_url}">Connect with Strava</a>'

@app.route('/authorization')
def authorization():
    # Get authorization code from Strava
    code = request.args.get('code')
    # Exchange authorization code for access token
    token_response = requests.post(
        'https://www.strava.com/oauth/token',
        data={
            'client_id': CLIENT_ID,
            'client_secret': CLIENT_SECRET,
            'code': code,
            'grant_type': 'authorization_code'
        }
    )
    token_json = token_response.json()
    session['access_token'] = token_json['access_token']
    session['athlete_id'] = token_json['athlete']['id']
    return redirect(url_for('activities'))

#@app.route('/activities')
#def activities():
#    # Use the access token to get activities
#    access_token = session.get('access_token')
#    if not access_token:
#        return redirect(url_for('home'))
#
#    # Get activities from Strava API
#    response = requests.get(
#        'https://www.strava.com/api/v3/athlete/activities',
#        headers={'Authorization': f'Bearer {access_token}'}
#    )
#    activities = response.json()
#
#    # Display activities
#    return f'<h1>My Activities</h1>' + '<br>'.join([f"Distance: {activity['distance']} meters" for activity in activities])

@app.route('/activities')
@login_required
def activities():
    access_token = session.get('access_token')
    if not access_token:
        return redirect(url_for('home'))

    # Get activities from Strava API
    response = requests.get(
        'https://www.strava.com/api/v3/athlete/activities',
        headers={'Authorization': f'Bearer {access_token}'}
    )
    activities = response.json()

    # Pass activities to the template
    return render_template('activities.html', activities=activities)
@app.route('/profile')
@login_required
def profile():
    access_token = session.get('access_token')
    if not access_token:
        return redirect(url_for('home'))

    # Fetch athlete profile information
    response = requests.get(
        'https://www.strava.com/api/v3/athlete',
        headers={'Authorization': f'Bearer {access_token}'}
    )
    athlete = response.json()

    return render_template('profile.html', athlete=athlete)

@app.route('/segments')
@login_required
def segments():
    access_token = session.get('access_token')
    if not access_token:
        return redirect(url_for('home'))

    # Fetch starred segments from Strava API
    response = requests.get(
        'https://www.strava.com/api/v3/segments/starred',
        headers={'Authorization': f'Bearer {access_token}'}
    )
    segments = response.json()

    # Apply translation to state and city of each segment
    for segment in segments:
        segment['state'] = state_translation.get(segment.get('state', ''), segment.get('state', ''))
        segment['city'] = city_translation.get(segment.get('city', ''), segment.get('city', ''))

    # Extract unique states and cities from translated values
    states = sorted({segment.get('state', '') for segment in segments if segment.get('state')})
    cities = sorted({segment.get('city', '') for segment in segments if segment.get('city')})

    print(states)
    print(cities)

    # Filtering logic
    name_filter = request.args.get('name')
    min_distance = request.args.get('min_distance')
    min_elevation = request.args.get('min_elevation')
    state_filter = request.args.get('state')
    city_filter = request.args.get('city')

    if name_filter:
        segments = [s for s in segments if name_filter.lower() in s['name'].lower()]
    if min_distance:
        segments = [s for s in segments if s['distance'] >= int(min_distance)]
    if min_elevation:
        segments = [s for s in segments if s['total_elevation_gain'] >= int(min_elevation)]
    if state_filter and state_filter != 'all':
        #for s in segments:
        #    if s.get('state'):
        #        if s.get('state', '').lower() == state_filter.lower():
        #            segments.append(s)
        #segments = [s for s in segments if s.get('state', '').lower() == state_filter.lower() if s.get('state')]
        segments = [s for s in segments if s.get('state', '') == state_filter]
    if city_filter and city_filter != 'all':
        #for s in segments:
        #    if s.get('city'):
        #        if s.get('city', '').lower() == state_filter.lower():
        #            segments.append(s)
        #segments = [s for s in segments if s.get('city', '').lower() == city_filter.lower() if s.get('city')]
        segments = [s for s in segments if s.get('city', '') == city_filter]

    # Calculate total elevation gain
    for segment in segments:
        total_elevation_gain = segment['elevation_high'] - segment['elevation_low']
        segment['total_elevation_gain'] = total_elevation_gain

    # Fetch additional details for each segment (optional, to show more info)
    for segment in segments:
        detail_response = requests.get(
            f'https://www.strava.com/api/v3/segments/{segment["id"]}',
            headers={'Authorization': f'Bearer {access_token}'}
        )
        segment['details'] = detail_response.json()

    return render_template('segments.html', segments=segments, states=states, cities=cities)
""" def segments():
    access_token = session.get('access_token')
    if not access_token:
        return redirect(url_for('home'))

    # Fetch starred segments from Strava API
    response = requests.get(
        'https://www.strava.com/api/v3/segments/starred',
        headers={'Authorization': f'Bearer {access_token}'}
    )
    segments = response.json()

    # Apply translation to state and city of each segment
    for segment in segments:
        segment['state'] = state_translation.get(segment.get('state', ''), segment.get('state',''))
        segment['city'] = city_translation.get(segment.get('city', ''), segment.get('city',''))

    # Extract unique states and cities from translated values
    states = sorted({segment.get('state', '') for segment in segments if segment.get('state')})
    cities = sorted({segment.get('city', '') for segment in segments if segment.get('city')})
    
    print(states)
    print(cities)

     # Filtering logic
    name_filter = request.args.get('name')
    min_distance = request.args.get('min_distance')
    min_elevation = request.args.get('min_elevation')
    state_filter = request.args.get('state')
    city_filter = request.args.get('city')

    if name_filter:
        segments = [s for s in segments if name_filter.lower() in s['name'].lower()]
    if min_distance:
        segments = [s for s in segments if s['distance'] >= int(min_distance)]
    if min_elevation:
        segments = [s for s in segments if s['total_elevation_gain'] >= int(min_elevation)]
    if state_filter and state_filter != 'all':
        segments = [s for s in segments if s.get('state', '').lower() == state_filter.lower() if s.get('state')]
    if city_filter and city_filter != 'all':
        segments = [s for s in segments if s.get('city', '').lower() == city_filter.lower() if s.get('city')]

    #j = len(segments)
    #for i in range(j):
        #print(segments[i])
    #    total_elevation_gain = segments[i]['elevation_high'] - segments[i]['elevation_low']
    #    segments[i]['total_elevation_gain']= total_elevation_gain

    # Calculate total elevation gain
    for segment in segments:
        total_elevation_gain = segment['elevation_high'] - segment['elevation_low']
        segment['total_elevation_gain'] = total_elevation_gain

    # Fetch additional details for each segment (optional, to show more info)
    for segment in segments:
        detail_response = requests.get(
            f'https://www.strava.com/api/v3/segments/{segment["id"]}',
            headers={'Authorization': f'Bearer {access_token}'}
        )
        segment['details'] = detail_response.json()

    #total_elevation_gain = segments[0]['elevation_high'] - segments[0]['elevation_low']
    #print(total_elevation_gain)
    #segments[0]['total_elevation_gain']= total_elevation_gain
    return render_template('segments.html', segments=segments, states=states, cities=cities) """

@app.route('/stats')
@login_required
def stats():
    access_token = session.get('access_token')
    if not access_token:
        return redirect(url_for('home'))

    # Fetch athlete statistics from Strava API
    athlete_id = session.get('athlete_id')
    #print(athlete_id)
    response = requests.get(
        f'https://www.strava.com/api/v3/athletes/{athlete_id}/stats',
        headers={'Authorization': f'Bearer {access_token}'}
    )
    stats = response.json()
    #print(stats)

    return render_template('stats.html', stats=stats)

if __name__ == '__main__':
    app.run(debug=True)