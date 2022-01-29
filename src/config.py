import json
import os

# local imports
#from src.log import rootLogger

cfg = None


class Configuration:
    def __init__(self):
        #self._logger = rootLogger.getChild('Configuration')
        self.config = {}
        self._load_config()

    def _load_config(self):
        #print('Load config is invoked..')
        loaded = self._load_config_file()
        # TODO: Schema validation
        self.config = self._flatten_settings(loaded)

    @staticmethod
    def _load_config_file():
        file = os.path.join(os.path.dirname(__file__), '..', 'config.json')
        if not os.path.isfile(file):
            # logger.error(f'Unable to find config file at: {file}')
            raise

        try:
            with open(os.path.join(file), mode='r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as ex:
            # logger.error(f'Failed to open config file {file}, exception was: ', ex)
            raise

    @staticmethod
    def _flatten_settings(settings: dict):
        ret = {}
        for k in settings.keys():
            if isinstance(settings[k], dict):
                for k2 in settings[k].keys():
                    if isinstance(settings[k][k2], dict):
                        for k3 in settings[k][k2].keys():
                            value = settings[k][k2][k3]
                            ret["_".join([k.upper(), k2.upper(), k3.upper()])] = value
                    else:
                        value = settings[k][k2]
                        ret["_".join([k.upper(), k2.upper()])] = value
            else:
                ret[k.upper()] = settings[k]
        return ret


def load():
    global cfg
    if cfg is None:
        cfg = Configuration().config

    return cfg
