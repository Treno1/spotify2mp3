import spotipy
import requests
from spotipy.oauth2 import SpotifyClientCredentials
import json
from dataclasses import dataclass
from dataclasses_json import dataclass_json
from bs4 import BeautifulSoup
import requests
from datetime import datetime, timedelta
from pytube import YouTube
from moviepy.editor import AudioFileClip, VideoFileClip
import os


@dataclass_json
@dataclass
class Track:
    name: str
    artist: str
    fullName: str
    durationSec: int


@dataclass_json
@dataclass
class YtVideo:
    id: str
    name: str
    durationStr: str
    durationSec: int


def getPlaylistTracks(url: str):
    client_id = 'XXX'
    client_secret = 'XXX'

    client_credentials_manager = SpotifyClientCredentials(client_id=client_id, client_secret=client_secret)
    sp = spotipy.Spotify(client_credentials_manager=client_credentials_manager)

    playlist_info = sp.playlist_tracks(url)

    result = []

    for item in playlist_info['items']:
        track = item['track']
        artists = [artist['name'] for artist in track['artists']]

        track_result = Track(
            name=track['name'],
            artist=','.join(artists),
            fullName = f"{','.join(artists)} - {track['name']}",
            durationSec=track['duration_ms']/1000
        )

        result.append(track_result)

    return result


def _durationStr2Sec(duration: str):
    if len(duration) > 5:
        return 9999999
    t = datetime.strptime(duration, '%M:%S')
    delta = timedelta(minutes=t.minute, seconds=t.second)
    return delta.total_seconds()


def listYoutubeVideos(track: Track):
    url = f"https://www.youtube.com/results?search_query={track.fullName}"
    response = requests.get(url)

    soup = BeautifulSoup(response.text, 'html.parser')

    scripts = soup.find_all('script')

    videos = []

    for script in scripts:
        scriptCode = script.get_text()
        if "var ytInitialData" not in scriptCode:
            continue

        scriptCode = scriptCode[scriptCode.find('{'):scriptCode.rfind('}')+1]

        ytInitialData = json.loads(scriptCode)

        for content in ytInitialData['contents']['twoColumnSearchResultsRenderer']['primaryContents']['sectionListRenderer']['contents']:
            if 'itemSectionRenderer' not in content: 
                continue

            for subContent in content['itemSectionRenderer']['contents']:
                if 'videoRenderer' not in subContent:
                    continue
                videoRenderer = subContent['videoRenderer']

                video = YtVideo(
                    id=videoRenderer['videoId'],
                    name=videoRenderer['title']['runs'][0]['text'],
                    durationStr=videoRenderer['lengthText']['simpleText'],
                    durationSec=_durationStr2Sec(videoRenderer['lengthText']['simpleText'])
                )
                videos.append(video)
    
    return videos


def chooseYtVideo(track: Track, videos: list[YtVideo]):
    durationMaxDiffSecs = 5;

    for video in videos:
        if abs(track.durationSec - video.durationSec) > durationMaxDiffSecs:
            continue

        return video

    return None 


def download_as_mp3(track: Track, video: YtVideo):
    output_path = "/Users/aleksandrsuvorkin/Downloads/music-export"
    target_file_name = f"{output_path}/{track.fullName}.mp3"

    if os.path.isfile(target_file_name):
        print(f"already donwloaded {track.fullName}. Skip")
        return

    youtube_url = f"https://www.youtube.com/watch?v={video.id}"    
    yt = YouTube(youtube_url)

    # get the highest quality stream
    stream = yt.streams.get_highest_resolution()

    # download the file
    output_file = stream.download(output_path=output_path)

    # convert video to mp3
    video_clip = VideoFileClip(output_file)
    audio_clip = video_clip.audio
    audio_clip.write_audiofile(target_file_name)

    # optionally, if you want to remove the original .mp4 file after conversion
    # uncomment the following line:
    os.remove(output_file)

    









url = 'https://open.spotify.com/playlist/7Gog4SLFOhXobZcwMdGxAF?si=5a9222d3cc824f35' # wake
tracks = getPlaylistTracks(url)

for track in tracks:
    
    vids = listYoutubeVideos(track)
    
    mainVid = chooseYtVideo(track, vids)
    
    if mainVid is None:
        print(f"!!!!!!!! Couldn't find proper YtVideo for {track.artist}-{track.name}")
        continue

    download_as_mp3(track, mainVid)

    