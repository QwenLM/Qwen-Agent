import base64


def covert_image_to_base64(image_path):
    ext = image_path.split('.')[-1]
    if ext not in ['gif', 'jpeg', 'png']:
        ext = 'jpeg'

    with open(image_path, 'rb') as image_file:
        # Read the file
        encoded_string = base64.b64encode(image_file.read())

        # Convert bytes to string
        base64_data = encoded_string.decode('utf-8')

        base64_url = f'data:image/{ext};base64,{base64_data}'
        return base64_url


def format_cover_html(bot_name, bot_description, bot_avatar):
    if bot_avatar:
        image_src = covert_image_to_base64(bot_avatar)
    else:
        image_src = '//img.alicdn.com/imgextra/i3/O1CN01YPqZFO1YNZerQfSBk_!!6000000003047-0-tps-225-225.jpg'
    return f"""
<style>
    body.dark-mode .bot_cover {{
        background-color: #222;
        color: #fff;
    }}

    .bot_cover {{
        display: flex;
        flex-direction: column;
        align-items: center;
        text-align: center;
        padding: 20px;
        border-radius: 8px;
        box-shadow: 0 4px 8px rgba(0, 0, 0, 0.1);
    }}
    .bot_avatar img {{
        width: 150px;
        height: 150px;
        object-fit: cover;
        border-radius: 50%;
        margin-bottom: 10px;
    }}
    .bot_name {{
        font-size: 18px;
        font-weight: bold;
        margin-bottom: 5px;
    }}
    .bot_desp {{
        font-size: 14px;
        line-height: 1.5;
    }}
</style>

<div class="bot_cover">
    <div class="bot_avatar">
        <img src="{image_src}" />
    </div>
    <div class="bot_name">{bot_name}</div>
    <div class="bot_desp">{bot_description}</div>
</div>
"""
