import deezer as Deezer
import sys

# local imports
from deezer.errors import DataException

from src.config import load as load_config
from src.spotify_api import SpotifySong
from src.log import rootLogger

logger = rootLogger.getChild('DEEZER_API')
config = load_config()

# load Deezer and login (for downloads), API is unauthenicated
client = Deezer.Deezer()


class MatchLogger:
    def __init__(self, song: SpotifySong):
        self._logger = logger
        self._song = song

    def info(self, message: str):
        self._logger.info(f'[{self._song.artist} - {self._song.title}] - {message}')

    def warning(self, message: str):
        self._logger.warning(f'[{self._song.artist} - {self._song.title}] - {message}')

    def debug(self, message: str):
        self._logger.debug(f'[{self._song.artist} - {self._song.title}] - {message}')

    def error(self, message: str):
        self._logger.error(f'[{self._song.artist} - {self._song.title}] - {message}')


class SongMatcher:
    def __init__(self, song: SpotifySong):
        self._logger = MatchLogger(song)
        self.song = song
        self.match = False
        self.match_type = None
        self.match_message = None
        self.match_payload = None

    def _match_via_isrc(self):
        track = Deezer.API.get_track(client.api, f'isrc:{self.song.isrc}')

        self._logger.debug(f'Matched - [isrc]')
        self.match = True
        self.match_type = "isrc"
        self.match_payload = track

    def _match_fuzzy(self):
        deezer_search = Deezer.API.advanced_search(
            client.api,  # self
            self.song.artist,  # artist
            self.song.album,  # album
            self.song.title  # track name
        )

        if len(deezer_search['data']) > 0:
            self._logger.debug(f'Matched - [fuzzy]')
            self.match = True
            self.match_type = "fuzzy"
            self.match_payload = deezer_search['data'][0]
        else:
            self._logger.debug(f'Failed fuzzy searching, SpotifyId: {self.song.id_}')

    def search(self):
        try:
            self._match_via_isrc()
        except DataException:
            self._match_fuzzy()
        except Exception as ex:
            raise Exception(ex)

        if self.match:
            if 'link' not in self.match_payload:
                self._logger.warning(f'[SpotifyId:{self.song.id_}] - Matched but response does not contain a Deezer link, unmatching..')
                self.match = False
                self.match_message = "Matched but response does not contain a Deezer link"
                return

            if self.match_payload.get('artist') is not None and not self.match_payload['artist'].get('name'):
                self._logger.warning(
                    f'[SpotifyId:{self.song.id_}] - Matched but response does not contain an Deezer artist, unmatching..')
                self.match = False
                self.match_message = f"Matched but response does not contain a artist name, likely this link will not work. Matched link: '{self.match_payload['link']}'"
                return

            if 'id' not in self.match_payload:
                self._logger.warning(
                    f'[SpotifyId:{self.song.id_}] - Matched but response does not contain a Deezer id, unmatching..')
                self.match = False
                self.match_message = f"Matched but response does not contain a Deezer id"