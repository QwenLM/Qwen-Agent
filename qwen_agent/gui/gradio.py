try:
    import gradio as gr
    if gr.__version__ < '4.0':
        raise ImportError('Incompatible "gradio" version detected. '
                          'Please install the correct version with: pip install "gradio>=4.0"')
except (ModuleNotFoundError, AttributeError):
    raise ImportError('Requirement "gradio" not installed. '
                      'Please install it by: pip install -U "gradio>=4.0"')
