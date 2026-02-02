import db_utils  # 导入我们写的数据库工具函数
import datetime
import json

def handle_help(params, message_info):
    '''/帮助'''
    return f"请参考帮助菜单：\n{db_utils.HELP_MENU_URL}"


def handle_create_team(params, message_info):
    """/创建队伍 [0]队伍名 [1]队长昵称"""
    if len(params) != 2:
        return "指令格式错误！\n正确用法：/创建队伍 [队伍名] [你的昵称]"
    team_name = params[0]
    creator_name = params[1]
    creator_id = message_info["source_id"]
   
    # 调用数据库函数创建队伍
    success, msg, team_id, invitation_code = db_utils.create_team(team_name, creator_id, creator_name)
    if success:
        return f"{msg}\n队伍名：{team_name}\n队伍ID：{team_id}\n邀请码：{invitation_code}\n（请告知队友ID与邀请码，用于加入）"
    else:
        return f"{msg}"


def handle_join_team(params, message_info):
    """/加入队伍 队伍id 邀请码 昵称"""
    if len(params) != 3:
        return "指令格式错误！正确用法：/加入队伍 [队伍ID] [邀请码] [你的昵称]"
    team_id = params[0]
    invitation_code = params[1]
    user_name = params[2]
    user_id = message_info["source_id"]  # 从消息中获取真实用户ID
   
    success, msg = db_utils.join_team(team_id, user_id, user_name, invitation_code)
    return f"{'✅' if success else '❌'} {msg}"


def handle_my_team(params, message_info):
    """/队伍信息"""
    user_id = message_info["source_id"]
    team = db_utils.get_user_team(user_id)
    if team:
        members = db_utils.get_team_members(team["team_id"])
        member_count = len(members)
        limit = db_utils.TEAM_MEMBER_LIMIT
        
        # 处理完赛信息
        completion_status = "已完赛" if team["is_completed"] else "未完赛"
        completed_time_str = ""
        if team["is_completed"] and team["completed_time"]:
            # 转换小时为xx:xx:xx格式
            hours = team["completed_time"]
            total_seconds = int(hours * 3600)
            h = total_seconds // 3600
            m = (total_seconds % 3600) // 60
            s = total_seconds % 60
            completed_time_str = f" | 完赛用时：{h:02d}:{m:02d}:{s:02d}"
        
        members_str = "\n".join([
            f"{'👑 ' if m['is_leader'] else '   '}{m['user_name']}（加入时间：{m['join_time']}）"
            for m in members
        ])
        return (
            f"📢 你的队伍信息：\n"
            f"队伍名：{team['team_name']}\n"
            f"队伍ID：{team['team_id']}\n"
            f"创建时间：{team['create_time']}\n"
            f"完赛状态：{completion_status}{completed_time_str}\n"
            f"当前章节数：{team['current_chapter_id']}\n"
            f"已通过题目数：{team['passed_puzzle_count']}\n"
            f"当前{db_utils.POINT_NAME}：{team['points']}({db_utils.ADD_POINT_PER_MINUTE}/min)\n"
            f"队员列表（{member_count}/{limit}人）：\n{members_str}"
        )
    else:
        return "❌ 你还没有加入任何队伍！"


def handle_dismiss_team(params, message_info):
    """/解散队伍（无需参数，仅队长可解散自己的队伍）"""
    if db_utils.is_competition_started():
        return f"⏰ 比赛已开始，无法解散队伍"
    
    if len(params) != 0:
        return "指令格式错误！\n正确用法：/解散队伍（无需参数）"
    
    user_id = message_info["source_id"]
    success, msg = db_utils.dismiss_team(user_id)
    return f"{'✅' if success else '❌'} {msg}"


def handle_quit_team(params, message_info):
    """/退出队伍（无需参数，队员可退出当前队伍）"""
    if db_utils.is_competition_started():
        return f"⏰ 比赛已开始，无法退出队伍"
    
    if len(params) != 0:
        return "指令格式错误！\n正确用法：/退出队伍（无需参数）"
    
    user_id = message_info["source_id"]
    success, msg = db_utils.quit_team(user_id)
    return f"{'✅' if success else '❌'} {msg}"


def handle_change_team_name(params, message_info):
    """/修改队名 [新队名]"""
        # 检查开赛状态
    if db_utils.is_competition_started():
        return f"⏰ 比赛已开始，无法修改队名"
    
    if len(params) != 1:
        return "指令格式错误！\n正确用法：/修改队名 [新队名]"
    
    new_team_name = params[0]
    user_id = message_info["source_id"]
    
    success, msg = db_utils.change_team_name(user_id, new_team_name)
    return f"{'✅' if success else '❌'} {msg}"


def handle_change_nickname(params, message_info):
    """/修改昵称 [新昵称]"""
    if db_utils.is_competition_started():
        return f"⏰ 比赛已开始，无法修改昵称"
    
    if len(params) != 1:
        return "指令格式错误！\n正确用法：/修改昵称 [新昵称]"
    
    new_nickname = params[0]
    user_id = message_info["source_id"]
    
    success, msg = db_utils.change_user_nickname(user_id, new_nickname)
    return f"{'✅' if success else '❌'} {msg}"

# ------------------------------
# 题目相关
# ------------------------------
def handle_get_chapter(params, message_info):
    """/题目 [章节名] - 返回对应章节的图文信息"""
    # 检查开赛状态
    if not db_utils.is_competition_started():
        return f"⏰ 比赛尚未开始\n开赛时间：{db_utils.get_start_time()}"

    # 检查参数格式
    if len(params) != 1:
        return "参数格式错误！正确格式：/题目 [章节名]"
    
    chapter_name = params[0]
    
    # 检查用户是否在队伍中
    user_id = message_info["source_id"]
    team = db_utils.get_user_team(user_id)
    if not team:
        return "您尚未加入任何队伍，请先创建或加入队伍"
    
    chapter_id = db_utils.get_chapter_id(chapter_name)

    # 检查章节是否存在
    if not chapter_id:
        return f"该章节未解锁或不存在"
    
    # 检查章节是否已解锁，返回相同信息
    if chapter_id > team["current_chapter_id"]:
        return f"该章节未解锁或不存在"
    
    # 获取章节信息
    puzzle_info = db_utils.load_puzzle_info()
    target_chapter = None
    for chapter in puzzle_info["chapters"]:
        if chapter["id"] == chapter_id:
            target_chapter = chapter
            break
    
    if not target_chapter:
        return "未找到该章节信息"
    
    # 创建Article对象
    from werobot.replies import Article
    return Article(
        title=f"#{chapter_id} " + target_chapter["name"],
        description=target_chapter.get("news_description", ""),
        img=target_chapter.get("news_img", ""),
        url=target_chapter.get("news_url", "")
    )

def get_puzzle_unlock_time(team_id, chapter_id, puzzle_id):
        """获取题目解锁时间"""
        conn = db_utils.get_db_connection()
        cursor = conn.cursor()
        try:
            cursor.execute('''
                SELECT unlock_time FROM team_puzzle_status 
                WHERE team_id = ? AND chapter_id = ? AND puzzle_id = ?
            ''', (team_id, chapter_id, puzzle_id))
            res = cursor.fetchone()
            return res[0] if res else None
        finally:
            conn.close()

def handle_submit_answer(params, message_info):
    """处理提交答案命令"""
    # 检查开赛状态
    if not db_utils.is_competition_started():
        return f"⏰ 比赛尚未开始\n开赛时间：{db_utils.get_start_time()}"
    
    user_id = message_info["source_id"]  # 获取当前用户ID
    
    # 检查参数格式（至少需要章节名、题目序号、答案（可多个词））
    if len(params) < 3:
        return "参数格式错误！正确格式：/提交 [区域名称] [题目序号] [答案]"
    
    # 解析参数：前两项为章节名和题目序号，剩余所有项合并为答案
    chapter_name = params[0]
    puzzle_id_str = params[1]
    # 合并剩余参数作为答案
    user_answer = ''.join(params[2:])
    # 处理为小写
    user_answer = user_answer.lower()

    # 滤去不可见字符
    clean_answer = ''.join(filter(lambda c: not c.isspace(), user_answer))
    
    # 检查用户是否在队伍中
    team_id = db_utils.get_user_team_id(user_id)
    if not team_id:
        return "您尚未加入任何队伍，请先创建或加入队伍"
    
    # 验证题目序号
    try:
        puzzle_id = int(puzzle_id_str)
    except ValueError:
        return "题目序号必须是数字"
    
    chapter_id = db_utils.get_chapter_id(chapter_name)

    # 检查章节是否存在
    if not chapter_id:
        return f"该章节未解锁或不存在"
    
    # 验证是否存在以及是否解锁
    if not db_utils.is_puzzle_unlocked(team_id, chapter_id, puzzle_id):
        return "该章节未解锁或不存在"


    # 提交答案
    success, msg, is_correct = db_utils.submit_puzzle_answer(
        team_id, chapter_id, puzzle_id, clean_answer, user_id
    )
    
    return f"{msg}"
    

def handle_query_submission_history(params, message_info):
    """/查询提交记录 [章节名] [题目序号] [可选页码] - 分页显示指定章节和题目的提交记录"""
    # 检查开赛状态
    if not db_utils.is_competition_started():
        return f"⏰ 比赛尚未开始\n开赛时间：{db_utils.get_start_time()}"
    
    user_id = message_info["source_id"]
    
    # 检查用户是否在队伍中
    team_id = db_utils.get_user_team_id(user_id)
    if not team_id:
        return "您尚未加入任何队伍，请先创建或加入队伍"
    
    # 检查参数格式（至少需要章节名和题目序号）
    if len(params) < 2:
        return "参数格式错误！正确格式：/查询提交记录 [章节名] [题目序号] [可选页码]"
    
    # 解析章节名
    chapter_name = params[0]
    
    # 解析题目序号
    try:
        puzzle_id = int(params[1])
    except ValueError:
        return "题目序号必须是数字"
    
    chapter_id = db_utils.get_chapter_id(chapter_name)

    # 检查章节是否存在
    if not chapter_id:
        return f"该章节未解锁或不存在"
    
    # 验证是否存在以及是否解锁
    if not db_utils.is_puzzle_unlocked(team_id, chapter_id, puzzle_id):
        return "该章节未解锁或不存在"
    
    # 解析页码参数（默认第一页）
    page = 1
    if len(params) >= 3:
        try:
            page = int(params[2])
            if page < 1:
                return "页码必须大于等于1"
        except ValueError:
            return "页码必须是数字"
    
    # 获取分页数据（筛选指定章节和题目）
    history_data = db_utils.get_team_submission_history(
        team_id, chapter_id, puzzle_id, page=page, per_page=10  # 每页10条
    )
    
    if not history_data["records"]:
        return f"区域[{chapter_name}]第{puzzle_id}题暂无提交记录"
    
    # 格式化输出
    result = (f"📝 区域[{chapter_name}]第{puzzle_id}题提交记录（第{history_data['current_page']}/"
              f"{history_data['total_pages']}页）：\n")
    for record in history_data["records"]:
        result += (
            f"[{record['chapter_name']}{record['puzzle_id']}-{record['puzzle_name']}]\n"
            f"昵称：{record['user_name']}\n"
            f"答案：{record['submitted_answer']}\n"
            f"结果：{'✅正确' if record['result'] == 'correct' else '🚩里程碑' if record['result'] == 'milestone' else '❌错误'}\n"
            f"时间：{record['submit_time']}\n\n"
        )
    
    # 分页导航
    nav = []
    if history_data["current_page"] > 1:
        nav.append(f"上一页：/查询提交记录 {chapter_name} {puzzle_id} {history_data['current_page'] - 1}")
    if history_data["current_page"] < history_data["total_pages"]:
        nav.append(f"下一页：/查询提交记录 {chapter_name} {puzzle_id} {history_data['current_page'] + 1}")
    
    if nav:
        result += "分页导航：\n" + "\n".join(nav)
    
    return result


def handle_submission_history(params, message_info):
    """/提交记录 [可选页码] - 分页显示所有提交记录"""
    # 检查开赛状态
    if not db_utils.is_competition_started():
        return f"⏰ 比赛尚未开始\n开赛时间：{db_utils.get_start_time()}"
    
    user_id = message_info["source_id"]
    
    # 检查用户是否在队伍中
    team_id = db_utils.get_user_team_id(user_id)
    if not team_id:
        return "您尚未加入任何队伍，请先创建或加入队伍"
    
    # 解析页码参数（默认第一页）
    page = 1
    if params:
        try:
            page = int(params[0])
            if page < 1:
                return "页码必须大于等于1"
        except ValueError:
            return "页码必须是数字"
    
    # 获取分页数据（不筛选区域和题目，显示所有记录）
    history_data = db_utils.get_team_submission_history(
        team_id, page=page, per_page=10  # 每页10条
    )
    
    if not history_data["records"]:
        return "暂无提交记录"
    
    chapter_name_to_id = db_utils.get_chapter_name_to_id()

    # 格式化输出
    result = f"📝 提交记录（第{history_data['current_page']}/{history_data['total_pages']}页）：\n"
    for record in history_data["records"]:
        chapter_name = next(
            (k for k, v in chapter_name_to_id.items() if v == record["chapter_id"]),
            str(record["chapter_id"])
        )
        result += (
            f"[{chapter_name}{record['puzzle_id']}-{record['puzzle_name']}]\n"
            f"昵称：{record['user_name']}\n"
            f"答案：{record['submitted_answer']}\n"
            f"结果：{'✅正确' if record['result'] == 'correct' else '🚩里程碑' if record['result'] == 'milestone' else '❌错误'}\n"
            f"时间：{record['submit_time']}\n\n"
        )
    
    # 分页导航
    nav = []
    if history_data["current_page"] > 1:
        nav.append(f"上一页：/提交记录 {history_data['current_page'] - 1}")
    if history_data["current_page"] < history_data["total_pages"]:
        nav.append(f"下一页：/提交记录 {history_data['current_page'] + 1}")
    
    if nav:
        result += "分页导航：\n" + "\n".join(nav)
    
    return result


def handle_add_submit_count(params, message_info):
    """/增加次数 [章节名] [题目序号] - 花费点数增加指定题目的提交次数"""
    # 检查开赛状态
    if not db_utils.is_competition_started():
        return f"⏰ 比赛尚未开始\n开赛时间：{db_utils.get_start_time()}"
    
    # 检查参数格式
    if len(params) != 2:
        return "参数格式错误！正确格式：/增加次数 [章节名] [题目序号]"
    
    chapter_name, puzzle_id_str = params[0], params[1]
    
    # 验证题目序号
    try:
        puzzle_id = int(puzzle_id_str)
    except ValueError:
        return "题目序号必须是数字"
    
    # 检查用户是否在队伍中
    user_id = message_info["source_id"]
    team_id = db_utils.get_user_team_id(user_id)
    if not team_id:
        return "您尚未加入任何队伍，请先创建或加入队伍"
    
    chapter_id = db_utils.get_chapter_id(chapter_name)

    # 检查章节是否存在
    if not chapter_id:
        return f"该章节未解锁或不存在"
    
    # 验证是否存在以及是否解锁
    if not db_utils.is_puzzle_unlocked(team_id, chapter_id, puzzle_id):
        return "该章节未解锁或不存在"
    
    # 执行增加次数操作
    success, msg = db_utils.add_submit_count(team_id, chapter_id, puzzle_id)
    return f"{'✅' if success else '❌'} {msg}"


'''
提示相关
'''

def handle_hints(params, message_info):
    """/提示 [章节名] [题目序号] - 查看指定题目的提示列表"""
    # 检查开赛状态
    if not db_utils.is_competition_started():
        return f"⏰ 比赛尚未开始\n开赛时间：{db_utils.get_start_time()}"
    
    # 检查参数格式
    if len(params) != 2:
        return "参数格式错误！正确格式：/提示 [区域名称] [题目序号]"
    
    chapter_name, puzzle_id_str = params[0], params[1]
    
    # 验证题目序号
    try:
        puzzle_id = int(puzzle_id_str)
    except ValueError:
        return "题目序号必须是数字"
    
    # 检查用户是否在队伍中
    user_id = message_info["source_id"]
    team_id = db_utils.get_user_team_id(user_id)
    if not team_id:
        return "您尚未加入任何队伍，请先创建或加入队伍"
    
    chapter_id = db_utils.get_chapter_id(chapter_name)

    # 检查章节是否存在
    if not chapter_id:
        return f"该章节未解锁或不存在"
    
    # 验证是否存在以及是否解锁
    if not db_utils.is_puzzle_unlocked(team_id, chapter_id, puzzle_id):
        return "该章节未解锁或不存在"
    
    unlock_time_str = get_puzzle_unlock_time(team_id, chapter_id, puzzle_id)
    if not unlock_time_str:
        return "该题目未解锁"

    # 计算当前时间与解锁时间的差值
    unlock_time = datetime.datetime.strptime(unlock_time_str, "%Y-%m-%d %H:%M:%S")
    current_time = datetime.datetime.now()
    time_diff_hours = (current_time - unlock_time).total_seconds() / 3600

    # 计算提示解锁时间（题目解锁时间 + 延迟小时数）
    hint_unlock_time = unlock_time + datetime.timedelta(hours=db_utils.HINT_UNLOCK_DELAY)
    # 格式化提示解锁时间为字符串
    hint_unlock_time_str = hint_unlock_time.strftime("%Y-%m-%d %H:%M:%S")

    # 提示解锁延迟判断
    if time_diff_hours < db_utils.HINT_UNLOCK_DELAY:
        return f"该题提示暂未开放！\n开放时间：{hint_unlock_time_str}"
    
    # 获取已解锁的提示ID
    unlocked_hint_ids = db_utils.get_unlocked_hints(team_id, chapter_id, puzzle_id)
    
    # 查找对应的题目提示
    for chapter in puzzleInfo["chapters"]:
        if chapter["id"] == chapter_id:
            for puzzle in chapter["puzzle"]:
                if puzzle["id"] == puzzle_id:
                    # 提取并排序提示（按id排序）
                    hints = sorted(puzzle.get("hints", []), key=lambda x: x["id"])
                    if not hints:
                        return "该题目暂无提示"
                    # 格式化输出，显示已解锁提示的内容
                    result = "提示列表：\n"
                    for hint in hints:
                        status = "（已解锁）" if hint["id"] in unlocked_hint_ids else f"（{hint['cost']}星韵）"
                        result += f"{hint['id']}.{hint['title']}{status}"
                        # 如果已解锁，显示提示内容
                        if hint["id"] in unlocked_hint_ids:
                            result += f"\n{hint['content']}\n"
                        else:
                            result += "\n"
                    return result
    
    # 未找到题目
    return f"未找到区域[{chapter_name}]中的第{puzzle_id}题"


def handle_unlock_hint(params, message_info):
    """/解锁提示 [章节名] [题目序号] [提示序号] - 解锁指定题目的特定提示"""
    # 检查开赛状态
    if not db_utils.is_competition_started():
        return f"⏰ 比赛尚未开始\n开赛时间：{db_utils.get_start_time()}"
    
    # 检查参数格式
    if len(params) != 3:
        return "参数格式错误！正确格式：/解锁提示 [区域名称] [题目序号] [提示序号]"
    
    chapter_name, puzzle_id_str, hint_id_str = params[0], params[1], params[2]
    
    # 验证题目序号和提示序号
    try:
        puzzle_id = int(puzzle_id_str)
        hint_id = int(hint_id_str)
    except ValueError:
        return "题目序号和提示序号必须是数字"
    
    # 检查用户是否在队伍中
    user_id = message_info["source_id"]
    team_id = db_utils.get_user_team_id(user_id)
    if not team_id:
        return "您尚未加入任何队伍，请先创建或加入队伍"
    
    chapter_id = db_utils.get_chapter_id(chapter_name)

    # 检查章节是否存在
    if not chapter_id:
        return f"该章节未解锁或不存在"
    
    # 验证是否存在以及是否解锁
    if not db_utils.is_puzzle_unlocked(team_id, chapter_id, puzzle_id):
        return "该题目未解锁或不存在"
    
    unlock_time_str = get_puzzle_unlock_time(team_id, chapter_id, puzzle_id)
    if not unlock_time_str:
        return "该题目未解锁"

    # 计算当前时间与解锁时间的差值
    unlock_time = datetime.datetime.strptime(unlock_time_str, "%Y-%m-%d %H:%M:%S")
    current_time = datetime.datetime.now()
    time_diff_hours = (current_time - unlock_time).total_seconds() / 3600

    # 计算提示解锁时间（题目解锁时间 + 延迟小时数）
    hint_unlock_time = unlock_time + datetime.timedelta(hours=db_utils.HINT_UNLOCK_DELAY)
    # 格式化提示解锁时间为字符串
    hint_unlock_time_str = hint_unlock_time.strftime("%Y-%m-%d %H:%M:%S")

    # 提示解锁延迟判断
    if time_diff_hours < db_utils.HINT_UNLOCK_DELAY:
        return f"该题提示暂未开放！\n开放时间：{hint_unlock_time_str}"
    
    # 解锁提示
    success, msg = db_utils.unlock_hint(team_id, chapter_id, puzzle_id, hint_id)
    return f"{'✅' if success else '❌'} {msg}"


# ------------------------------
# 消息、管理员与排行榜
# ------------------------------
def handle_send_team_msg(params, message_info):
    """/发消息 [内容] - 发送消息到本队消息面板"""
    # 检查开赛状态
    if not db_utils.is_competition_started():
        return f"⏰ 比赛尚未开始\n开赛时间：{db_utils.get_start_time()}"
    
    # 检查当前时间是否禁用了消息状态
    if db_utils.is_send_msg_disabled():
        return f"⏰ 发消息功能已禁用！"
    
    if not params:
        return "格式错误：/发消息 [消息内容]"
    user_id = message_info["source_id"]
    team_id = db_utils.get_user_team_id(user_id)
    if not team_id:
        return "未加入队伍，无法发送消息"
    user_name = db_utils.get_user_nickname(user_id, team_id)
    content = " ".join(params)
    success, msg = db_utils.send_team_message(team_id, user_id, user_name, content)
    return f"{'✅' if success else '❌'} {msg}"


def handle_view_team_board(params, message_info):
    """/消息 - 查看本队消息面板"""
    # 检查开赛状态
    if not db_utils.is_competition_started():
        return f"⏰ 比赛尚未开始\n开赛时间：{db_utils.get_start_time()}"
    
    user_id = message_info["source_id"]
    team_id = db_utils.get_user_team_id(user_id)
    if not team_id:
        return "未加入队伍，无消息面板"
    messages = db_utils.get_team_message_board(team_id)
    if not messages:
        return "本队暂无消息"
    result = "📢 本队消息面板：\n"
    for msg in messages:
        result += f"[{msg['time']}] {msg['sender']}：{msg['content']}\n"
    return result


def handle_all_teams(params, message_info):
    """/队伍 [可选页码]"""
    admin_id = message_info["source_id"]
    if not db_utils.is_admin(admin_id):
        return "权限不足，仅管理员可查看"
    page = int(params[0]) if params else 1
    teams_data = db_utils.get_all_teams(page)
    if not teams_data["teams"]:
        return "暂无队伍"
    result = f"📋 所有队伍（第{page}/{teams_data['total_pages']}页）：\n"
    for team in teams_data["teams"]:
        # 未回复消息数>0标红
        unreplied_tag = "🔴" if team["unreplied_count"] > 0 else "⚪"
        result += (
            f"{unreplied_tag} ID：{team['team_id']} | {team['team_name']}\n"
            f"  章节：{team['current_chapter']} | 过题：{team['passed_puzzles']}\n"
            f"  {db_utils.POINT_NAME}：{team['points']} | 消息：{team['unreplied_count']}\n"
        )
    result += f"\n查看其他页：/队伍 [页码]"
    return result


def handle_admin_view_team(params, message_info):
    """/查看 [队伍ID]"""
    if len(params) != 1:
        return "格式错误：/查看 [队伍ID]"
    admin_id = message_info["source_id"]
    if not db_utils.is_admin(admin_id):
        return "权限不足"
    team_id = params[0]
    board_data, err = db_utils.admin_get_team_board(team_id)
    if err:
        return err
    team_info = board_data["team_info"]
    messages = board_data["messages"]

    # 增加一步获取所有队员
    members = db_utils.get_team_members(team_id)
    member_count = len(members)
    limit = db_utils.TEAM_MEMBER_LIMIT
    members_str = "\n".join([
            f"{'👑 ' if m['is_leader'] else '   '}{m['user_name']}"
            for m in members
        ])
    
    result = (
        f"📊 队伍信息：\n"
        f"ID：{team_info['team_id']} | {team_info['team_name']}\n"
        f"章节：{team_info['current_chapter_id']} | 过题：{team_info['passed_puzzle_count']}\n"
        f"{db_utils.POINT_NAME}：{team_info['points']}\n"
        f"队员列表（{member_count}/{limit}人）：\n{members_str}\n\n"
        f"💬 消息记录：\n"
    )
    for msg in messages:
        replied_tag = "🔴" if (not msg['is_replied'] and not msg['is_admin']) else "⚪"
        result += f"[{msg['time']}] {replied_tag} {msg['sender']}：{msg['content']}\n"
        if msg['reply']:
            result += f"  {msg['reply']}\n"
    return result


def handle_admin_reply_team(params, message_info):
    """/回复 [队伍ID] [内容] - 回复指定队伍的消息（自动标记所有未回复消息为已回复）"""
    if len(params) < 2:
        return "格式错误：/回复 [队伍ID] [回复内容]"
    admin_id = message_info["source_id"]
    if not db_utils.is_admin(admin_id):
        return "权限不足"
    try:
        team_id = params[0]
        content = " ".join(params[1:])  # 取队伍ID后的所有内容作为回复内容
    except ValueError:
        return "参数格式错误"
    
    success, msg = db_utils.admin_reply_team(
        team_id, admin_id, "", content
    )
    return f"{'✅' if success else '❌'} {msg}"


def handle_update_points(params, message_info):
    """/修改点数 [队伍ID] [增减量] - 调整队伍点数（如50/-30）"""
    if len(params) != 2:
        return "格式错误：/修改点数 [队伍ID] [增减量，如50/-30]"
    admin_id = message_info["source_id"]
    if not db_utils.is_admin(admin_id):
        return "权限不足"
    try:
        team_id = params[0]
        amount = int(params[1])
    except ValueError:
        return "增减量必须是整数（如+50/-30）"
    success, msg = db_utils.update_team_points(team_id, amount, admin_id)
    return f"{'✅' if success else '❌'} {msg}"

def handle_update_all_teams_points(params, message_info):
    """/修改所有队伍点数 [增减量]"""
    if len(params) != 1:
        return "格式错误：/修改所有队伍点数 [增减量] [增减量，如50/-30]"
    admin_id = message_info["source_id"]
    if not db_utils.is_admin(admin_id):
        return "权限不足"
    try:
        amount = int(params[0])
    except ValueError:
        return "增减量必须是整数（如+50/-30）"
    success, msg = db_utils.add_points_to_all_teams(amount)
    return f"{'✅' if success else '❌'} {msg}"


"""/排行榜 [可选页码] - 显示队伍排行榜"""
def handle_ranking(params, message_info):
    """/排行榜 [可选页码] - 显示队伍排行榜"""
    # 解析页码参数（默认第一页）
    page = 1
    if params:
        try:
            page = int(params[0])
            if page < 1:
                return "页码必须大于等于1"
        except ValueError:
            return "页码必须是数字"
    
    # 获取排行榜数据
    ranking_data = db_utils.get_teams_ranking(page, per_page=20)
    
    if not ranking_data["teams"]:
        return "暂无队伍数据"
    
    # 计算当前页队伍的起始名次
    start_rank = (page - 1) * 20 + 1
    
    # 格式化输出
    result = f"🏆 队伍排行榜（第{page}/{ranking_data['total_pages']}页）：\n"
    for i, team in enumerate(ranking_data["teams"]):
        rank = start_rank + i
        completion_status = "已完赛" if team["is_completed"] else "未完赛"
        time_display = f" | {team['completed_time']}" if team["is_completed"] else ""
        result += (
            f"{rank}. {team['team_name']}(ID:{team['team_id']})\n"
            f"   {completion_status}{time_display} | {team['current_chapter_id']}章 {team['passed_puzzle_count']}题\n"
        )
    
    # 分页导航
    nav = []
    if ranking_data["current_page"] > 1:
        nav.append(f"上一页：/排行榜 {ranking_data['current_page'] - 1}")
    if ranking_data["current_page"] < ranking_data["total_pages"]:
        nav.append(f"下一页：/排行榜 {ranking_data['current_page'] + 1}")
    
    if nav:
        result += "\n分页导航：\n" + "\n".join(nav)
    
    return result


# 在 command_handler.py 中添加（建议放在管理员指令区域）
def handle_all_records(params, message_info):
    """/所有记录 [可选页码] - 管理员查看所有队伍的提交记录"""
    admin_id = message_info["source_id"]
    if not db_utils.is_admin(admin_id):
        return "权限不足，仅管理员可查看"
    
    # 解析页码参数
    page = 1
    if params:
        try:
            page = int(params[0])
            if page < 1:
                return "页码必须大于等于1"
        except ValueError:
            return "页码必须是数字"
    
    # 获取所有队伍提交记录
    history_data = db_utils.get_all_teams_submission_history(page=page, per_page=10)
    
    if not history_data["records"]:
        return "暂无提交记录"
    
    # 格式化输出
    result = f"📋 所有队伍提交记录（第{history_data['current_page']}/{history_data['total_pages']}页）：\n"
    for record in history_data["records"]:
        result += (
            f"[{record['team_name']}({record['team_id']})] {record['chapter_name']}{record['puzzle_id']}-{record['puzzle_name']}\n"
            f"昵称：{record['user_name']} | 结果：{'✅正确' if record['result'] == 'correct' else '🚩里程碑' if record['result'] == 'milestone' else '❌错误'}\n"
            f"答案：{record['submitted_answer']}\n时间：{record['submit_time']}\n\n"
        )
    
    # 分页导航
    nav = []
    if history_data["current_page"] > 1:
        nav.append(f"上一页：/所有记录 {history_data['current_page'] - 1}")
    if history_data["current_page"] < history_data["total_pages"]:
        nav.append(f"下一页：/所有记录 {history_data['current_page'] + 1}")
    
    if nav:
        result += "分页导航：\n" + "\n".join(nav)
    
    return result


def handle_team_records(params, message_info):
    """/队伍记录 [队伍ID] [可选页码] - 管理员查看特定队伍的提交记录"""
    admin_id = message_info["source_id"]
    if not db_utils.is_admin(admin_id):
        return "权限不足，仅管理员可查看"
    
    # 解析参数
    if len(params) < 1:
        return "格式错误：/队伍记录 [队伍ID] [可选页码]"
    
    team_id = params[0]
    page = 1
    if len(params) >= 2:
        try:
            page = int(params[1])
            if page < 1:
                return "页码必须大于等于1"
        except ValueError:
            return "页码必须是数字"
    
    # 验证队伍是否存在
    team = db_utils.get_team_by_id(team_id)
    if not team:
        return f"队伍ID {team_id} 不存在"
    
    # 获取指定队伍的提交记录（复用现有函数）
    history_data = db_utils.get_team_submission_history(
        team_id=team_id,
        page=page,
        per_page=10
    )
    
    if not history_data["records"]:
        return f"队伍 {team['team_name']}({team_id}) 暂无提交记录"
    
    # 格式化输出
    result = f"📋 队伍 {team['team_name']}({team_id}) 提交记录（第{history_data['current_page']}/{history_data['total_pages']}页）：\n"
    for record in history_data["records"]:
        result += (
            f"{record['chapter_name']}{record['puzzle_id']}-{record['puzzle_name']}\n"
            f"昵称：{record['user_name']} | 结果：{'✅正确' if record['result'] == 'correct' else '🚩里程碑' if record['result'] == 'milestone' else '❌错误'}\n"
            f"答案：{record['submitted_answer']}\n时间：{record['submit_time']}\n\n"
        )
    
    # 分页导航
    nav = []
    if history_data["current_page"] > 1:
        nav.append(f"上一页：/队伍记录 {team_id} {history_data['current_page'] - 1}")
    if history_data["current_page"] < history_data["total_pages"]:
        nav.append(f"下一页：/队伍记录 {team_id} {history_data['current_page'] + 1}")
    
    if nav:
        result += "分页导航：\n" + "\n".join(nav)
    
    return result


def handle_puzzle_records(params, message_info):
    """/查询题目记录 [章节名] [题目序号] [可选页码] - 管理员显示指定章节和题目的提交记录"""
    admin_id = message_info["source_id"]
    if not db_utils.is_admin(admin_id):
        return "权限不足，仅管理员可查看"


    chapter_name = params[0]
    puzzle_id_str = params[1]
    # 处理可选页码
    page = 1
    if len(params) >= 3:
        try:
            page = int(params[2])
            if page < 1:
                return "页码必须大于0"
        except ValueError:
            return "页码必须为整数"

    # 验证题目序号是否为数字
    try:
        puzzle_id = int(puzzle_id_str)
        if puzzle_id < 1:
            return "题目序号必须大于0"
    except ValueError:
        return "题目序号必须为整数"
    


    # 从数据库查询提交记录
    page_size = 10
    records = db_utils.get_puzzle_submit_records(
        chapter_id=db_utils.get_chapter_id(chapter_name),
        puzzle_id=puzzle_id,
        page=page,
        page_size=page_size
    )

    # 格式化返回结果
    if not records:
        return f"未查询到【{chapter_name}】第{puzzle_id}题的提交记录"

#columns = ["team_name", "user_name", "submitted_answer", "result", "submit_time"]

    result = [f"【{chapter_name}】第{puzzle_id}题 提交记录（第{page}页，每页{page_size}条）："]
    for idx, record in enumerate(records, start=1):
        # 假设record包含提交人ID、提交时间、提交内容/状态等字段，可根据实际调整
        team_id = record.get("team_id", "未知")
        submitter_team = record.get("team_name", "未知")
        submitter_id = record.get("user_name", "未知")
        submit_time = record.get("submit_time", "未知时间")
        submit_answer = record.get("submitted_answer", "未知")
        submit_status = record.get("result", "未知状态")
        result.append(f"({team_id}){submitter_team} | {submitter_id}\n 答案：{submit_answer} | 结果：{submit_status}\n时间：{submit_time}\n")

    # 拼接结果返回
    return "\n".join(result)


def handle_view_other_team(params, message_info):
    """/查看其他队伍 - 查看一个队的队伍信息"""
    # 检查参数格式（至少需要章节名和题目序号）
    if len(params) < 1:
        return "参数格式错误！正确格式：/查看其他队伍 [队伍ID]"
    
    team_id = params[0]

    team_info = db_utils.get_team_by_id(team_id)
    if not team_info:
        return "❌ 队伍不存在"

    # 获取所有队员
    members = db_utils.get_team_members(team_id)
    member_count = len(members)
    limit = db_utils.TEAM_MEMBER_LIMIT
    members_str = "\n".join([
            f"{'👑 ' if m['is_leader'] else '   '}{m['user_name']}"
            for m in members
        ])
    
    result = (
        f"📊 队伍信息：\n"
        f"ID：{team_info['team_id']} | {team_info['team_name']}\n"
        f"队员列表（{member_count}/{limit}人）：\n{members_str}"
    )

    return result


def handle_view_ending(params, message_info):
    """{ENDING_VIEW_COMMAND} - 查看完赛结局（仅完赛队伍可使用）"""
    if len(params) != 0:
        return f"指令格式错误！\n正确用法：{db_utils.VIEW_ENDING_COMMAND}（无需参数）"
    
    user_id = message_info["source_id"]
    team = db_utils.get_user_team(user_id)
    
    if not team:
        return "❌ 你还没有加入任何队伍，无法查看结局！"
    
    if not team["is_completed"]:
        return "❌ 你的队伍尚未完赛，无法查看结局！"
    
    # 获取结局信息
    ending_info = db_utils.get_ending_info()  # 假设已修正该函数仅返回信息（无错误值）
    if not ending_info:
        return "❌ 结局信息加载失败"
    
    # 因为文章还没写，暂时返回文本
    # 返回Article对象（与handle_get_chapter保持一致）
    from werobot.replies import Article
    return Article(
        title=ending_info["name"],
        description=ending_info["description"],
        img=ending_info["news_img"],
        url=ending_info["news_url"]
    )

    # return "这里是最终结局剧情！"