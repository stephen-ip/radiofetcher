# radiofetcher
A python script that connects radio stations to Spotify.
These scripts automatically checks a radio station's website and add songs that have not yet been added to the playlist.

Technology Used: Python, Spotify API, Google Drive API, OAuth, Webscraping with Beautiful Soup 4, Notivize, Google Compute Engine (VM Instance), MongoDB
Update(5/16/2022): MongoDB is now used instead of saving to a Google Doc in a Google Drive for simplicity reasons. The scripts are now also running using AWS Lambda functions triggered by AWS CloudWatch Events every 30 mins instead of running in GCP since it uses less resources and does need permanent uptime.

The links to the 3 radio stations are listed below:

Wild 94.9: https://open.spotify.com/playlist/1I0G9xjsHyypBjQDMrG04l?si=8d459e5388cf4cfc

95.3 KUIC: https://open.spotify.com/playlist/2aKFnLcwzbHRuVSoFpKW2x?si=381376976f1f43bb

Alice @ 97.3: https://open.spotify.com/playlist/7HaIcQA6sZjL7xGaxsyNP2?si=8e0698a370ab4acb

US Top 50 Saved (not a radio station, just an archive built with the same technology): https://open.spotify.com/playlist/0rw0Vx0evy7EP1Dy4UAS0v?si=e0b0155436834af3
