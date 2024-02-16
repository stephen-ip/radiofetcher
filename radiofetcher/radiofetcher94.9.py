from bs4 import BeautifulSoup
import requests
import json
import urllib.parse
import re
from pymongo import MongoClient  # pip3 install pymongo + pip3 install pymongo[srv]
import os
from datetime import datetime

class RadioFetcher:

    def __init__(self):
        self.api_token = ""
        self.refresh_token = os.environ['SPOTIFY_REFRESH_TOKEN']  # allow access to make new api tokens
        self.base_64 = os.environ['SPOTIFY_BASE_64']  # encoded credentials of clientID:clientSecret
        self.playlist_id = os.environ['PLAYLIST_ID']
        self.radio_site_url = "https://wild949.iheart.com/music/recently-played/"
        self.CONNECTION_STRING = os.environ['MONGO_DB_CONNECTION_STRING']
        self.collection = None
        self.new_songs_dict = dict()  # a dictionary of songs to be added
        self.song_uris = []  # temp storage to hold package of new song uris to send to playlist

    def find_song_on_site(self):  # find song name and artist and assign to class variables
        try:  # if there is an error getting website data, try again next loop
            source = requests.get(self.radio_site_url).text  # website that records played songs from the radio station
        except Exception:
            return False
        soup = BeautifulSoup(source, "html.parser")  # if getting source is success, turn it into soup to scrape

        list_songs = []  # list of scraped song_names
        song_names = soup.select(".track-title")  # select track song class with selector gadget css
        for song in song_names:
            list_songs.append(song.text)  # no need to strip anything from title for most precise search

        list_artists = []  # list of scraped song_artists
        song_artists = soup.select(".track-artist")  # select track artist class with selector gadget css
        for artist in song_artists:
            song_artist = re.sub(r'\W+', ' ', artist.text)  # clean punctuation from artist
            if "feat." in song_artist:  # remove "feat." and "Featuring" for proper spotify search
                song_artist = song_artist.replace("feat.", " ")  # leave only alpha numeric characters in the artist for encoding format
            if "Feat." in song_artist:
                song_artist = song_artist.replace("Feat.", " ")  # leave only alpha numeric characters in the artist for encoding format
            if " feat " in song_artist:
                song_artist = song_artist.replace("feat", " ")  # leave only alpha numeric characters in the artist for encoding format
            if "Feat" in song_artist:
                song_artist = song_artist.replace("Feat", " ")  # leave only alpha numeric characters in the artist for encoding format
            if "Featuring" in song_artist:
                song_artist = song_artist.replace("Featuring", " ")  # leave only alpha numeric characters in the artist for encoding format
            if "featuring" in song_artist:
                song_artist = song_artist.replace("featuring", " ")  # leave only alpha numeric characters in the artist for encoding format
            if " and " in song_artist:
                song_artist = song_artist.replace("and", " ")  # leave only alpha numeric characters in the artist for encoding format
            if " x " in song_artist:
                song_artist = song_artist.replace(" x ", " ")  # leave only alpha numeric characters in the artist for encoding format
            if "Pink" in song_artist:  # remove "feat." and "Featuring" for proper spotify search
                song_artist = song_artist.replace("Pink", "P!nk")  # leave only alpha numeric characters in the artist for encoding format
            list_artists.append(song_artist)  # leave only alpha numeric characters in the artist for encoding format

        for s, a in zip(list_songs, list_artists):  # create a new dictionary of updated recently played songs to match song to artist
            self.new_songs_dict[s] = a

        try:
            self.collection = self.get_database_collection()
        except Exception:
            print("error accessing data base")
            return False  # if an error occurs trying to access data base, stop and try again later

        for song, artists in list(self.new_songs_dict.items()):  # delete songs that are already in playlist
            if self.collection.find_one({"track_name": song, "track_artists": artists}):
                del self.new_songs_dict[song]

        if len(self.new_songs_dict) > 0:  # check if there are new songs to be added
            return True  # returns True to signify that an update to the playlist is needed
        else:
            return False  # returns False to signify that no new song has been played yet

    def search_spotify_for_song(self):  # search spotify for song and append song uri to class list of uris
        for song_name, song_artist in list(self.new_songs_dict.items()):  # go through list dictionary of new songs so we can del keys
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
                    new_song_document = {  # create new song document to be inserted into the database
                    "track_name": song_name,
                    "track_artists": song_artist,
                    "added_to_playlist": False,
                    "created_time": datetime.now()
                    }
                    self.collection.insert_one(new_song_document)
                    del self.new_songs_dict[song_name]  # remove the song from showing up on added songs notification
            else:
                print("failed to search for song - error code:", response.status_code)
                del self.new_songs_dict[song_name]  # remove the song from showing up on added songs notification
                # do not add to the song dictionary so it can retry again next iteration

    def add_song_to_playlist(self):  # function adds the list of song uris to the playlist
        if len(self.song_uris) != 0:  # only execute if there is songs to add. no need to add empty dictionary
            query = f"https://api.spotify.com/v1/playlists/{self.playlist_id}/tracks?position=0"  # Add Items to a Playlist
            request_data = json.dumps(self.song_uris)
            response = requests.post(query, data=request_data, headers={"Content-Type": "application/json",
                                                                        "Authorization": f"Bearer {self.api_token}"})
            if response.status_code == 201:  # in case of failure in request (201 is success)
                new_song_documents_array = []
                for song in self.new_songs_dict.keys():  # adding the new songs to the main dictionary
                    new_song_document = {  # create new song document to be inserted into the database
                    "track_name": song,
                    "track_artists": self.new_songs_dict[song],
                    "added_to_playlist": True,
                    "created_time": datetime.now()
                    }
                    new_song_documents_array.append(new_song_document)
                else:
                    print("playlist updated - added:", self.new_songs_dict)
                    try:
                        self.collection.insert_many(new_song_documents_array)
                    except Exception:
                        print("failed to insert data into database")
            else:
                print("error code:", response.status_code, "failed to add:", self.new_songs_dict)
            self.song_uris.clear()  # clear song uris after adding them
            self.new_songs_dict.clear()  # clear new_songs dictionary

    def refresh_api(self):  # automatically generate api tokens so it stays authorized forever
        query = "https://accounts.spotify.com/api/token"
        response = requests.post(query, data={"grant_type": "refresh_token", "refresh_token": self.refresh_token},
                                 headers={"Authorization": "Basic " + self.base_64})
        if response.status_code == 200:  # check if request was success (200 is success)
            response_json = response.json()
            self.api_token = response_json["access_token"]  # reset api_token

    def get_database_collection(self):  # returns the mongoDB data base collection for this project
        client = MongoClient(self.CONNECTION_STRING)
        database = client['saved_songs']
        return database["WILD_94.9"]

def lambda_handler(event, context):
    program = RadioFetcher()
    program.refresh_api()
    if program.find_song_on_site():
        program.search_spotify_for_song()
        program.add_song_to_playlist()
