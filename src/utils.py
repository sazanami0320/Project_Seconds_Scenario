import re

def valid_word_count(meta):
    return sum(map(lambda obj: len(obj['line']), filter(lambda obj: obj['type'] == 'line', meta)))

def sort_chapters(titles, objs):
    title_index_dict = {}
    new_titles = []
    new_objs = []
    recognized_title_pattern = re.compile(r"([A-Z])-(\d+)")
    for index, title in enumerate(titles):
        match = re.fullmatch(recognized_title_pattern, title)
        if match is None:
            print(f"\033[33;1;4mCannot recognize {title}, abort sorting, please check your macros.\033[0m")
            return titles, objs
        else:
            a, n = match.group(1), match.group(2)
            if a not in title_index_dict:
                title_index_dict[a] = {int(n): index}
            else:
                title_index_dict[a][int(n)] = index
    alphas = sorted(list(title_index_dict.keys()))
    for alpha in alphas:
        numerics = sorted(list(title_index_dict[alpha]))
        for numeric in numerics:
            new_titles.append(f"{alpha}-{numeric}")
            new_objs.append(objs[title_index_dict[alpha][numeric]])
    return new_titles, new_objs
