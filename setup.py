from setuptools import find_packages, setup


def read_requirements():
    with open('requirements.txt') as req:
        content = req.read()
        requirements = content.split('\n')
    return requirements


setup(
    name='qwen_agent',
    version='0.0.1',
    packages=find_packages(
        exclude=['examples', 'examples.*', 'qwen_server', 'qwen_server.*']),
    package_data={
        'qwen_agent':
        ['utils/qwen.tiktoken', 'tools/resource/*.ttf', 'tools/resource/*.py'],
    },
    install_requires=read_requirements(),
    url='https://github.com/QwenLM/Qwen-Agent')
