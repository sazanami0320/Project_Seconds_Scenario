from .ast import ASTBuilder

from exception import SourcedException

class HomoSapiensText:
    ext = 'txt'
    def __init__(self, print_expression=False):
        super().__init__()
        self.exp_flag = print_expression

    def _format_system(self, system_object):
        system_type = system_object['type']
        content = system_object['content']
        if system_type == 'background' or system_type == 'cg':
            return f"背景切换为{content}"
        elif system_type == 'transform':
            return f"{content}转场"
        elif system_type == 'sound':
            return f"{content}音效"
        elif system_type == 'effect':
            return f"{content}"
        elif system_type == 'tachie':
            if self.exp_flag:
                return f"{content['cid']}: {content['exp']}"
        elif system_type == 'hide':
            return f"隐藏{content}立绘"
        elif system_type == 'move':
            return f"{content}运镜"
        elif system_type == 'font':
            return f"{content}字体"
        elif system_type == 'filter':
            return f"{content}滤镜"
        elif system_type == 'music':
            return f"{content}音乐"
        elif system_type == 'reset':
            if content == 'move':
                return '重置运镜'
            elif content == 'effect':
                return '重置效果'
            elif content == 'sound':
                return '重置音效'
            elif content == 'focus':
                return '重置镜头'
            elif content == 'cg':
                return '重置CG'
            else:
                raise SourcedException(system_object['src'], f"无法对{content}进行重置。")
        else:
            raise SourcedException(system_object['src'], f"无法识别系统操作类型{system_type}。")
    
    def encode(self, script):
        raise NotImplementedError('Touching Fish')

    def decode(self, object):
        formatted_list = []
        for item in object:
            if item['type'] == 'comment':
                formatted_list.append('//' + item['content'])
            elif item['type'] == 'line':
                if item['cid'] != '旁白':
                    formatted_line = '[' + item['cid'] + ']\t'
                else:
                    formatted_line = ''
                formatted_line += item['line']
                formatted_list.append(formatted_line)
            elif item['type'] == 'systems':
                system_str_list = [self._format_system(system) for system in item['contents']]
                formatted_list.append(f"（{', '.join(system_str_list)}）")
            else:
                raise SourcedException(item['src'], f"无法识别AST节点类型{item['type']}。")
        return '\n'.join(formatted_list)

