from qwen_agent.prompts import Assistant

# config
role_npc = '你扮演一个玩五子棋的高手，你下白棋。棋盘中用0代表无棋子、用1黑棋、用-1白棋。用坐标<i,j>表示位置，i代表行，j代表列，棋盘左上角位置为<0,0>，请决定你要下在哪里，你可以随意下到一个位置，不要说你是AI助手不会下！返回格式为坐标：\n<i,j>\n除了这个坐标，不要返回其他任何内容'
board = '你扮演一个五子棋棋盘，你可以调用代码工具，根据原始棋盘和玩家下棋的位置坐标，把新的棋盘用矩阵展示出来。棋盘中用0代表无棋子、用1表示黑棋、用-1表示白棋。用坐标<i,j>表示位置，i代表行，j代表列，棋盘左上角位置为<0,0>。'
llm_config = {'model': 'qwen-max', 'model_server': 'dashscope'}
function_list = ['code_interpreter']

# init three agent
player_npc = Assistant(llm=llm_config, system_message=role_npc)
board = Assistant(function_list=function_list,
                  llm=llm_config,
                  system_message=board)


# define a result_processing function
def result_processing(response_stream):
    response = []
    for r in response_stream:
        response = r
    print('Bot: ')
    print(response[-1]['content'])
    return response[-1]['content']


# run agent: init chessboard
board_display = ''
position = ''
response_stream = board.run([{'role': 'user', 'content': '初始化一个10*10的棋盘'}])

while True:
    # result processing: Extract the chessboard from the answer
    board_display = result_processing(response_stream)

    # user: play black chess
    print('User input:')
    position = input()

    # run agent: update chessboard
    response_stream = board.run([{
        'role':
        'user',
        'content':
        f'请更新棋盘并打印，原始棋盘是：\n{board_display}\n黑棋玩家刚下在{position}位置'
    }])
    board_display = result_processing(response_stream)

    # run agent: play white chess
    response_stream = player_npc.run([{
        'role':
        'user',
        'content':
        f'当前棋盘是：\n{board_display}\n，请下白棋'
    }])
    position = result_processing(response_stream)

    # run agent: update chessboard
    response_stream = board.run([{
        'role':
        'user',
        'content':
        f'请更新棋盘并打印，原始棋盘是：\n{board_display}\n白棋玩家刚下在{position}位置'
    }])
