from pathlib import Path
from typing import Dict, List, Optional
import pickle
from zipfile import ZipFile

PIC_SUFFIXES = ['png', 'jpg', 'jpeg', 'bmp', 'raw']
AUDIO_SUFFIXES = ['ogg', 'mp3', 'wav', 'flac']

# I'm pretty sure this would not be used
def deep_merge_dict(target_dict: dict, new_dict: dict):
    if not isinstance(new_dict, dict):
        raise RuntimeError(f"Bad hierarchy structure at {new_dict}.")
    for key, value in new_dict.items():
        if key in target_dict:
            deep_merge_dict(target_dict[key], value)
        else:
            target_dict[key] = value


def index_simple_dir(folder: Path, accept_suffixes: Optional[List[str]]=None) -> Dict[str, Dict | Path]:
    if folder.is_file():
        raise RuntimeError(f"Expect {folder} to be a directory, turns out to be a file.")
    result = {}
    for item in folder.iterdir():
        if item.is_file():
            if accept_suffixes is None or item.suffix[1:] in accept_suffixes:
                result[item.stem] = item
        else:
            result[item.stem] = index_simple_dir(item)
    return result


def index_hierarchy(hierarchical_dir: Path, accept_suffixes: Optional[List[str]]=None, max_level: int=1) -> Dict[str, Dict]:
    result = {}
    for h_item in hierarchical_dir.iterdir():
        if h_item.is_dir():
            sub_result = index_simple_dir(result, accept_suffixes)
            if h_item.stem in result:
                old_value = result[h_item.stem]
                if not isinstance(old_value, dict):
                    raise RuntimeError(f"{h_item} is a directory yet already covered by file")
                deep_merge_dict(old_value, sub_result)
            else:
                result[h_item.stem] = sub_result
        else:
            if accept_suffixes is not None and h_item.suffix[1:] not in accept_suffixes:
                continue
            file_name_parts = h_item.stem.split('_')
            index_level = min(len(file_name_parts) - 1, max_level)
            keys = file_name_parts[:index_level]
            name = '_'.join(file_name_parts[index_level:])
            current = result
            for key in keys:
                if key in current:
                    current = current[key]
                else:
                    _temp = {}
                    current[key] = _temp
                    current = _temp
            current[name] = h_item
    return result

def enumerate_zip_file(zip_path: Path, accept_suffixes: List[str]=[]) -> List[Path]:
    with ZipFile(zip_path) as zip:
        vitrual_assets = map(lambda name: zip_path / name, 
                             filter(lambda name: '__MACOSX' not in name,                # God Damns Apple 
                             filter(lambda name: name.split('.')[-1] in accept_suffixes, 
                                map(lambda info: info.filename, zip.infolist()))))
    return list(vitrual_assets)

def index_voice(current_dir: Path, result_dict: Dict[str, Dict]):
    for zip_file in current_dir.iterdir():
        if zip_file.suffix != '.zip':
            continue
        virtual_assets = enumerate_zip_file(zip_file, AUDIO_SUFFIXES)
        if len(virtual_assets) == 0:
            continue
        # Well, the naming sense is...
        short_key = zip_file.stem
        assets_tri = list(map(lambda va: (va.stem.split('_')[2], va.stem.split('_')[1], va), virtual_assets))
        versions = set(map(lambda tri: tri[0], assets_tri))
        for version in versions:
            if version not in result_dict:
                result_dict[version] = {}
            result_dict[version][short_key] = dict(map(lambda tri: (tri[1], tri[2]),
                                        filter(lambda tri: tri[0] == version, assets_tri)))


def update_index(asset_dir: Path, art_dir_name: Optional[str]):
    index = {}
    if art_dir_name is None:
        art_dir = asset_dir
    else:
        art_dir = asset_dir / art_dir_name
    index['bg'] = index_simple_dir(art_dir / 'bgimage', PIC_SUFFIXES)
    index['cg'] = index_hierarchy(art_dir / 'cg', PIC_SUFFIXES)
    index['fg'] = index_hierarchy(art_dir / 'fgimage', PIC_SUFFIXES, max_level=3)
    index['se'] = index_simple_dir(art_dir / 'se', AUDIO_SUFFIXES)
    # Deal with stance of fg specially
    for chara_id, clothing_dict in index['fg'].items():
        new_charadict = {}
        for clothing_id, stance_dict in clothing_dict.items():
            new_subdict = {}
            for stance_id, expression_dict in stance_dict.items():
                for expression_id, fg_file in expression_dict.items():
                    if expression_id in new_subdict:
                        new_subdict[expression_id][stance_id] = fg_file
                    else:
                        new_subdict[expression_id] = {stance_id: fg_file}
            for expression_id, stance_dict in new_subdict.items():
                if expression_id in new_charadict:
                    new_charadict[expression_id][clothing_id] = stance_dict
                else:
                    new_charadict[expression_id] = {clothing_id: stance_dict}
            index['fg'][chara_id] = new_charadict

    # Deal with voice specially
    new_voice_dict = {}
    index_voice(art_dir / 'voice', new_voice_dict)
    index['voice'] = new_voice_dict
    with open(asset_dir / 'index.pickle', 'wb') as f:
        pickle.dump(index, f)
    return index

def get_index(asset_dir:Path, art_dir_name: Optional[str]='assets'):
    update_flag = False
    index_file = asset_dir / 'index.pickle'
    if index_file.exists():
        update_flag = index_file.stat().st_mtime < asset_dir.stat().st_mtime
    else:
        update_flag = True
    if update_flag:
        print('Updating asset index...')
        return update_index(asset_dir, art_dir_name)
    else:
        with index_file.open('rb') as f:
            return pickle.load(f)
