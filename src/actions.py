from src import spotify_api, transform, download, pushover_api, autoscan_api, git_api, deemix_api, io_
from src.log import rootLogger

from datetime import datetime

logger = rootLogger.getChild('ACTIONS')


def auto():
    logger.info('Script started with -auto flag')

    # Checks
    deemix_api.check_deemix_config()
    deemix_api.check_arl_valid()

    pushover_api.send_notification('Spotify downloader', 'Script started with --auto flag')
    git_api.assert_repo()

    spotify_api.download_liked()
    transform.process_liked()
    download.missing_tracks()
    autoscan_api.scan(download.downloaded_track_paths)

    git_api.commit_files(f'Spotify Downloader auto commit {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}')

    if len(download.downloaded_track_paths) >= 1:
        pushover_api.send_notification(
            'Spotify downloader',
            f'Successfully downloaded {len(download.downloaded_track_paths)} new tracks'
        )
    pushover_api.send_notification('Spotify downloader', f'Script finished')
    logger.info('Script finished')


def sync_liked():
    logger.info('Script started with -sync-liked flag')
    spotify_api.download_liked()
    logger.info('Script finished')


def sync_liked_custom_user(client_id, client_secret, username, liked_songs_path):
    logger.info('Script started with -download-liked flag')
    spotify_api.download_liked_manual(client_id, client_secret, username, liked_songs_path)
    logger.info('Script finished')


def match_liked():
    logger.info('Script started with -match-liked flag')
    transform.process_liked()
    logger.info('Script finished')


def download_missing():
    logger.info('Script started with -download-missing flag')
    download.missing_tracks()
    logger.info('Script finished')


def authorize_spotify():
    spotify_api.cache_spotify_auth()


def scan(paths):
    logger.info('Script started with -manual-scan flag')
    autoscan_api.scan(paths)
    logger.info('Script finished')


def playlist_stats():
    logger.info('Script started with -playlist-stats flag')
    spotify_api.display_playlist_stats()
    logger.info('Script finished')


def validate_downloaded_files():
    logger.info('Script started with -validate-downloaded-files flag')
    missing = io_.get_missing_files()
    logger.info(f'Found {str(missing)} missing songs')
    logger.info('Script finished')