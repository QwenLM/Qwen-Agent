try:
    import gradio as gr
    if gr.__version__ < '4.0':
        raise ImportError('Incompatible "gradio" version detected. '
                          'Please install the correct version with: pip install "gradio>=4.0"')
except (ModuleNotFoundError, AttributeError):
    raise ImportError('Requirement "gradio" not installed. '
                      'Please install it by: pip install -U "gradio>=4.0"')

try:
    import modelscope_studio as mgr  # noqa
except ModuleNotFoundError:
    raise ImportError('Requirement "modelscope-studio" not installed. '
                      'Please install it by: pip install -U "modelscope-studio>=0.2.1"')
