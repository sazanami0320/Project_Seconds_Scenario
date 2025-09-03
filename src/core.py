from pathlib import Path
from analyzer import TSSL, ASTScript
from utils import valid_word_count
import json

WORKSPACE = Path(__file__).resolve().parent.parent
SCENARIO_DIR = WORKSPACE / 'scenario'
CONFIG_DIR = WORKSPACE / 'config'
OUTPUT_DIR = WORKSPACE / 'output'

def read_scenario(target_file: Path):
    try:
        with target_file.open('r', encoding='utf-8') as f:
            return f.read()
    except UnicodeEncodeError as e:
        with target_file.open('r', encoding='gb2312') as f:
            return f.read()

def analyze(proj_name: str, target_file: Path, base_class):
    if base_class is TSSL:
        with open(CONFIG_DIR / proj_name / 'tssl_map.json', 'r', encoding='utf-8') as f:
            tssl_config = json.load(f)
        instance = TSSL(tssl_config)
    else:
        instance = base_class()

    return instance.encode(read_scenario(target_file), filename=target_file.stem)

def output_tokens(instance, objs, titles, targe_file, *args, count=False, **kwargs):
    json_flag = isinstance(instance, ASTScript)
    total_count = 0
    with targe_file.open('w', encoding='utf-8') as f:
        if json_flag:
            f.write('[\n')
        for index, (title, meta_obj) in enumerate(zip(titles, objs)):
            if count:
                word_count = valid_word_count(meta_obj)
                total_count += word_count
                print(f"{title}: {word_count} characters processed.")
            f.write(instance.decode(meta_obj, *args, **kwargs))
            if json_flag and index < len(objs) - 1:
                f.write(',\n')
        if json_flag:
            f.write(']\n')
    if count:
        print(f"{total_count} characters processed in total.")
