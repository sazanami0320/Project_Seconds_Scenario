
from typing import List, Dict, Optional, Any
import json
import hashlib

from exception import SourcedException

class ASTBuilder:
    ''' For obvious reasons, the genkou/scenario of our game should be imperative;
        And for the same reasons, the scenario should also be imperative.
        However, there are inevitably some redundant or inferrable infomation in the scenario, 
        which can be a Odysssey for the playwrights if they have to write it through every line.
        Also, composers and voice actors(actually AI though) need to access the state of stage frequently.
        As the result, I decided to write a IR which traverse through every single line and record their states.
        However, it turns out that nobody need a simple ST without details, so I combined that IR into AST to
        eliminate extra passes.
        Short version: AST tracks stage change. It is even not an AST actually, so why not.'''

    def __init__(self, hash_len:int = 8):
        self.content = []
        self.stacked_bg = None
        self.bg = 'black'
        self.cg_mode = False
        self.characters = {}
        self.hash_len = hash_len
        self.hash_counts = {}

    def make_id(self, cid: str, serifu: str):
        hasher = hashlib.sha256(b"Project Seconds!")
        hasher.update(cid.encode('utf-8')) # Add cid in hash to avoic cases like 'The Shadow'
        hasher.update(serifu.encode('utf-8'))
        hash_str = hasher.hexdigest()[:self.hash_len - 1]
        if hash_str in self.hash_counts:
            count = self.hash_counts[hash_str]
            self.hash_counts[hash_str] = count + 1
            hash_str += hex(count)[2:]
        else:
            self.hash_counts[hash_str] = 1
            hash_str += '0'
        return hash_str

    def comment(self, src: str, comment: str):
        self.content.append({
            'type': 'comment',
            'src': src,
            'content': comment
        })

    def line(self, src: str, jinbutsu: str, serifu: str, alias: Optional[str]=None, hyojyo: Optional[str]=None, systems: Optional[List[Any]]=None):
        if systems is not None:
            self.systems(src, *zip(*systems))
        if hyojyo is not None: # Alias system.tachie and functions most lately
            self.systems(src, 'tachie', (jinbutsu, hyojyo))
        # We should keep the body short and stout to spare disk usage and make it more readable.
        # And if you know what I mean, no, this is a coffee machine.
        line = {
            'type': 'line',
            'bg': self.bg,
            'src': src,
            'id': self.make_id(jinbutsu, serifu),
            'cid': jinbutsu,
            'line': serifu,
        }
        if self.characters:
            line['charas'] = self.characters.copy()
        if alias is not None:
            line['alias'] = alias
        self.content.append(line)
    
    def macro(self, src: str, macro_content:str):
        macro_parts = macro_content.split(' ')
        macro_name = macro_parts[0]
        macro = {
            'type': 'macro',
            'name': macro_name
        }
        if macro_name.lower() == 'setclothing':
            if len(macro_parts) != 3:
                raise SourcedException(src, 'Illegal setclothing Macro!')
            macro['target'] = macro_parts[1]
            macro['clothing'] = macro_parts[2]
        else:
            raise SourcedException(src, f"Fail to resolve macro {macro_content}")
        self.content.append(macro)
    
    def systems(self, src: str, responsibles: str | List[str], works: Any):
        if isinstance(responsibles, str):
            responsibles = [responsibles]
            works = [works]
        if len(self.content) > 0 and self.content[-1]['type'] == 'systems':
            target = self.content[-1]['contents']
        else:
            target = []
            self.content.append({
                'type': 'systems',
                'contents': target
            })
        for responsible, work in zip(responsibles, works):
            if responsible == 'tachie':
                chara, expression = work
                self.characters[chara] = expression
                work = {
                    'cid': chara,
                    'exp': expression
                }
            elif responsible == 'background':
                self.bg = work
                self.cg_mode = False
            elif responsible == 'cg':
                # A CG cannot contains any tachie.
                # However, you can still give them expressions... via tachie.
                # So we do not clear characters here.
                # Yes, I know tachie is not a good name now, finally.
                # Maybe you can consider this like CG is always shown in the top layer
                # and all tachie are covered by CG.
                if self.cg_mode: # Satsubun case
                    self.stacked_bg = self.bg
                self.bg = work
                self.cg_mode = True
            elif responsible == 'hide':
                if work == '全部': 
                    self.characters.clear()
                else:
                    if work in self.characters:
                        self.characters.pop(work)
                    else:
                        raise SourcedException(src, f"Trying to hide {work}'s tachie, who is not even on stage!")
            elif responsible == 'reset':
                if work == 'cg':
                    if not self.cg_mode:
                        raise SourcedException(src, 'Cannot exit CG while no CG is shown!')
                    self.cg_mode = False
            elif responsible == 'transform':
                self.characters.clear() # If we transform, then clear tachie?
            target.append({
                'type': responsible,
                'src': src,
                'content': work,
            })

    def finish(self) -> List[Dict]:
        content = self.content
        self.content = None
        return content
    
class ASTScript:
    ext = 'json'
    def encode(self, script):
        return json.loads(script)

    def decode(self, obj):
        return json.dumps(obj, ensure_ascii=False)
