action_list = {
    'ghostwriter': {
        'summarize': 'summarize the main content of reference materials',
        'outline': 'write outline',
        'expand': 'expand text'
    }
}


def get_action_list(task):
    return action_list[task]
