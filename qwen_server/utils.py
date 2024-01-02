def is_local_path(path):
    if path.startswith('https://') or path.startswith('http://'):
        return False
    return True
