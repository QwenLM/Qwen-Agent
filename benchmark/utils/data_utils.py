import json
import logging

from tqdm import tqdm


def load_jsonl(path):
    data = []
    with open(path, 'r', encoding='utf8') as f:
        for idx, line in enumerate(f, start=1):
            try:
                data.append(json.loads(line))
            except Exception as e:
                logging.info(line)
                logging.warning(f'Error at line {idx}: {e}')
                continue
    return data


def save_jsonl(data, path, progress=False, enabled=True):
    if not enabled:
        return
    with open(path, 'w', encoding='utf-8') as f:
        if progress:
            data = tqdm(data)
        for item in data:
            line = json.dumps(item, ensure_ascii=False)
            print(line, file=f)
