# 97.3 RADIO STATION

from bs4 import BeautifulSoup
import requests
import json
import urllib.parse
import re
import ast
import time
import sys

import pickle
import os.path
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.http import MediaFileUpload


class RadioFetcher:

    def __init__(self):
        self.api_token = ""  # generated using the refresh function
        self.refresh_token = "REDACTED"  # allow access to make new api tokens
        self.base_64 = "REDACTED"  # encoded credentials of clientID:clientSecret
        self.playlist_id = "7HaIcQA6sZjL7xGaxsyNP2"
        self.radio_site_url = "https://www.radio.com/radioalice/listen"
        try:  # create a dictionary to hold all song names as keys and song artists as values in playlist
            with open('saved_songs.txt', 'r') as f:  # see if there is a saved version of the songs_dict
                self.songs_dict = ast.literal_eval(f.read())  # interpret the saved string as a dictionary
        except Exception:  # if there is an error or no saved version of the songs_dict:
            self.songs_dict = dict()  # just create an empty songs_dict
        self.new_songs_dict = dict()  # a dictionary of songs to be added
        self.song_uris = []  # temp storage to hold package of new song uris to send to playlist

    def find_song_on_site(self):  # find song name and artist and assign to class variables
        try:  # if there is an error getting website data, try again next loop
            source = requests.get(self.radio_site_url).text  # website that records played songs from the radio station
        except Exception:
            return False
        soup = BeautifulSoup(source, "html.parser")  # if getting source is success, turn it into soup to scrape

        list_songs = []  # list of scraped song_names
        song_names = soup.select(".details__title")  # select track song class with selector gadget css
        for song in song_names:
            song_name = song.text
            if " - Custom Intro" in song_name:
                song_name = song_name.replace(" - Custom Intro", "")  # remove tag for proper name search
            if "- Custom Intro" in song_name:
                song_name = song_name.replace("- Custom Intro", "")  # remove tag for proper name search
            list_songs.append(song_name)  # append final song name

        list_artists = []  # list of scraped song_artists
        song_artists = soup.select(".details__artist")  # select track artist class with selector gadget css
        for artist in song_artists:
            song_artist = re.sub(r'\W+', ' ', artist.text)  # clean punctuation from artist
            if " F. " in song_artist:  # remove "feat." and "Featuring" for proper spotify search
                song_artist = song_artist.replace(" F. ", " ")  # leave only alpha numeric characters in the artist for encoding format
            if " F " in song_artist:  # remove "feat." and "Featuring" for proper spotify search
                song_artist = song_artist.replace(" F ", " ")  # leave only alpha numeric characters in the artist for encoding format
            if " Ft " in song_artist:  # remove "feat." and "Featuring" for proper spotify search
                song_artist = song_artist.replace(" Ft ", " ")  # leave only alpha numeric characters in the artist for encoding format
            if " And " in song_artist:  # remove "feat." and "Featuring" for proper spotify search
                song_artist = song_artist.replace(" And ", " ")  # leave only alpha numeric characters in the artist for encoding format
            if " and " in song_artist:  # remove "feat." and "Featuring" for proper spotify search
                song_artist = song_artist.replace(" and ", " ")  # leave only alpha numeric characters in the artist for encoding format
            if " & " in song_artist:  # remove "feat." and "Featuring" for proper spotify search
                song_artist = song_artist.replace(" & ", " ")  # leave only alpha numeric characters in the artist for encoding format
            if "Pink" in song_artist:  # remove "feat." and "Featuring" for proper spotify search
                song_artist = song_artist.replace("Pink", "P!nk")  # leave only alpha numeric characters in the artist for encoding format
            list_artists.append(song_artist)  # leave only alpha numeric characters in the artist for encoding format

        for s, a in zip(list_songs, list_artists):  # create a new dictionary of updated recently played songs to match song to artist
            self.new_songs_dict[s] = a

        for song in list(self.new_songs_dict.keys()):  # delete songs that are already in playlist
            if song in self.songs_dict.keys():
                del self.new_songs_dict[song]

        if len(self.new_songs_dict) > 0:  # check if there are new songs to be added
            return True  # returns True to signify that an update to the playlist is needed
        else:
            return False  # returns False to signify that no new song has been played yet

    def search_spotify_for_song(self):  # search spotify for song and append song uri to class list of uris
        for song_name in list(self.new_songs_dict.keys()):  # go through list dictionary of new songs so we can del keys
            song_artist = self.new_songs_dict[song_name]
            song_name_encoded = urllib.parse.quote(song_name)  # properly format name and artist for search query
            song_artist_encoded = urllib.parse.quote(song_artist)
            query = f"https://api.spotify.com/v1/search?q=track:{song_name_encoded}%20artist:{song_artist_encoded}&type=track"  # Search for an Item using name and artist
            response = requests.get(query, headers={"Content-Type": "application/json",
                                                    "Authorization": f"Bearer {self.api_token}"})
            if response.status_code == 200:  # check if request was a success (200 is success)
                response_json = response.json()
                if response_json["tracks"]["items"]:
                    self.song_uris.append(response_json["tracks"]["items"][0]["uri"])  # choose the first result from the search and add its uri to the list
                else:
                    print("failed to find:", song_name, "by", song_artist)
                    sys.stdout.flush()
                    self.songs_dict[song_name] = song_artist  # preemptively add the song to the dictionary so it does not show up in the update
                    del self.new_songs_dict[song_name]  # remove the song from showing up on added songs notification
            else:
                print("error code:", response.status_code, "failed to search for song:", song_name, "by", song_artist)
                sys.stdout.flush()
                del self.new_songs_dict[song_name]  # remove the song from showing up on added songs notification
                # do not add to the song dictionary so it can retry again next iteration

    def add_song_to_playlist(self):  # function adds the list of song uris to the playlist
        if len(self.song_uris) != 0:  # only execute if there is songs to add. no need to add empty dictionary
            query = f"https://api.spotify.com/v1/playlists/{self.playlist_id}/tracks?position=0"  # Add Items to a Playlist
            request_data = json.dumps(self.song_uris)
            response = requests.post(query, data=request_data, headers={"Content-Type": "application/json", "Authorization": f"Bearer {self.api_token}"})
            if response.status_code == 201:  # in case of failure in request (201 is success)
                for song in self.new_songs_dict.keys():  # adding the new songs to the main dictionary
                    self.songs_dict[song] = self.new_songs_dict[song]
                else:
                    print("playlist updated - added:", self.new_songs_dict)
                    sys.stdout.flush()
                    try:
                        with open('saved_songs.txt', 'w') as f:  # save new iteration of songs_dict to backup
                            f.write(str(self.songs_dict))
                        self.update_google_drive()
                        # send notification (need to refine a separate process from 94.9)
                        #new_songs_dict_str = str(self.new_songs_dict)
                        #response = requests.post(
                        #    'https://events-api.notivize.com/applications/REDACTED',
                        #    json={'lifecycle_stage': 'update', 'self.new_songs_dict': new_songs_dict_str,
                        #          'songs_dict': 'saved_songs.txt', 'user_email': 'stephencfip@gmail.com'},
                        #    headers={'Authorization': 'Bearer REDACTED'})
                    except Exception:
                        print("error completing post upload tasks")
            else:
                print("error code:", response.status_code, "failed to add:", self.new_songs_dict)
                sys.stdout.flush()
            self.song_uris.clear()  # clear song uris after adding them
            self.new_songs_dict.clear()  # clear new_songs dictionary

    def refresh_api(self):  # automatically generate api tokens so it stays authorized forever
        query = "https://accounts.spotify.com/api/token"
        response = requests.post(query, data={"grant_type": "refresh_token", "refresh_token": self.refresh_token},
                                 headers={"Authorization": "Basic " + self.base_64})
        if response.status_code == 200:  # check if request was success (200 is success)
            response_json = response.json()
            self.api_token = response_json["access_token"]  # reset api_token

    def update_google_drive(self):  # back up saved_songs.txt to a google doc
        try:
            credentials = None
            SCOPES = ['https://www.googleapis.com/auth/drive']
            if os.path.exists('token.pickle'):
                with open('token.pickle', 'rb') as token:
                    credentials = pickle.load(token)
            if not credentials or not credentials.valid:
                if credentials and credentials.expired and credentials.refresh_token:
                    credentials.refresh(Request())
                else:
                    print("NEED MANUAL AUTHENTICATION OF CREDENTIALS")
                    # flow = InstalledAppFlow.from_client_secrets_file(
                    #    'credentials.json', SCOPES)
                    # credentials = flow.run_local_server(port=0)
                with open("token.pickle", "wb") as token:
                    pickle.dump(credentials, token)
            service = build('drive', 'v3', credentials=credentials)
            file_id = "REDACTED"  # unique for each file
            media = MediaFileUpload("saved_songs.txt")
            response = service.files().update(
                fileId=file_id,
                media_body=media
            ).execute()
        except Exception:
            print("error backing up to google drive")


program = RadioFetcher()
while True:
    program.refresh_api()
    if program.find_song_on_site():
        program.search_spotify_for_song()
        program.add_song_to_playlist()
    time.sleep(60)  # add delay (60 seconds) between loops to reduce stress

