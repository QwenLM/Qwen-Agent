import re

from setuptools import find_packages, setup


def get_version() -> str:
    with open('qwen_agent/__init__.py', encoding='utf-8') as f:
        version = re.search(
            r'^__version__\s*=\s*[\'"]([^\'"]*)[\'"]',
            f.read(),
            re.MULTILINE,
        ).group(1)
    return version


def read_requirements():
    with open('requirements.txt') as req:
        content = req.read()
        requirements = content.split('\n')

    # Note: `pip install qwen-agent` by default installs the following deps for code_interpreter.
    # However, if you do not want these optional deps, you can install qwen-agent via the following:
    # ```bash
    # curl -O https://raw.githubusercontent.com/QwenLM/Qwen-Agent/main/requirements.txt;
    # pip install -r requirements.txt;
    # pip install -U --no-deps qwen-agent;
    # ```
    code_interpreter_deps = [
        'anyio>=3.7.1',
        'fastapi>=0.103.1',
        'jupyter>=1.0.0',
        'matplotlib',
        'numpy',
        'pandas',
        'pillow',
        'seaborn',
        'sympy',
        'uvicorn>=0.23.2',
    ]
    requirements.extend(code_interpreter_deps)

    return requirements


def read_description() -> str:
    with open('README.md', 'r', encoding='UTF-8') as f:
        long_description = f.read()
    return long_description


setup(
    name='qwen-agent',
    version=get_version(),
    author='Qwen Team',
    author_email='tujianhong.tjh@alibaba-inc.com',
    description='Qwen-Agent: Enhancing LLMs with Agent Workflows, RAG, Function Calling, and Code Interpreter.',
    long_description=read_description(),
    long_description_content_type='text/markdown',
    keywords=['LLM', 'Agent', 'Function Calling', 'RAG', 'Code Interpreter'],
    packages=find_packages(exclude=['examples', 'examples.*', 'qwen_server', 'qwen_server.*']),
    package_data={
        'qwen_agent': [
            'utils/qwen.tiktoken', 'tools/resource/*.ttf', 'tools/resource/*.py', 'gui/assets/*.css',
            'gui/assets/*.jpeg'
        ],
    },
    install_requires=read_requirements(),
    extras_require={
        'gui': [
            'gradio==4.21.0',
            'modelscope-studio>=0.4.0',
        ],
    },
    url='https://github.com/QwenLM/Qwen-Agent',
)
