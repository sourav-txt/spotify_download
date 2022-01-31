import json
from typing import List

# local imports
from src.deemix_api import DownloadStatus, get_deemix_config
from src.log import rootLogger
from src.config import load as load_config
from src import transform, deemix_api

logger = rootLogger.getChild('DOWNLOAD')

config = load_config()
downloaded_track_paths = []


def missing_tracks():
    logger.info('Getting missing tracks to download')
    songs = transform.get_tracks_to_download()

    logger.info(f'{len(songs)} tracks pending download')
    if not songs:
        logger.info('No tracks to download')
        return

    logger.info(f'Downloading {len(songs)} song(s) from Deezer')
    downloader = deemix_api.DeemixDownloader(arl=config["DEEMIX_ARL"], config=get_deemix_config(), skip_low_quality=True)
    downloader.download_songs(songs)
    downloaded_songs, failed_songs = downloader.get_report()
    logger.info(f'Successfully downloaded {len(downloaded_songs)}/{len(songs)}')

    transform.set_tracks_as_downloaded(downloaded_songs)
    transform.set_tracks_as_failed_to_download(failed_songs)

    get_file_download_paths(downloaded_songs)


def get_file_download_paths(download_report: List[DownloadStatus]):
    global downloaded_track_paths

    for k in download_report:
        downloaded_track_paths.append(download_report[k].download_path)


