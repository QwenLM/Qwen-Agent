import os


def replace_upload_fname(text, upload_fname_list):
    for full_input_fname in upload_fname_list:
        if full_input_fname not in text and os.path.basename(full_input_fname) in text:
            text = text.replace(os.path.basename(full_input_fname), full_input_fname)
    return text
