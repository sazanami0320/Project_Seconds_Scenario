from .ast import ASTBuilder
from exception import SourcedException

class TSSL:
    '''Tadshi's Simple Scenario Lang'''
    ext = 'vbs'
    def __init__(self, mapper):
        super().__init__()
        self.mapper = mapper

    # Standard makes sure that jinbutsu_str has no spaces
    def parse_jinbutsu(self, src: str, jinbutsu_str: str):
        state = 0
        name = None # Actually this is ID
        alias = None
        expression = None
        for c in jinbutsu_str:
            if state == 0: # Hajime
                if c == '<':
                    state = 2
                    alias = ''
                else:
                    state = 1
                    name = c
            elif state == 1: # Parsing Raw Name:
                if c == '(':
                    state = 4
                    expression = ''
                elif c == '<':
                    state = 2
                    alias = ''
                else:
                    name += c
            elif state == 2: # Parsing alias
                if c == '>':
                    state = 3
                else:
                    alias += c
            elif state == 3: # Name and alias parse finished
                if c == '(':
                    state = 4
                    expression = ''
                else:
                    raise SourcedException(src, f"无法识别人物{jinbutsu_str}.")
            elif state == 4: # Start parsing Hyojo
                if c == ')':
                    state == 'CLOSED'
                else:
                    expression += c
            else:
                raise SourcedException(src, f"无法识别人物{jinbutsu_str}.")
        if name is None:
            name = f"${alias}" # We do not map this
        elif name in self.mapper:
            name = self.mapper[name]
        return name, alias, expression
    
    def parse_system(self, src, sub_system_str: str):
        if '=>' in sub_system_str: # Legacy 
            equal_sign = '=>'
        elif '=' in sub_system_str:
            equal_sign = '='
        elif ':' in sub_system_str:
            equal_sign = ':'
        else:
            equal_sign = None
        if equal_sign:
            left, right = sub_system_str.split(equal_sign)
            left = left.strip()
            right = right.strip()
        else:
            left = 'tachie'
            right = sub_system_str

        if left == 'tachie':
            character, alias, expression = self.parse_jinbutsu(src, right)
            if alias is not None:
                raise SourcedException(src, f"不能在tachie指令中使用alias！")
            assert expression is not None, sub_system_str
            right = (character, expression)
        elif right in self.mapper:
            right = self.mapper[right]
        return left, right
        
    
    def parse_systems(self, src, system_str: str):
        assert(system_str.startswith('[') and system_str.endswith(']')), system_str
        return [self.parse_system(src, sub_system_str.strip()) for sub_system_str in system_str[1:-1].split(',')] 

    def encode(self, scenario: str, filename: str):
        lines = scenario.splitlines()
        builder = ASTBuilder()
        for lineno, line in enumerate(lines):
            self.lineno = lineno + 1
            src = f"{filename}:{self.lineno}"
            line = line.strip()
            try:
                if len(line) == 0:
                    continue
                elif line.startswith(';'):
                    if line.startswith(';;'): # Omote comment
                        builder.comment(src, line[2:].strip())
                elif line.startswith('['):
                    assert line.endswith(']') # Butai Shikake
                    lefts, rights = zip(*self.parse_systems(src, line))
                    builder.systems(src, lefts, rights)
                else:
                    spilt_point = line.index(' ')
                    jinbutsu = line[:spilt_point]
                    chara, alias, expression = self.parse_jinbutsu(src, jinbutsu)

                    serifu = line[spilt_point + 1:]
                    systems = None
                    if serifu.endswith(']'):
                        spilt_point = serifu.index('[')
                        system_str = serifu[spilt_point:]
                        systems = self.parse_systems(src, system_str)
                        serifu = serifu[:spilt_point]
                    builder.line(src, chara, serifu, alias, expression, systems)
            except Exception as e:
                print(f"\033[31;1;4mAt {src}:\033[0m")
                raise e from None
        return builder.finish()
    
    def decode(self, obj):
        raise NotImplementedError('Touching Fish...')
    
