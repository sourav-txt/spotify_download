import hashlib
import json
import os
from typing import List, Dict
from dataclasses import dataclass

# deemix
from deezer import Deezer
from deemix import generateDownloadObject
from deemix.downloader import Downloader, generatePath, extensions, getPreferredBitrate
from deemix.utils import getBitrateNumberFromText, formatListener
from deemix.types.Track import Track
from deemix.types.DownloadObjects import Single

# local imports
from src import config
from src import pushover_api
from src.log import rootLogger

from src.git_api import commit_files

config = config.load()
arl_valid = False
logger = rootLogger.getChild('DEEMIX_API')


def get_md5(file):
    md5_hash = hashlib.md5()
    with open(file, "rb") as f:
        # Read and update hash in chunks of 4K
        for byte_block in iter(lambda: f.read(4096), b""):
            md5_hash.update(byte_block)
        return md5_hash.hexdigest()


# class LogListener:
#     @classmethod
#     def send(cls, key, value=None):
#         logString = formatListener(key, value)
#         if logString: print(logString)

class LogListener:
    def __init__(self):
        self.messages = []

    def send(self, key, value=None):
        self.messages.append({key: value})


class DownloadLogger:
    def __init__(self, index: int, total: int, isrc: str):
        self._logger = logger
        self._downloadIndex = index
        self._downloadTotal = total
        self._isrc = isrc

    def info(self, message: str):
        self._logger.info(f'{str(self._downloadIndex)}/{str(self._downloadTotal)} - [isrc:{self._isrc}] - {message}')

    def warn(self, message: str):
        self._logger.warning(f'{str(self._downloadIndex)}/{str(self._downloadTotal)} - [isrc:{self._isrc}] - {message}')

    def error(self, message: str):
        self._logger.error(f'{str(self._downloadIndex)}/{str(self._downloadTotal)} - [isrc:{self._isrc}] - {message}')


@dataclass
class DownloadStatus:
    # TODO: add bitrate / file type
    isrc: str
    url: str
    success: bool
    skipped: bool
    errors: List[str]
    download_path: str
    md5: str


class DeemixDownloader:
    def __init__(self, arl: str, deemix_config: dict, skip_low_quality=False):
        self.dz = Deezer()
        self.deemix_config = deemix_config
        self.deezer_logged_in = self.dz.login_via_arl(arl)
        # self.listener = LogListener()
        self.skip_low_quality = skip_low_quality
        self.urls_to_download = list()
        self.download_report: Dict[DownloadStatus] = {}

    def download_urls(self, urls: list):
        self.urls_to_download = urls

        if self.skip_low_quality and not self.dz.current_user.get('can_stream_lossless'):
            logger.info(f'SKIP_LOW_QUALITY is specified and unable to stream FLAC, stopping download')
            logger.info(f'If this is unexpected, please ensure your Deezer account is Premium/Hi-Fi')
            raise Exception()

        if not self.deezer_logged_in:
            raise Exception('Failed to login with arl, you may need to refresh it')

        logger.info(f'Gathering song information in preparation for download..')
        download_objs = {v: generateDownloadObject(self.dz, v, '9') for v in self.urls_to_download}
        num_urls_to_download = len(self.urls_to_download)
        i = 0
        for k, obj in download_objs.items():
            errors = None
            try:
                isrc = self.extract_isrc_from_download_object(obj)
                dl_logger = DownloadLogger(index=(i+1), total=num_urls_to_download, isrc=isrc)
                listener = LogListener()
                # dl = Downloader(self.dz, obj, self.deemix_config, self.listener)
                dl = Downloader(self.dz, obj, self.deemix_config, listener)


                # path, fn = extract_path_and_filename_from_track_api(dl, obj)
                # if os.path.isfile(path):
                #     print(f'{path} is already downloaded, skipping')
                #     self.download_report[k] = DownloadStatus(
                #                                     isrc=isrc,
                #                                     url=k,
                #                                     success=True,
                #                                     skipped=True,
                #                                     errors=errors or [],
                #                                     download_path=path or "",
                #                                     md5=get_md5(path)
                #                                 )
                #     i += 1
                #     continue

                # logger.info(f"{str(i + 1)}/{len(self.urls_to_download)} - Downloading {fn}")

                #logger.info(f"{str(i + 1)}/{len(self.urls_to_download)} - Downloading  {isrc}")
                dl_logger.info('Download starting')
                dl.start()
                self.update_download_report(dl.downloadObject, isrc, k, listener, dl_logger)

            except Exception as ex:
                logger.error(ex)

            i += 1

    @staticmethod
    def download_skipped(listener: LogListener):
        download_skipped = False
        for m in listener.messages:
            if 'downloadInfo' in m:
                if m['downloadInfo'].get('state') == 'alreadyDownloaded':
                    download_skipped = True

        return download_skipped


    def update_download_report(self, download_object, isrc: str, url: str, listener: LogListener, dl_logger):
        if not isinstance(download_object, Single):
            raise Exception("Not a Single, unexpected type!", download_object)
        errors = None
        md5 = ""
        status = False
        f = ""

        if download_object.downloaded == 1:
            f = download_object.files[0]['path']
            if self.download_skipped(listener):
                #logger.warning(f'Already downloaded: {f}, skipping..')
                dl_logger.warn(f'Already downloaded: {f}, skipping..')
                status = True
                md5 = get_md5(f)

            elif os.path.isfile(f):
                #logger.info(f'Successfully downloaded: {f}')
                dl_logger.info(f'Successfully downloaded: {f}')
                status = True
                md5 = get_md5(f)
            else:
                #logger.warn(f'Downloaded but could not find {f}')
                dl_logger.warn(f'Downloaded but could not find {f}')
                errors = [f"Downloaded but could not find {f}"]

        elif download_object.failed == 1:
            #logger.warn(f'Download for DeezerId: {download_object.single["trackAPI"]["id"]} failed, errors:',
                        #download_object.errors[0]['message'])
            dl_logger.warn(f'Download for DeezerId: {download_object.single["trackAPI"]["id"]} failed, error: {download_object.errors[0]["message"]}')
            errors = download_object.errors

        self.download_report[url] = DownloadStatus(isrc=isrc, url=url, success=status, skipped=False,
                                                   errors=errors or [],
                                                   download_path=f, md5=md5)

    def get_report(self):
        succeeded = {}
        failed = {}

        for v in self.download_report.values():
            if v.success:
                succeeded[v.isrc] = v
            else:
                failed[v.isrc] = v

        return succeeded, failed

    @staticmethod
    def extract_isrc_from_download_object(obj):
        return obj.single["trackAPI"]["isrc"]


def extract_path_and_filename_from_track_api(downloader: Downloader, download_obj: Single):
    track = Track().parseData(
        dz=downloader.dz,
        track_id=downloader.downloadObject.single["trackAPI"]["id"],
        trackAPI=downloader.downloadObject.single["trackAPI"],
        albumAPI=None,
        playlistAPI=None
    )
    (filename, filepath, artistPath, coverPath, extrasPath) = generatePath(track, download_obj, downloader.settings)

    selectedFormat = getPreferredBitrate(
        downloader.dz,
        track,
        downloader.bitrate,
        downloader.settings['fallbackBitrate'],
        downloader.settings['feelingLucky'],
        downloader.downloadObject.uuid,
        downloader.listener
    )

    return os.path.join(filepath, filename + extensions[selectedFormat]), filename


def check_deemix_config():
    if not os.path.isdir(config["deemix"]["download_path"]):
        logger.error(f'{config["deemix"]["download_path"]} must be an existing folder')
        raise Exception(f'{config["deemix"]["download_path"]} must be an existing folder')

    if '\\' in config["deemix"]["download_path"]:
        config["deemix"]["download_path"] = config["deemix"]["download_path"].replace("\\", "/")

    # config_json = json.loads(
    #     deemix_config
    #         .replace('DOWNLOAD_LOCATION_PATH', config["deemix"]["download_path"])
    #         .replace('MAX_BITRATE', config["deemix"]["max_bitrate"])
    # )


# def check_deemix_config():
#     if not os.path.isdir(config["deemix"]["config_path"]):
#         logger.error("config['deemix']['config_path'] must be an existing folder")
#         raise Exception("config['deemix']['config_path'] must be an existing folder")
#     if not os.path.isdir(config["deemix"]["download_path"]):
#         logger.error(f'{config["deemix"]["download_path"]} must be an existing folder')
#         raise Exception(f'{config["deemix"]["download_path"]} must be an existing folder')
#     elif not os.path.isfile(os.path.join(config["deemix"]["config_path"], 'config.json')):
#         if '\\' in config["deemix"]["download_path"]:
#             config["deemix"]["download_path"] = config["deemix"]["download_path"].replace("\\", "/")
#         config_json = json.loads(deemix_config.replace('DOWNLOAD_LOCATION_PATH', config["deemix"]["download_path"]))
#         logger.info('Creating deemix config for first use')
#         with open(os.path.join(config["deemix"]["config_path"], 'config.json'), mode='w', encoding='utf-8') as f:
#             json.dump(config_json, f, indent=True)
#         if config['git']['enabled']:
#             # Ensure repo clean
#             commit_files('Created deemix config for first use')


def check_arl_valid():
    logger.debug(f'Checking if arl is valid')
    global arl_valid
    if not arl_valid:
        logger.debug(f'arl_valid is False')
        arl = config['deemix']['arl'].strip()
        logger.debug(f'Logging in with arl in config.json')
        client = Deezer()
        login = client.login_via_arl(arl)

        if login:
            logger.debug(f'Login successful')
            arl_valid = True
        else:
            logger.error(f'Login unsuccessful, raising exception')
            pushover_api.send_notification('Spotify downloader', 'Failed to validate arl')
            raise Exception('Failed to login with arl, you may need to refresh it')


# def download_url(url=[]):
#     app = cli('', config['deemix']['config_path'])
#     app.login()
#     url = list(url)
#     logger.info(f'Downloading {len(url)} songs from Deezer')
#     app.downloadLink(url)


def download_urls(urls: List[str]):
    #logger.info(f'Downloading {len(urls)} song(s) from Deezer')

    deemix_config = json.loads(
        template_config
            .replace('DOWNLOAD_LOCATION_PATH', config["deemix"]["download_path"])
            .replace('MAX_BITRATE', config["deemix"]["max_bitrate"])
    )
    downloader = DeemixDownloader(arl=config["deemix"]["arl"], deemix_config=deemix_config, skip_low_quality=True)
    downloader.download_urls(urls)


def download_file(path):
    print('Placeholder')


template_config = """
{
  "downloadLocation": "DOWNLOAD_LOCATION_PATH",
  "tracknameTemplate": "%artist% - %title%",
  "albumTracknameTemplate": "%artist% - %title%",
  "playlistTracknameTemplate": "%artist% - %title%",
  "createPlaylistFolder": false,
  "playlistNameTemplate": "%playlist%",
  "createArtistFolder": true,
  "artistNameTemplate": "%artist%",
  "createAlbumFolder": true,
  "albumNameTemplate": "%album%",
  "createCDFolder": false,
  "createStructurePlaylist": true,
  "createSingleFolder": true,
  "padTracks": true,
  "paddingSize": "0",
  "illegalCharacterReplacer": "_",
  "queueConcurrency": 10,
  "maxBitrate": "MAX_BITRATE",
  "feelingLucky": false,
  "fallbackBitrate": true,
  "fallbackSearch": false,
  "logErrors": true,
  "logSearched": false,
  "saveDownloadQueue": false,
  "overwriteFile": "n",
  "createM3U8File": false,
  "syncedLyrics": false,
  "embeddedArtworkSize": 1000,
  "localArtworkSize": 1400,
  "saveArtwork": false,
  "coverImageTemplate": "cover",
  "saveArtworkArtist": false,
  "artistImageTemplate": "folder",
  "PNGcovers": false,
  "jpegImageQuality": 80,
  "dateFormat": "Y-M-D",
  "removeAlbumVersion": false,
  "featuredToTitle": "0",
  "titleCasing": "nothing",
  "artistCasing": "nothing",
  "executeCommand": "",
  "tags": {
    "title": true,
    "artist": true,
    "album": true,
    "cover": true,
    "trackNumber": true,
    "trackTotal": false,
    "discNumber": true,
    "discTotal": false,
    "albumArtist": true,
    "genre": true,
    "year": true,
    "date": true,
    "explicit": false,
    "isrc": true,
    "length": true,
    "barcode": false,
    "bpm": true,
    "replayGain": false,
    "label": true,
    "lyrics": false,
    "copyright": false,
    "composer": true,
    "rating": false,
    "involvedPeople": false,
    "savePlaylistAsCompilation": false,
    "useNullSeparator": false,
    "saveID3v1": true,
    "multitagSeparator": "default",
    "syncedLyrics": false,
    "multiArtistSeparator": "default",
    "singleAlbumArtist": false,
    "coverDescriptionUTF8": false,
    "source": false
  },
  "playlistFilenameTemplate": "playlist",
  "embeddedArtworkPNG": false,
  "localArtworkFormat": "jpg",
  "albumVariousArtists": true,
  "removeDuplicateArtists": false,
  "tagsLanguage": ""
}
"""
