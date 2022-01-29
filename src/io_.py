

# local imports
import json
import os
import pathlib

from src.config import load as load_config

#logger = rootLogger.getChild('IO')
config = load_config()


def verify_files():
    files = [config["DATA_FILES_LIKED_SONGS"], config["DATA_FILES_PROCESSED_SONGS"]]

    for f in files:
        f = os.path.join(config["DATA_PERSISTENT_DATA_ROOT"], f)
        if not pathlib.Path(f).is_file():
            print(f'{f} not found, creating blank file')
            with open(f, mode='w', encoding='utf-8') as fp:
                json.dump({}, fp)


def load_liked_songs():
    file = os.path.join(config["DATA_PERSISTENT_DATA_ROOT"], config["DATA_FILES_LIKED_SONGS"])
    return load_json(file)


def load_processed_songs():
    file = os.path.join(config["DATA_PERSISTENT_DATA_ROOT"], config["DATA_FILES_PROCESSED_SONGS"])
    return load_json(file)


def load_json(file):
    if os.path.isfile(file):
        with open(file, mode='r', encoding='utf-8') as f:
            ret = json.load(f)
    else:
        ret = {}

    return ret


def dump_json(file, obj):
    def obj_dict(obj):
        return obj.__dict__

    with open(file, mode='w', encoding='utf-8') as f:
        #TODO: reused - refine
        json.dump(obj, f, indent=4, sort_keys=True, default=obj_dict)


def persist_processed_songs(songs):
    file = os.path.join(config["DATA_PERSISTENT_DATA_ROOT"], config["DATA_FILES_PROCESSED_SONGS"])
    dump_json(file, songs)


def persist_liked_songs(songs):
    file = os.path.join(config["DATA_PERSISTENT_DATA_ROOT"], config["DATA_FILES_LIKED_SONGS"])
    dump_json(file, songs)