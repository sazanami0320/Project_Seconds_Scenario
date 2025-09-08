from analyzer import HomoSapiensText, TSSL, ASTScript
from ir import Unbabel
from kag import KAGMaker
from sys import argv
from index import get_index
import json
from core import WORKSPACE, SCENARIO_DIR, CONFIG_DIR, OUTPUT_DIR, analyze, output_tokens
from utils import sort_chapters

if __name__ == '__main__':
    if len(argv) != 2 and len(argv) != 3:
        print(f"Usage: {argv[0]} <target_folder> [supress_level]")
        exit(1)
    proj_name = argv[1]
    supress_level = int(argv[2]) if len(argv) > 2 else 0
    target_folder = SCENARIO_DIR / proj_name
    if not target_folder.exists():
        raise FileNotFoundError(f"Cannot find scenario {proj_name}.")
# Tokenize and analyze. Note that there are legacy parameters which are no longer used.
    objs = []
    sources = []
    for target_file in target_folder.iterdir():
        if target_file.suffix == '.txt' or target_file.suffix == '.vbs':
            sources.append(target_file)
            objs.append(analyze(argv[1], target_file, TSSL))
    output_folder = OUTPUT_DIR / proj_name
    if not output_folder.exists():
        output_folder.mkdir(parents=True)
# Raw scenario => AST
    titles = list(map(lambda path: path.stem, sources))
    titles, objs = sort_chapters(titles, objs)
    output_tokens(HomoSapiensText(), objs, titles, output_folder / f"{proj_name}.txt", count=True)
    output_tokens(HomoSapiensText(print_expression=True), objs, titles, output_folder / f"{proj_name}_with_expressions.txt")
    output_tokens(ASTScript(), objs, titles, output_folder / f"{proj_name}_ast.json")
# AST => IR
    index = get_index(WORKSPACE / 'assets')
    ir_compiler = Unbabel(CONFIG_DIR / proj_name, index)
    irs = ir_compiler(objs, titles, suppress_level=supress_level)
    with open(output_folder / f"{proj_name}_ir.json", 'w', encoding='utf-8') as f:
        json.dump(irs, f, ensure_ascii=False)
# IR => Instr
    instr_compiler = KAGMaker(CONFIG_DIR / proj_name / 'kag_config.json', index)
    instr_compiler(proj_name, irs, titles) # Auto outputs
