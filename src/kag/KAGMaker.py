from core import OUTPUT_DIR
from pathlib import Path
from .stage import Stage
from .effect import EffectManager
import json

class KAGMaker:
    def __init__(self, config_dir: Path, asset_index: dict):
        self.kag_lines = None
        # A set of used chara ids i.e. tags.
        # List can keep the order of charas.
        self.chara_list = []
        self.asset_index = asset_index
        self.cg_mode = False # Whether we are showing a CG.
        self.background = None
        # Config and others
        with config_dir.open('r', encoding='utf-8') as f:
            self.config = json.load(f)
        self.name_map = self.config['name_map']
        markers = self.config['markers']
        heights = self.config['heights']
        self.stage = Stage(markers, heights, asset_index, self.writeln)
        self.effect_manager = EffectManager(self.writeln, self.stage)
        # Variables for line hooks
        self.transform_cache = None
        self.font_cache = None
        self.voice_flag = False
    
    def __call__(self, *args, **kwds):
        proj_name, irs, names = args
        for chapter_index in range(len(irs)):
            name = names[chapter_index]
            output_path = OUTPUT_DIR / proj_name / f"{name}.ks"
            self.kag_lines = []
            self.writeln(f"*start|{name}")
            self.writeln(f"@dia")
            self.writeln(f"@history output=\"true\"")
            for item in irs[chapter_index]:
                if item['type'] == 'comment':
                    self.writeln(f";[剧本注]{item['content']}")
                elif item['type'] == 'macro':
                    macro_name = item['name']
                    if macro_name == 'setclothing':
                        self.stage.set_clothing(item['target'], item['clothing'])
                    else:
                        raise RuntimeError(f"Cannot recognize macro type {macro_name}.")
                elif item['type'] == 'line':
                    self.pre_line_hook()
                    chara_id = item['cid']
                    self.stage.tick_line(item['id'], chara_id, render=not self.cg_mode)
                    if 'voice' in item:
                        self.writeln(f"@vo storage=\"{item['voice']}\"")
                        self.voice_flag = True
                    if chara_id.startswith('$'): # Take this as an NPC
                        self.writeln(f"@npc id=\"{item['alias']}\"")
                    elif chara_id == '旁白':
                        self.writeln(f"@r")
                    else:
                        if chara_id in self.name_map:
                            chara_id = self.name_map[chara_id]
                        if chara_id not in self.chara_list:
                            self.chara_list.append(chara_id)
                        if 'alias' in item:
                            # namelist.tjs actually compiles into npc macros.
                            # So as long as we do not play with fontcolor, this is correct:
                            chara_command = f"@npc id=\"{item['alias']}\""
                        else:
                            chara_command = f"@{chara_id}"
                        self.writeln(chara_command)
                    if self.font_cache is not None:
                        self.writeln(f"@font size=\"{self.font_cache}\"")
                    self.writeln(f"{item['line']} [w]") # default w
                    self.post_line_hook()
                elif item['type'] == 'systems':
                    for system_item in item['content']:
                        self.compile_system(system_item)
            if chapter_index == len(irs) - 1:
                self.writeln('@gotostart')
            else:
                self.writeln(f"@jump storage=\"{names[chapter_index + 1]}.ks\"")
            with output_path.open('w', encoding='utf-8') as f:
                f.writelines(self.kag_lines)
        # Try to generate a namelist for futher edit. Is this really necessary?
        if '主角' in self.chara_list:
            # Syujinko or Die!
            index = self.chara_list.index('主角')
            self.chara_list.pop(index)
            # NVLMaker assumes that the first item is Syujinko while the second one is passers-by.
            self.chara_list.insert(0, '主角')
        with open(OUTPUT_DIR / proj_name / 'appendix' / 'macro_name.ks', 'w', encoding='utf-8') as f:
            f.write('*start\n')
            for index, chara_tag in enumerate(self.chara_list):
                f.writelines([
                    f"[macro name={chara_tag}]\n",
                    f"[npc * id={chara_tag} color=0xfdeff2]\n",
                    '[endmacro]\n',
                ])
            f.write('[return]\n')
        with open(OUTPUT_DIR / proj_name / 'appendix' / 'namelist.tjs', 'w', encoding='utf-8') as f:
            self.chara_list.insert(1, '路人')
            f.write('(const) [\n')
            for index, chara_tag in enumerate(self.chara_list):
                f.writelines([
                    ' (const) %[\n',
                    f"  \"name\" => \"{chara_tag}\",\n",
                    '  "face" => "",\n',
                    '  "color" => "0xfdeff2",\n'
                    f"  \"tag\" => \"{chara_tag}\"\n"
                    ' ]'
                ])
                if index < len(self.chara_list) - 1:
                    f.write(',') # In case nvlmaker does not recognize trailing comma
                f.write('\n')
            f.write(']\n')
        
        self.kag_lines = None

    def compile_system(self, system: dict):
        # Dirty works now, guys.
        # We try to convert some simple instr here.
        # Well, I do not expect that I will be responsible of this.
        system_type = system['type']
        content = system['content']
        if system_type == 'background':
            if self.transform_cache:
                transform_cache = self.transform_cache
                self.transform_cache = None
                self.writeln(';Transition')
                self.compile_system({'type': 'background', 'content': transform_cache})
            self.background = content
            # EXPERIMENTAL!
            self.effect_manager.reset_effect()
            self.writeln('@backlay')
            self.writeln(f"@image layer=\"stage\" page=\"back\" storage=\"{content}\" visible=\"true\"")
            if self.cg_mode:
                self.stage.render_on_back()
                self.cg_mode = False
            else:
                self.stage.clear_fg(page='back')
            self.writeln('@trans method=\"crossfade\" time=\"700\"')
            self.writeln('@wt')
            self.stage.reset_record()
        elif system_type == 'cg':
            self.writeln('@backlay')
            if not self.cg_mode:
                self.enter_cg_mode()
            self.writeln(f"@image layer=\"stage\" page=\"back\" storage=\"{content}\" visible=\"true\"")
            self.writeln('@trans method=\"crossfade\" time=\"700\"')
            self.writeln('@wt')
        elif system_type == 'sound':
            self.writeln(f"@se storage=\"{content}\"")
            self.writeln('@ws canskip=\"true\"')
        elif system_type == 'tachie':
            if content['exp'].startswith('<'):
                return
            self.stage.parse_chara_command(content['cid'], content['exp'].split('_')[1])
        elif system_type == 'hide':
            if content == '全部':
                self.writeln('@backlay')
                self.stage.clear_fg(page='back')
                self.writeln('@trans method=\"crossfade\" time=\"500\"')
                self.writeln('@wt')
                self.stage.reset_record()
            else:
                self.stage.parse_hide_command(content)
        elif system_type == 'reset':
            if content == 'cg':
                self.stage.render_on_back()
                self.writeln('@trans time="200" method="crossfade"')
                self.writeln('@wt')
                self.cg_mode = False
            elif content == 'sound':
                self.writeln('@stopse')
            elif content == 'effect' or content == 'move':
                self.effect_manager.reset_effect()
            else: # e.g. zoom effect
                self.writeln(f";[需求]重置{content}")
        elif system_type == 'transform':
            if content == 'black' or content == 'blackout':
                self.transform_cache = 'black'
            elif content == 'crossfade':
                pass
            else:
                self.writeln(f";[需求]{system_type} = {content}")
        elif system_type == 'effect' or system_type == 'move':
            self.effect_manager.parse_effect(content)
        elif system_type == 'font':
            if content == '放大':
                self.font_cache = 80
        else: # Transforms, move of focus, and many others:
            self.writeln(f";[需求]{system_type} = {content}")
    
    def pre_line_hook(self):
        if self.transform_cache:
            self.writeln(';==Transition==')
            self.writeln('@backlay')
            self.stage.clear_fg(page='back')
            self.writeln(f"@image layer=\"stage\" page=\"back\" storage=\"{self.transform_cache}\" time=\"1000\" visible=\"true\"")
            self.writeln('@trans method="crossfade" time="1000"')
            self.writeln('@wt')
            self.writeln('@backlay')
            self.writeln(f"@image layer=\"stage\" page=\"back\" storage=\"{self.background}\" time=\"1000\" visible=\"true\"")
            self.writeln('@trans method="crossfade" time="1000"')
            self.writeln('@wt')
            self.writeln(f"@backlay")
            self.writeln(';==End Transition==')
            self.transform_cache = None

    def post_line_hook(self):
        if self.font_cache:
            self.writeln('@resetfont')
            self.font_cache = None
        if self.voice_flag:
            # Included in [w]
            # self.writeln('@endvo')
            self.voice_flag = False

    def enter_cg_mode(self):
        self.stage.clear_fg(page='back')
        self.cg_mode = True
    
    def writeln(self, line: str):
        self.kag_lines.append(f"{line}\n")