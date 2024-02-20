from qwen_agent.agents import ReActChat
from qwen_agent.llm.schema import Message


def test_react_chat():
    llm_cfg = {'model': 'qwen-max'}
    tools = ['image_gen', 'amap_weather']
    agent = ReActChat(llm=llm_cfg, function_list=tools)

    messages = [Message('user', '海淀区天气')]

    *_, last = agent.run(messages)

    assert '\nAction: ' in last[-1].content
    assert '\nAction Input: ' in last[-1].content
    assert '\nObservation: ' in last[-1].content
    assert '\nThought: ' in last[-1].content
    assert '\nFinal Answer: ' in last[-1].content
