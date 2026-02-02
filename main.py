import werobot
import os
import dotenv
import json
import command_handler as cmd_hanlder
import db_utils
from werobot.replies import ArticlesReply, Article, ImageReply


dotenv.load_dotenv(dotenv_path='./.env')
token = os.getenv("token")
appSecret = os.getenv("AppSecret")
appID = os.getenv("AppID")
encodingAESKey = os.getenv("EncodingAESKey")

robot = werobot.WeRoBot(token=token, app_id=appID, app_secret=appSecret, encoding_aes_key=encodingAESKey)


# 指令映射字典
command_map = {
    "/帮助": cmd_hanlder.handle_help,
    "/创建队伍": cmd_hanlder.handle_create_team,
    "/加入队伍": cmd_hanlder.handle_join_team,
    "/队伍信息": cmd_hanlder.handle_my_team,
    "/解散队伍": cmd_hanlder.handle_dismiss_team,
    "/退出队伍": cmd_hanlder.handle_quit_team,
    "/修改昵称": cmd_hanlder.handle_change_nickname,
    "/修改队名": cmd_hanlder.handle_change_team_name,

    "/题目": cmd_hanlder.handle_get_chapter,
    "/提交": cmd_hanlder.handle_submit_answer,
    "/查询提交记录": cmd_hanlder.handle_query_submission_history,
    "/提交记录": cmd_hanlder.handle_submission_history,
    "/提示": cmd_hanlder.handle_hints,
    "/解锁提示": cmd_hanlder.handle_unlock_hint,
    "/增加次数": cmd_hanlder.handle_add_submit_count,

    "/查看其他队伍": cmd_hanlder.handle_view_other_team,

    "/发消息": cmd_hanlder.handle_send_team_msg,
    "/消息": cmd_hanlder.handle_view_team_board,

    "/队伍": cmd_hanlder.handle_all_teams,
    "/查看": cmd_hanlder.handle_admin_view_team,
    "/回复": cmd_hanlder.handle_admin_reply_team,
    "/修改点数": cmd_hanlder.handle_update_points,
    "/修改所有队伍点数": cmd_hanlder.handle_update_all_teams_points,
    "/所有记录": cmd_hanlder.handle_all_records,
    "/队伍记录": cmd_hanlder.handle_team_records,
    "/题目记录": cmd_hanlder.handle_puzzle_records,

    "/排行榜": cmd_hanlder.handle_ranking,
    f"{db_utils.VIEW_ENDING_COMMAND}": cmd_hanlder.handle_view_ending,
}

#处理消息
def handle_message(message):
    text = message.content.strip().split()

    # /斜杠开头的是普通用户指令
    if text and text[0][0] == "/":

        '''
        # 维护
        if message.source not in db_utils.ADMIN_USER_IDS:
            return "服务器正在维护，请稍等。"
        '''

        command = text[0]
        params = text[1:] if len(text) > 1 else []
        
        if command not in command_map:
            return "未知指令，请发送 /帮助 查看可用指令"
        
        message_info = {
            "source_id": message.source,  # 用户唯一标识
            "time": message.time
        }
        result = command_map[command](params, message_info)
        
        # 处理图文消息返回
        if isinstance(result, Article):
            reply = ArticlesReply(message=message)
            reply.add_article(result)
            return reply
        else:
            return result
    
    return None


@robot.subscribe
def subscribe_event(message):
    return "欢迎关注！\n请查看公众号文章以了解相关信息！"


@robot.text
def hello(message):
    print(f"Received message:{message.content} (from {message.FromUserName})")

    #分割消息处理指令
    result = handle_message(message)

    return result


# 启动定时任务
db_utils.start_points_timer()

# 让服务器监听在 0.0.0.0:80
robot.config['HOST'] = '0.0.0.0'
robot.config['PORT'] = 80
robot.run()

robot.parse_message()



'''
message参数：

'Content', 'CreateTime', 'FromUserName', 
'MsgId', 'ToUserName'

'content', 'message_id', 'raw', 'source', 'target', 'time', 'type'
'''