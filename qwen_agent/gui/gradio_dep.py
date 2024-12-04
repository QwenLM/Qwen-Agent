try:
    import gradio as gr
    assert gr.__version__ >= '5.0'
    import modelscope_studio.components.base as ms  # noqa
    import modelscope_studio.components.legacy as mgr  # noqa
except Exception as e:
    raise ImportError('The dependencies for GUI support are not installed. '
                      'Please install the required dependencies by running: pip install "qwen-agent[gui]"') from e
