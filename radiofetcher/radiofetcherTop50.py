# United States Top 50 Saved

import requests  # pip3 install requests
import json
import ast
import time
import sys

from pymongo import MongoClient  # pip3 install pymongo
import pymongo


class RadioFetcher:

    def __init__(self):
        self.api_token = ""  # generated using the refresh function
        self.refresh_token = "REDACTED"  # allow access to make new api tokens
        self.base_64 = "REDACTED"  # encoded credentials of clientID:clientSecret
        self.playlist_id = "0rw0Vx0evy7EP1Dy4UAS0v"  # US Top 50 Saved playlist id
        self.US_Top_50_id = "37i9dQZEVXbLRQDuF5jeBp"  # US Top 50 playlist id
        self.CONNECTION_STRING = "REDACTED"  # for mongoDB connection
        self.database = None  # global database object
        self.new_songs_dict = dict()  # temp holder for new songs' information {uri: (track, artist)}
        self.song_uris = []  # array of newly found song uris to be added to the playlist at the end of iteration
        self.new_song_documents_array = []  # array of newly found song docs to be added to the data base after being added to the playlist

    def find_new_song_from_UST50(self):  # find the uris of all the songs in UST50 playlist and see if there are new songs. Returns True if it finds anything, else False
        query = f"https://api.spotify.com/v1/playlists/{self.US_Top_50_id}/tracks"  # Get a Playlist's Items
        response = requests.get(query, headers={"Content-Type": "application/json",
                                                "Authorization": f"Bearer {self.api_token}"})
        if response.status_code == 200:  # check if request was a success (200 is success)
            response_json = response.json()

            try:
                self.database = self.get_database()
                collection = self.database["US_Top_50_Saved"]
            except Exception:
                print("error accessing data base")
                sys.stdout.flush()
                return False  # if an error occurs trying to access data base, stop and try again later

            for item in response_json["items"]:  # go through each item in playlist
                track_uri = item["track"]["uri"]
                if not collection.find_one({"track_uri": track_uri}):  # if we find a song that is not added in our playlist...
                    track_name = item["track"]["name"]
                    track_artists = [artist["name"] for artist in item["track"]["artists"]]
                    song_info_tuple = (track_name, track_artists)  # (song name, [song artists])
                    self.new_songs_dict[track_uri] = song_info_tuple  # hold newly found songs in new_songs_dict
        else:
            print("error code:", response.status_code, "had occurred when searching for tracks in UST50 playlist")
            return False
        if len(self.new_songs_dict) != 0:
            self.song_uris = [uri for uri in self.new_songs_dict.keys()]  # create an array of song_uris to be added
            return True
        else:
            return False

    def add_songs_to_playlist(self):  # function adds the list of new song uris to the playlist
        query = f"https://api.spotify.com/v1/playlists/{self.playlist_id}/tracks?position=0"  # Add Items to a Playlist
        request_data = json.dumps(self.song_uris)  # format array of song uris for request data
        response = requests.post(query, data=request_data, headers={"Content-Type": "application/json",
                                                                    "Authorization": f"Bearer {self.api_token}"})
        if response.status_code == 201:  # in case of failure in request (201 is success)
            for uri in self.new_songs_dict.keys():  # adding the new songs to the main dictionary
                track_name = self.new_songs_dict[uri][0]
                track_artists = self.new_songs_dict[uri][1]
                new_song_document = {  # create new song document to be inserted into the database
                    "track_name": track_name,
                    "track_artists": track_artists,
                    "track_uri": uri,
                    "added_to_playlist": True
                }
                self.new_song_documents_array.append(new_song_document)
                # self.songs_dict[song] = self.new_songs_dict[song]
            else:
                print("playlist updated - added:", self.new_songs_dict.values())  # values show the song info (no uris)
                sys.stdout.flush()
                collection = self.database["US_Top_50_Saved"]
                collection.insert_many(self.new_song_documents_array)  # insert new song docs into data base collection
        else:
            print("error code:", response.status_code, "failed to add:", self.new_songs_dict)
            sys.stdout.flush()
        self.song_uris.clear()  # clear song uris after adding them
        self.new_songs_dict.clear()  # clear new_songs dictionary
        self.new_song_documents_array.clear()  # clear new song docs in array

    def refresh_api(self):  # automatically generate api tokens so it stays authorized forever
        query = "https://accounts.spotify.com/api/token"
        response = requests.post(query, data={"grant_type": "refresh_token", "refresh_token": self.refresh_token},
                                 headers={"Authorization": "Basic " + self.base_64})
        if response.status_code == 200:  # check if request was success (200 is success)
            response_json = response.json()
            self.api_token = response_json["access_token"]  # reset api_token

    def get_database(self):  # returns the mongoDB data base for this project
        client = MongoClient(self.CONNECTION_STRING)
        return client['saved_songs']


program = RadioFetcher()
while True:
    program.refresh_api()
    if program.find_new_song_from_UST50():
        program.add_songs_to_playlist()
    time.sleep(10800)  # add delay (3 hours) between loops to reduce stress

