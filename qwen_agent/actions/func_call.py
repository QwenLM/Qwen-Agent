from qwen_agent.tools.tools import call_plugin  # NOQA


def func_call(query, functions, llm):
    messages = [{
        'role': 'user', 'content': query
    }]
    while True:
        rsp = llm.qwen_chat_func(messages, functions)
        if rsp['function_call']:
            yield rsp['content'].strip() + '\n'
            yield 'Action: '+rsp['function_call']['name'].strip() + '\n'
            yield 'Action Input:\n'+rsp['function_call']['arguments'] + '\n'
            bot_msg = {
                'role': 'assistant',
                'content': rsp['content'],
                'function_call': {
                    'name': rsp['function_call']['name'],
                    'arguments': rsp['function_call']['arguments'],
                }
            }
            messages.append(bot_msg)

            obs = call_plugin(rsp['function_call']['name'], rsp['function_call']['arguments'])
            func_msg = {
                'role': 'function',
                'name': rsp['function_call']['name'],
                'content': obs,
            }
            yield 'Observation: ' + obs + '\n'
            messages.append(func_msg)
        else:
            bot_msg = {
                'role': 'assistant',
                'content': rsp['content'],
            }
            yield 'Thought: I now know the final answer.\n'
            yield 'Final Answer: ' + rsp['content']
            messages.append(bot_msg)
            break
