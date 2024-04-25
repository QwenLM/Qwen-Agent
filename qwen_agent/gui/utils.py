import os


def get_avatar_image(name: str = 'user') -> str:
    if name == 'user':
        return os.path.join(os.path.dirname(__file__), 'assets/user.jpeg')

    return os.path.join(os.path.dirname(__file__), 'assets/logo.jpeg')
