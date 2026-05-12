from qwen_agent.utils.utils import merge_generate_cfgs


def test_merge_generate_cfgs_drops_redundant_stop_prefixes():
    generate_cfg = merge_generate_cfgs(
        base_generate_cfg={
            'stop': [
                '✿RESULT✿',
                '✿RETURN✿',
                'Observation:',
            ],
        },
        new_generate_cfg={
            'stop': [
                'Observation:\n',
                '"], "instruction":',
            ],
        },
    )

    assert generate_cfg['stop'] == [
        '✿RESULT✿',
        '✿RETURN✿',
        'Observation:',
        '"], "instruction":',
    ]


def test_merge_generate_cfgs_keeps_shorter_stop_word():
    generate_cfg = merge_generate_cfgs(
        base_generate_cfg={'stop': ['Observation:\n']},
        new_generate_cfg={'stop': ['Observation:']},
    )

    assert generate_cfg['stop'] == ['Observation:']
