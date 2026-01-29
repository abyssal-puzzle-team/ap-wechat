import sqlite3
import datetime
import random
import json
import threading
import time

START_TIME = datetime.datetime(2026, 1, 23, 20, 0, 0)                 # 比赛开始时间
END_TIME = datetime.datetime(2026, 1, 30, 20, 0, 0)                   # 比赛结束时间
DISABLE_SEND_MESSAGE_TIME = datetime.datetime(2026, 1, 30, 17, 0, 0)  # 禁用发消息功能的时间

# 帮助菜单链接
HELP_MENU_URL = "https://mmbiz.qpic.cn/mmbiz_png/x0lwngPKUjh73rBLVibicFtIffZibmysBJU0FTyibKM3bLqYqw4mGh1iaxQ6XEBsYDLGcicxUAjV7TKPUMd4uSBBict0g/640?wx_fmt=png&amp;from=appmsg"
# 结局文章的查看指令
VIEW_ENDING_COMMAND = "/夺取永恒核心" 
# 完赛的提示，是最后一章通过后显示的内容，可以在这里写完赛群之类内容
ENDING_INFO = f"🎉恭喜完赛！\n完赛群：951308436\n请回复 {VIEW_ENDING_COMMAND} 查看最终结局。"


TEAM_MEMBER_LIMIT = 5           # 队伍人数限制
SUBMIT_COUNT_LIMIT = 20         # 每题的提交次数限制
HINT_UNLOCK_DELAY = 1           # 提示解锁时间延迟（小时）
POINT_NAME = "星韵"              # 点数的称呼
ADD_POINT_PER_MINUTE = 30       # 每分钟增加的点数

CAN_ADD_PASSED_PUZZLE_SUBMIT_COUNT = False    #是否允许已通过题目增加次数
ADD_SUBMIT_COUNT_COST = 10000   # 增加提交次数要花费的点数
ADD_SUBMIT_COUNT = 20           # 增加的提交次数

MESSAGE_CHAR_LIMIT = 80        # 一条消息的字符数上限
MESSAGE_SHOW_LIMIT = 6          # 显示的消息条数上限，建议这两个乘积不大于500，否则可能会导致回复不出来

ADMIN_NAME = "【回响】"    # 管理员回复的站内信时显示的称呼
# 管理员ID列表
ADMIN_USER_IDS = [
                    "op1PY2xxxxxxxxxxxxxxxxxx"
                    ]


# 数据库文件路径（和db_init.py生成的文件对应）
DB_PATH = "abyssal_puzzle.db"

def load_puzzle_info():
    """加载谜题信息JSON文件"""
    with open("data/puzzle_info.json", "r", encoding="utf-8") as f:
        return json.load(f)

def random_str(n):
    """随机生成一个长度为n的数字字母字符串"""
    res = ""
    for i in range(n):
        a = random.randint(65, 90)
        b = random.randint(48, 57)
        res += chr(random.choice([a, a, a, b]))
    return res

def is_chapter_exist(chapter_name):
    """检查章节是否存在"""
    puzzle_info = load_puzzle_info()
    return chapter_name in puzzle_info["chapters"]

def is_puzzle_exist(chapter_name, puzzle_id):
    """检查题目是否存在"""
    puzzle_info = load_puzzle_info()
    if chapter_name not in puzzle_info["chapters"]:
        return False,"章节不存在"
    is_exist = puzzle_id in puzzle_info["chapters"][chapter_name]
    if is_exist:
        return True,""
    else:
        return False,"题目不存在"

def get_chapter_id(chapter_name):
    """根据章节名获取章节ID"""
    puzzle_info = load_puzzle_info()
    for chapter in puzzle_info["chapters"]:
        if chapter["name"] == chapter_name:
            return chapter["id"]
    return None

def get_chapter_name(chapter_id):
    """根据章节ID获取章节名"""
    puzzle_info = load_puzzle_info()
    for chapter in puzzle_info["chapters"]:
        if chapter["id"] == chapter_id:
            return chapter["name"]
    return None

def get_chapter_name_to_id():
    """获取chapter_name_to_id字典映射"""
    dic = {}

    puzzle_info = load_puzzle_info()
    for chapter in puzzle_info["chapters"]:
        dic[chapter["name"]] = chapter["id"]

    return dic

def get_puzzle_name(chapter_id, puzzle_id):
    """根据章节ID和题目ID获取题目名"""
    puzzle_info = load_puzzle_info()
    for chapter in puzzle_info["chapters"]:
        if chapter["id"] == chapter_id:
            for puzzle in chapter["puzzle"]:
                if puzzle["id"] == int(puzzle_id):
                    return puzzle["name"]
    return None


def get_ending_info():
    """读取结局信息"""
    try:
        with open('data/ending.json', 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"读取结局失败：{str(e)}")  # 仅内部打印错误
        return None


def get_db_connection():
    """获取数据库连接"""
    conn = sqlite3.connect(DB_PATH)
    # 开启外键约束（确保队员表的team_id必须在队伍表中存在）
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


# ------------------------------
# 校验函数与时间
# ------------------------------
def is_user_in_team(user_id):
    """校验用户是否已在某个队伍中：返回True/False"""
    conn = get_db_connection()
    cursor = conn.cursor()
    # 查询用户是否存在于队员表中
    cursor.execute(
        "SELECT 1 FROM team_members WHERE user_id = ? LIMIT 1",
        (user_id,)
    )
    result = cursor.fetchone()
    conn.close()
    return result is not None  # 有结果则返回True（已在队伍中）


def is_team_name_valid(team_name):
    """校验队伍名合法性：返回（是否合法，错误提示）"""
    if not team_name.strip():  # 队伍名为空或全是空格
        return False, "队伍名不能为空"
    if len(team_name) > 30:  # 限制队伍名长度（避免过长）
        return False, "队伍名长度不能超过30个字符"
    # 可选：禁止含特殊字符（如@#$%^&*等，按需调整）
    # import re
    # if not re.match(r'^[\u4e00-\u9fa5a-zA-Z0-9_]+$', team_name):
    #    return False, "队伍名只能包含中文、字母、数字和下划线"
    return True, ""


def is_user_name_valid(user_name):
    """校验昵称合法性：返回（是否合法，错误提示）"""
    if not user_name.strip():  # 昵称为空或全是空格
        return False, "昵称不能为空"
    if len(user_name) > 30:  # 限制长度（避免过长）
        return False, "昵称长度不能超过30个字符"
    # 可选：禁止含特殊字符（如@#$%^&*等，按需调整）
    # import re
    # if not re.match(r'^[\u4e00-\u9fa5a-zA-Z0-9_]+$', team_name):
    #    return False, "队伍名只能包含中文、字母、数字和下划线"
    return True, ""


def is_admin(user_id):
    """验证用户是否为管理员（可硬编码管理员ID或从数据库读取）"""
    return user_id in ADMIN_USER_IDS

def is_competition_started():
    """检查比赛是否已开始（与开赛时间比较）"""
    current_time = datetime.datetime.now()
    return current_time >= START_TIME

def is_competition_end():
    """检查比赛是否已结束（与结束时间比较）"""
    current_time = datetime.datetime.now()
    return current_time >= END_TIME

def is_send_msg_disabled():
    """检查发消息功能是否已禁用"""
    current_time = datetime.datetime.now()
    return current_time >= DISABLE_SEND_MESSAGE_TIME


def get_start_time():
    """获取固定的开赛时间（格式化输出）"""
    return START_TIME.strftime("%Y-%m-%d %H:%M:%S")

def get_end_time():
    """获取固定的开赛时间（格式化输出）"""
    return END_TIME.strftime("%Y-%m-%d %H:%M:%S")


# ------------------------------
# 增删改查函数
# ------------------------------
def get_user_nickname(user_id, team_id):
    """获取用户在指定队伍中的昵称"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT user_name FROM team_members 
        WHERE user_id = ? AND team_id = ?
    ''', (user_id, team_id))
    result = cursor.fetchone()
    conn.close()
    return result[0] if result else None

def change_user_nickname(user_id, new_nickname):
    """修改用户在队伍中的昵称"""
    # 校验用户是否在队伍中
    team_id = get_user_team_id(user_id)
    if not team_id:
        return False, "你不在任何队伍中，无法修改昵称"
    
    # 校验昵称合法性
    is_valid, info = is_user_name_valid(new_nickname)
    if not is_valid:
        return False, f"修改失败：{info}"
    
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute('''
            UPDATE team_members 
            SET user_name = ? 
            WHERE user_id = ? AND team_id = ?
        ''', (new_nickname, user_id, team_id))
        conn.commit()
        return True, f"昵称已更新为：{new_nickname}"
    except sqlite3.Error as e:
        return False, f"修改失败：{str(e)}"
    finally:
        conn.close()

def get_user_team_id(user_id):
    """获取用户所在队伍的ID（仅返回存在的队伍ID）"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT team_id FROM team_members WHERE user_id = ? LIMIT 1",
        (user_id,)
    )
    result = cursor.fetchone()
    conn.close()
    return result[0] if result else None

def get_user_team(user_id):
    """查询用户所在的队伍（包含点数和完赛信息）"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT t.team_id, t.team_name, t.create_time, t.current_chapter_id, t.valid_chapter_id,
               t.passed_puzzle_count, t.valid_passed_puzzle_count, t.points, t.is_completed, t.completed_time
        FROM teams t 
        JOIN team_members m ON t.team_id = m.team_id 
        WHERE m.user_id = ?
    ''', (user_id,))
    team = cursor.fetchone()
    conn.close()
    
    if team:
        return {
            "team_id": team[0],
            "team_name": team[1],
            "create_time": team[2],
            "current_chapter_id": team[3],
            "valid_chapter_id": team[4],
            "passed_puzzle_count": team[5],
            "valid_passed_puzzle_count": team[6],
            "points": team[7],
            "is_completed": team[8] == 1,
            "completed_time": team[9]
        }
    return None

"""检查队伍是否已解锁指定题目"""
def is_puzzle_unlocked(team_id, chapter_id, puzzle_id):
    """检查队伍是否已解锁指定题目（基于team_puzzle_status的unlock_time）"""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute('''
            SELECT unlock_time FROM team_puzzle_status 
            WHERE team_id = ? AND chapter_id = ? AND puzzle_id = ?
        ''', (team_id, chapter_id, puzzle_id))
        result = cursor.fetchone()
        # 存在记录且unlock_time不为空即为已解锁
        return result is not None and result[0] is not None
    finally:
        conn.close()

def get_team_by_id(team_id):
    """根据队伍ID查询队伍信息：返回队伍字典或None"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM teams WHERE team_id = ?", (team_id,))
    team = cursor.fetchone()
    conn.close()
    
    if team:
        return {
            "team_id": team[0],
            "team_name": team[1],
            "create_time": team[2],
            "invitation_code": team[3],
            "current_chapter_id": team[4],
            "valid_chapter_id": team[5],
            "passed_puzzle_count": team[6],
            "valid_passed_puzzle_count": team[7],
            "points": team[8]
        }
    return None

def is_user_team_leader(user_id):
    """检查用户是否是其所在队伍的队长"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT 1 FROM team_members WHERE user_id = ? AND is_leader = 1 LIMIT 1",
        (user_id,)
    )
    result = cursor.fetchone()
    conn.close()
    return result is not None

def get_team_member_count(team_id):
    """查询队伍当前的成员数量"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT COUNT(*) FROM team_members WHERE team_id = ?",
        (team_id,)
    )
    count = cursor.fetchone()[0]
    conn.close()
    return count

def get_team_members(team_id):
    """获取队伍所有成员列表（含队长标识）"""
    try:
        team_id = int(team_id)
    except ValueError:
        return []

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT user_name, join_time, is_leader FROM team_members WHERE team_id = ?",
        (team_id,)
    )
    members = cursor.fetchall()
    conn.close()
    return [
        {
            "user_name": m[0],
            "join_time": m[1],
            "is_leader": m[2] == 1
        } for m in members
    ]

def get_unlocked_hints(team_id, chapter_id, puzzle_id):
    """获取队伍已解锁的提示ID列表"""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute('''
            SELECT hint_id FROM team_unlocked_hints 
            WHERE team_id = ? AND chapter_id = ? AND puzzle_id = ?
        ''', (team_id, chapter_id, puzzle_id))
        results = cursor.fetchall()
        return [result[0] for result in results]
    finally:
        conn.close()

def get_remaining_attempts(team_id, chapter_id, puzzle_id):
    """获取指定题目的剩余提交次数"""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute('''
            SELECT remaining_attempts 
            FROM team_puzzle_status 
            WHERE team_id = ? AND chapter_id = ? AND puzzle_id = ?
        ''', (team_id, chapter_id, puzzle_id))
        result = cursor.fetchone()
        return result[0] if result else None
    finally:
        conn.close()

# ------------------------------
# 队伍相关操作
# ------------------------------
def create_team(team_name, creator_id, creator_name):
    """创建队伍：需传入队伍名、创建者ID、创建者昵称"""
    conn = get_db_connection()
    cursor = conn.cursor()
    create_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    invitation_code = random_str(5)

    # 校验创建者状态
    if is_user_in_team(creator_id):
        return False, "创建失败！您已经在队伍中了！", None, None

    # 校验队伍名
    is_valid, info = is_team_name_valid(team_name)
    if not is_valid:
        return False, f"创建失败！{info}！", None, None

    # 校验昵称
    is_valid, info = is_user_name_valid(creator_name)
    if not is_valid:
        return False, f"创建失败！{info}！", None, None

    try:
        # 插入队伍
        cursor.execute(
            "INSERT INTO teams (team_name, create_time, invitation_code) VALUES (?, ?, ?)",
            (team_name, create_time, invitation_code)
        )
        conn.commit()
        team_id = cursor.lastrowid

        # 创建者加入队伍（设为队长）
        cursor.execute(
            "INSERT INTO team_members (team_id, user_id, user_name, join_time, is_leader) VALUES (?, ?, ?, ?, ?)",
            (team_id, creator_id, creator_name, create_time, 1)
        )

        #如果此时已经开赛，自动初始化第1章，且将队伍章数设置为1
        if is_competition_started():
            cursor.execute('''
            UPDATE teams
            SET current_chapter_id = 1, valid_chapter_id = 1
            WHERE team_id = ?
            ''', (team_id,))
            init_chapter_puzzle_status(cursor, team_id, 1, create_time)

        conn.commit()
        return True, "🎉队伍创建成功！", team_id, invitation_code

    
    except sqlite3.IntegrityError as e:
        if "UNIQUE constraint failed: teams.team_name" in str(e):
            return False, "队伍名已被占用，请换一个吧！", None, None
        return False, f"创建失败：{str(e)}", None, None
    finally:
        conn.close()

def change_team_name(user_id, new_team_name):
    """修改队伍名称（仅队长可操作）"""
    # 1. 检查用户是否在队伍中
    team_id = get_user_team_id(user_id)
    if not team_id:
        return False, "你不在任何队伍中，无法修改队名"
    
    # 2. 检查用户是否为队长
    if not is_user_team_leader(user_id):
        return False, "只有队长才能修改队名"
    
    # 3. 校验新队名合法性
    is_valid, info = is_team_name_valid(new_team_name)
    if not is_valid:
        return False, f"修改失败：{info}"
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # 4. 检查队名是否已被占用
        cursor.execute("SELECT 1 FROM teams WHERE team_name = ?", (new_team_name,))
        if cursor.fetchone():
            return False, "该队名已被占用，请更换其他名称"
        
        # 5. 更新队名
        cursor.execute(
            "UPDATE teams SET team_name = ? WHERE team_id = ?",
            (new_team_name, team_id)
        )
        # 同时更新队题状态表中的队名
        cursor.execute(
            "UPDATE team_puzzle_status SET team_name = ? WHERE team_id = ?",
            (new_team_name, team_id)
        )
        # 同时更新提交记录表中的队名
        cursor.execute(
            "UPDATE team_puzzle_submissions SET team_name = ? WHERE team_id = ?",
            (new_team_name, team_id)
        )
        conn.commit()
        return True, f"队名已成功修改为：{new_team_name}"
    
    except sqlite3.Error as e:
        return False, f"修改失败：{str(e)}"
    finally:
        conn.close()

"""解散队伍：只有队长可以解散自己所在的队伍"""
def dismiss_team(user_id):
    """解散队伍：只有队长可以解散自己所在的队伍"""
    # 检查用户是否在队伍中
    team_id = get_user_team_id(user_id)
    if not team_id:
        return False, "你不在任何队伍中，无法解散队伍"
    
    # 检查用户是否为该队伍的队长
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT is_leader FROM team_members WHERE user_id = ? AND team_id = ? LIMIT 1",
        (user_id, team_id)
    )
    is_leader = cursor.fetchone()
    conn.close()
    if not is_leader or is_leader[0] != 1:
        return False, "只有队长才能解散队伍"
    
    # 执行解散操作（按顺序删除所有关联数据）
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        # 1. 删除队伍答题提交记录
        cursor.execute("DELETE FROM team_puzzle_submissions WHERE team_id = ?", (team_id,))
        # 2. 删除队伍答题状态
        cursor.execute("DELETE FROM team_puzzle_status WHERE team_id = ?", (team_id,))
        # 3. 删除队伍解锁提示记录
        cursor.execute("DELETE FROM team_unlocked_hints WHERE team_id = ?", (team_id,))
        # 4. 删除队伍消息（包括管理员回复）
        cursor.execute("DELETE FROM team_messages WHERE team_id = ?", (team_id,))
        # 5. 删除队员记录
        cursor.execute("DELETE FROM team_members WHERE team_id = ?", (team_id,))
        # 6. 最后删除队伍本身
        cursor.execute("DELETE FROM teams WHERE team_id = ?", (team_id,))
        
        conn.commit()
        return True, "队伍已成功解散"
    except sqlite3.Error as e:
        return False, f"解散失败：{str(e)}"
    finally:
        conn.close()


# ------------------------------
# 队员相关操作
# ------------------------------
def join_team(team_id, user_id, user_name, invitation_code):
    """加入队伍：需验证队伍ID、邀请码、用户昵称"""
    # 校验队伍ID格式
    try:
        team_id = int(team_id)
    except ValueError:
        return False, "队伍ID必须是整数"

    # 校验用户是否已在队伍
    if is_user_in_team(user_id):
        return False, "您已经在某个队伍中了，无法加入其他队伍"

    # 校验昵称
    is_valid, info = is_user_name_valid(user_name)
    if not is_valid:
        return False, f"加入失败！{info}！"

    # 校验队伍存在性和邀请码
    team = get_team_by_id(team_id)
    if not team:
        return False, "队伍不存在"
    if team["invitation_code"] != invitation_code:
        return False, "邀请码错误"
    
    # 检查队伍人数是否达到上限
    current_count = get_team_member_count(team_id)
    if current_count >= TEAM_MEMBER_LIMIT:
        return False, f"该队伍人数已达{TEAM_MEMBER_LIMIT}人上限，无法加入！"

    conn = get_db_connection()
    cursor = conn.cursor()
    join_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    try:
        cursor.execute(
            "INSERT INTO team_members (team_id, user_id, user_name, join_time) VALUES (?, ?, ?, ?)",
            (team_id, user_id, user_name, join_time)
        )
        conn.commit()
        return True, f"成功加入队伍【{team['team_name']}】"
    except sqlite3.IntegrityError:
        return False, "你已经在这个队伍里啦"
    finally:
        conn.close()

def quit_team(user_id):
    """队员退出队伍（队长不能退出，需先解散）"""
    # 1. 检查用户是否在队伍中
    team_id = get_user_team_id(user_id)
    if not team_id:
        return False, "你不在任何队伍中，无法退出"
    
    # 2. 检查用户是否为队长（队长不能退出）
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT is_leader FROM team_members WHERE user_id = ? AND team_id = ? LIMIT 1",
        (user_id, team_id)
    )
    is_leader = cursor.fetchone()
    conn.close()
    if is_leader and is_leader[0] == 1:
        return False, "你是队长，不能退出队伍，请先解散队伍"
    
    # 3. 执行退出操作
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("DELETE FROM team_members WHERE user_id = ?", (user_id,))
        conn.commit()
        return True, "已成功退出队伍"
    except sqlite3.Error as e:
        return False, f"退出失败：{str(e)}"
    finally:
        conn.close()


# ------------------------------
# 谜题相关操作
# ------------------------------
"""初始化队伍指定章节的题目状态"""
def init_chapter_puzzle_status(cursor, team_id, chapter_id, unlock_time):
    """初始化队伍指定章节的所有题目状态（含unlock_time）"""
    try:
        # 获取队伍名称
        cursor.execute("SELECT team_name FROM teams WHERE team_id = ?", (team_id,))
        team_name = cursor.fetchone()[0]
        
        # 获取章节信息（名称和题目列表）
        puzzle_info = load_puzzle_info()
        target_chapter = None
        for chapter in puzzle_info["chapters"]:
            if chapter["id"] == chapter_id:
                target_chapter = chapter
                break
        if not target_chapter:
            return False, "章节信息不存在"
        
        chapter_name = target_chapter["name"]
        puzzles = target_chapter.get("puzzle", [])
        
        # 初始化每个题目的状态
        for puzzle in puzzles:
            puzzle_id = puzzle["id"]
            puzzle_name = puzzle["name"]
            
            # 检查是否已存在记录（避免重复初始化）
            cursor.execute('''
                SELECT 1 FROM team_puzzle_status 
                WHERE team_id = ? AND chapter_id = ? AND puzzle_id = ?
            ''', (team_id, chapter_id, puzzle_id))
            
            if not cursor.fetchone():
                # 插入新记录，设置初始提交次数和解锁时间
                cursor.execute('''
                    INSERT INTO team_puzzle_status 
                    (team_id, team_name, chapter_id, chapter_name,
                     puzzle_id, puzzle_name, remaining_attempts, 
                     is_passed, unlock_time, last_submit_time)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    team_id, team_name, chapter_id, chapter_name,
                    puzzle_id, puzzle_name, SUBMIT_COUNT_LIMIT,
                    0, unlock_time, None  # 初始未通过，无提交时间
                ))
        
        return True, "章节题目初始化成功"
    except sqlite3.Error as e:
        print(f"初始化章节题目失败: {str(e)}")
        return False, f"初始化失败：{str(e)}"

"""解锁队伍的下一个章节"""
def unlock_next_chapter(team_id):
    """解锁队伍的下一个章节"""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        # 获取当前章节
        cursor.execute('''
            SELECT current_chapter_id FROM teams WHERE team_id = ?
        ''', (team_id,))
        current_chapter_id = cursor.fetchone()[0]
        next_chapter_id = current_chapter_id + 1
        
        # 更新队伍当前章节
        cursor.execute('''
            UPDATE teams SET current_chapter_id = ? WHERE team_id = ?
        ''', (next_chapter_id, team_id))
        
        # 初始化下一章节的题目状态，解锁时间为当前时间
        current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        init_chapter_puzzle_status(team_id, next_chapter_id, current_time)
        
        conn.commit()
        return True
    except sqlite3.Error as e:
        print(f"解锁章节失败: {str(e)}")
        return False
    finally:
        conn.close()

def get_puzzle_answer(chapter_id, puzzle_id):
    """根据章节ID和题目ID获取正确答案"""
    puzzle_info = load_puzzle_info()
    for chapter in puzzle_info["chapters"]:
        if chapter["id"] == chapter_id:
            for puzzle in chapter["puzzle"]:
                if puzzle["id"] == int(puzzle_id):
                    return puzzle["answer"]
    return None

def get_puzzle_milestone(chapter_id, puzzle_id):
    """根据章节ID和题目ID获取里程碑"""
    puzzle_info = load_puzzle_info()
    for chapter in puzzle_info["chapters"]:
        if chapter["id"] == chapter_id:
            for puzzle in chapter["puzzle"]:
                if puzzle["id"] == int(puzzle_id):
                    return puzzle["milestone"]
    return None

"""提交题目答案并更新状态（含用户昵称、章节名和题目名）"""
# ------------------------------
# 拆分的辅助函数
# ------------------------------
def _get_team_and_user_info(cursor, team_id, user_id):
    """获取队伍名和用户昵称"""
    cursor.execute("SELECT team_name FROM teams WHERE team_id = ?", (team_id,))
    team_result = cursor.fetchone()
    team_name = team_result[0] if team_result else None
    
    user_name = get_user_nickname(user_id, team_id)
    return team_name, user_name

def _get_puzzle_details(chapter_id, puzzle_id):
    """获取题目相关信息（章节名、题目名、正确答案、里程碑）"""
    puzzle_info = load_puzzle_info()
    chapter_name = None
    puzzle_name = None
    correct_answer = None
    milestones = []
    
    for chapter in puzzle_info["chapters"]:
        if chapter["id"] == chapter_id:
            chapter_name = chapter["name"]
            for puzzle in chapter["puzzle"]:
                if puzzle["id"] == int(puzzle_id):
                    puzzle_name = puzzle["name"]
                    correct_answer = puzzle["answer"]
                    milestones = puzzle.get("milestone", [])
                    break
            break
    return chapter_name, puzzle_name, correct_answer, milestones

def _check_submission_status(cursor, team_id, chapter_id, puzzle_id):
    """检查题目是否已通过或提交次数耗尽"""
    cursor.execute('''
        SELECT is_passed, remaining_attempts FROM team_puzzle_status 
        WHERE team_id = ? AND chapter_id = ? AND puzzle_id = ?
    ''', (team_id, chapter_id, puzzle_id))
    status_result = cursor.fetchone()
    
    if status_result:
        is_passed, remaining = status_result
        # 这里，重复提交增加一行提示
        if is_passed:
            return {"valid": True, "is_passed": True, "message": "(该题目已通过)", "is_correct": False,
                    "remaining": status_result[1] if status_result else SUBMIT_COUNT_LIMIT}
        if remaining <= 0:
            return {"valid": False, "message": "提交次数已耗尽，无法继续提交", "is_correct": False}
    return {"valid": True, "is_passed": status_result[0] if status_result else False, 
            "remaining": status_result[1] if status_result else SUBMIT_COUNT_LIMIT}

def _determine_result_type(user_answer, correct_answer, milestones):
    """判断提交结果类型（正确/里程碑/错误）"""
    user_answer_clean = ''.join(list(user_answer.strip().lower().split()))
    correct_answer_clean = ''.join(list(correct_answer.strip().lower().split()))
    # 检查是否触发里程碑
    for milestone in milestones:
        if user_answer_clean == milestone["content"].strip().lower():
            return "milestone", "🚩" + milestone["response"], False
    # 检查是否正确
    if user_answer_clean == correct_answer_clean:
        return "correct", "✅答案正确！", True
    # 错误答案
    return "incorrect", f"❌答案错误！", False

def _should_decrement_attempts(cursor, team_id, chapter_id, puzzle_id, user_answer, result_type):
    """判断是否需要减少提交次数（非重复错误答案）"""
    if result_type != "incorrect":
        return False
    # 检查是否提交过相同错误答案
    cursor.execute('''
        SELECT 1 FROM team_puzzle_submissions 
        WHERE team_id = ? AND chapter_id = ? AND puzzle_id = ? 
        AND submitted_answer = ? AND result = 'incorrect'
        LIMIT 1
    ''', (team_id, chapter_id, puzzle_id, user_answer))
    return cursor.fetchone() is None

def _update_puzzle_status(cursor, team_id, chapter_id, puzzle_id, team_name, chapter_name, puzzle_name,
                          is_passed, remaining_attempts, should_decrement, is_correct, current_time):
    """更新题目状态表，返回是否首次通过"""
    new_remaining = remaining_attempts - 1 if should_decrement else remaining_attempts
    # 已经通过，或者回答正确，都设为1
    new_passed = 1 if (is_passed or is_correct) else 0
    is_first_pass = not is_passed and is_correct  # 首次通过标记
    
    cursor.execute('''
        UPDATE team_puzzle_status 
        SET remaining_attempts = ?,is_passed = ?, last_submit_time = ?, 
            team_name = ?, chapter_name = ?, puzzle_name = ?
        WHERE team_id = ? AND chapter_id = ? AND puzzle_id = ?
    ''', (new_remaining, new_passed, current_time, team_name, 
            chapter_name, puzzle_name, team_id, chapter_id, puzzle_id))
    
    
    # 补充错误提示的剩余次数信息
    if not is_correct:
        return is_first_pass, f"\n剩余提交次数：{new_remaining}"
    return is_first_pass, ""

def _update_team_passed_count(cursor, team_id):
    """更新队伍总通过题目数，未完赛时更新合法通过数"""
    cursor.execute('''
        UPDATE teams 
        SET passed_puzzle_count = passed_puzzle_count + 1 
        WHERE team_id = ?
    ''', (team_id,))
    if not is_competition_end():
        cursor.execute('''
        UPDATE teams 
        SET valid_passed_puzzle_count = valid_passed_puzzle_count + 1 
        WHERE team_id = ?
    ''', (team_id,))

def _handle_chapter_unlock(cursor, team_id, chapter_id, puzzle_info, current_time):
    """处理章节解锁逻辑，返回解锁提示信息"""
    # 获取当前章节的解锁需求
    current_chapter = next((c for c in puzzle_info["chapters"] if c["id"] == chapter_id), None)
    if not current_chapter or "count_demand" not in current_chapter:
        return ""
    
    # 检查当前章节已通过题目数是否满足需求
    cursor.execute('''
        SELECT COUNT(*) FROM team_puzzle_status 
        WHERE team_id = ? AND chapter_id = ? AND is_passed = 1
    ''', (team_id, chapter_id))
    passed_count = cursor.fetchone()[0]
    if passed_count != current_chapter["count_demand"]:
        return ""
    
    # 查找下一章并解锁
    all_chapters = sorted(puzzle_info["chapters"], key=lambda x: x["id"])
    current_index = next((i for i, c in enumerate(all_chapters) if c["id"] == chapter_id), -1)
    
    if current_index == -1 or current_index + 1 >= len(all_chapters):
        # 最后一章，若比赛未结束则标记完赛
        if not is_competition_end():
            cursor.execute('''
                UPDATE teams 
                SET is_completed = 1, completed_time = ? 
                WHERE team_id = ?
            ''', ((datetime.datetime.now() - START_TIME).total_seconds() / 3600, team_id) )
            return f"{ENDING_INFO}\n\n"
        else:
            return f"\n\n{ENDING_INFO}\n(由于是比赛结束后完赛，完赛用时不会记录)"
    
    # 解锁下一章，未结束时增加合法id
    next_chapter = all_chapters[current_index + 1]
    cursor.execute('''
        UPDATE teams 
        SET current_chapter_id = ? 
        WHERE team_id = ?
    ''', (next_chapter["id"], team_id))
    if not is_competition_end():
        cursor.execute('''
        UPDATE teams 
        SET valid_chapter_id = ?
        WHERE team_id = ?
    ''', (next_chapter["id"], team_id))


    # 初始化下一章题目状态
    init_success, init_msg = init_chapter_puzzle_status(
        cursor, team_id, next_chapter["id"], current_time
    )
    if not init_success:
        print(f"章节{next_chapter['id']}初始化失败：{init_msg}")
    return f"\n\n章节“{next_chapter['name']}”已解锁！\n请回复 /题目 {next_chapter['name']} 查看。"

def _save_submission_record(cursor, team_id, team_name, user_id, user_name, chapter_id, chapter_name,
                            puzzle_id, puzzle_name, user_answer, result_type, current_time):
    """保存提交记录到数据库"""
    cursor.execute('''
        INSERT INTO team_puzzle_submissions 
        (team_id, team_name, user_id, user_name, chapter_id, chapter_name,
         puzzle_id, puzzle_name, submitted_answer, result, submit_time)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (team_id, team_name, user_id, user_name, chapter_id, chapter_name,
          puzzle_id, puzzle_name, user_answer, result_type, current_time))

def submit_puzzle_answer(team_id, chapter_id, puzzle_id, user_answer, user_id):
    """提交题目答案并更新状态（含用户昵称、章节名和题目名）"""
    conn = get_db_connection()
    cursor = conn.cursor()
    current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    try:
        # 1. 获取队伍和用户基础信息
        team_name, user_name = _get_team_and_user_info(cursor, team_id, user_id)
        if not team_name or not user_name:
            return False, "队伍或用户信息不存在", False
        
        # 2. 获取题目详情（章节名、题目名、正确答案、里程碑）
        chapter_name, puzzle_name, correct_answer, milestones = _get_puzzle_details(chapter_id, puzzle_id)
        if not all([chapter_name, puzzle_name, correct_answer]):
            return False, "章节、题目或答案信息缺失", False
        
        # 3. 检查题目提交状态（是否已通过/次数耗尽）
        status_check = _check_submission_status(cursor, team_id, chapter_id, puzzle_id)
        if not status_check["valid"]:
            conn.commit()
            return True, status_check["message"], status_check["is_correct"]
        
        is_passed, remaining_attempts = status_check["is_passed"], status_check["remaining"]
        
        # 4. 判断提交结果（正确/里程碑/错误）
        result_type, message, is_correct = _determine_result_type(
            user_answer, correct_answer, milestones
        )
        
        # 5. 计算是否需要减少提交次数，即是否是非重复错误答案
        should_decrement = _should_decrement_attempts(
            cursor, team_id, chapter_id, puzzle_id, user_answer, result_type
        )
        # 如果答案错误且重复，修改message
        if result_type == "incorrect" and not should_decrement:
            message = "已提交过相同错误答案。"
        #如果已通过，在message前加上“您的队伍已通过此题”
        if is_passed:
            message = f"您的队伍已通过此题，此题的答案是「{correct_answer}」。\n" + message
        
        # 6. 更新题目状态表，并处理首次通过标记
        is_first_pass, remaining_attempts_msg = _update_puzzle_status(
            cursor, team_id, chapter_id, puzzle_id, team_name, chapter_name, puzzle_name,
            is_passed, remaining_attempts, should_decrement, is_correct, current_time
        )
        #添加一行次数
        message += remaining_attempts_msg
        
        # 7. 首次通过时更新队伍总通过数
        if is_first_pass:
            _update_team_passed_count(cursor, team_id)
        
        # 8. 首次通过且答案正确时处理章节解锁逻辑
        if is_first_pass and is_correct:
            unlock_msg = _handle_chapter_unlock(cursor, team_id, chapter_id, load_puzzle_info(), current_time)
            if unlock_msg:
                message += unlock_msg
        # 如果是最后一题答案正确也添加信息
        elif chapter_id == 5 and is_correct:
            message += f"{ENDING_INFO}"
        
        # 9. 保存提交记录
        _save_submission_record(
            cursor, team_id, team_name, user_id, user_name, chapter_id, chapter_name,
            puzzle_id, puzzle_name, user_answer, result_type, current_time
        )
        
        conn.commit()
        return True, message, is_correct
    
    except sqlite3.Error as e:
        return False, f"提交失败：{str(e)}", False
    finally:
        conn.close()



def get_team_puzzle_status(team_id, chapter_id=None):
    """获取队伍答题状态"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        if chapter_id:
            cursor.execute('''
                SELECT team_name, chapter_name, puzzle_id, puzzle_name, 
                       remaining_attempts, is_passed, last_submit_time 
                FROM team_puzzle_status 
                WHERE team_id = ? AND chapter_id = ?
            ''', (team_id, chapter_id))
        else:
            cursor.execute('''
                SELECT team_name, chapter_id, chapter_name, puzzle_id, puzzle_name, 
                       remaining_attempts, is_passed, last_submit_time 
                FROM team_puzzle_status 
                WHERE team_id = ?
            ''', (team_id,))
        
        results = cursor.fetchall()
        status_list = []
        for row in results:
            if chapter_id:
                status_list.append({
                    "team_name": row[0],
                    "chapter_id": chapter_id,
                    "chapter_name": row[1],
                    "puzzle_id": row[2],
                    "puzzle_name": row[3],
                    "remaining_attempts": row[4],
                    "is_passed": row[5] == 1,
                    "last_submit_time": row[6]
                })
            else:
                status_list.append({
                    "team_name": row[0],
                    "chapter_id": row[1],
                    "chapter_name": row[2],
                    "puzzle_id": row[3],
                    "puzzle_name": row[4],
                    "remaining_attempts": row[5],  # 改为剩余次数
                    "is_passed": row[6] == 1,
                    "last_submit_time": row[7]
                })

        return status_list
    finally:
        conn.close()

def get_team_submission_history(team_id, chapter_id=None, puzzle_id=None, page=1, per_page=10):
    """获取队伍提交历史（支持分页和筛选）"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # 先查询总记录数
        count_query = """
        SELECT COUNT(*) FROM team_puzzle_submissions 
        WHERE team_id = ?
        """
        count_params = [team_id]
        
        if chapter_id:
            count_query += " AND chapter_id = ?"
            count_params.append(chapter_id)
        if puzzle_id:
            count_query += " AND puzzle_id = ?"
            count_params.append(puzzle_id)
            
        cursor.execute(count_query, count_params)
        total = cursor.fetchone()[0]
        
        # 计算分页偏移量
        offset = (page - 1) * per_page
        
        # 查询当前页记录
        query = """
        SELECT user_name, chapter_id, chapter_name, 
               puzzle_id, puzzle_name, 
               submitted_answer, result, submit_time 
        FROM team_puzzle_submissions 
        WHERE team_id = ?
        """
        params = [team_id]
        
        if chapter_id:
            query += " AND chapter_id = ?"
            params.append(chapter_id)
        if puzzle_id:
            query += " AND puzzle_id = ?"
            params.append(puzzle_id)
            
        query += " ORDER BY submit_time DESC LIMIT ? OFFSET ?"
        params.extend([per_page, offset])
        
        cursor.execute(query, params)
        results = cursor.fetchall()
        
        # 计算总页数
        total_pages = (total + per_page - 1) // per_page
        
        return {
            "records": [
                {
                    "user_name": row[0],
                    "chapter_id": row[1],
                    "chapter_name": row[2],
                    "puzzle_id": row[3],
                    "puzzle_name": row[4],
                    "submitted_answer": row[5],
                    "result": row[6],
                    "submit_time": row[7]
                } for row in results
            ],
            "total": total,
            "total_pages": total_pages,
            "current_page": page,
            "per_page": per_page
        }
    finally:
        conn.close()

def unlock_hint(team_id, chapter_id, puzzle_id, hint_id):
    """解锁提示，返回成功与否和消息"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # 1. 检查提示是否已解锁
        cursor.execute('''
            SELECT 1 FROM team_unlocked_hints 
            WHERE team_id = ? AND chapter_id = ? AND puzzle_id = ? AND hint_id = ?
        ''', (team_id, chapter_id, puzzle_id, hint_id))
        if cursor.fetchone():
            return False, "该提示已解锁"
        
        # 2. 获取提示的cost
        puzzle_info = load_puzzle_info()
        hint_cost = None
        hint_response = None
        hint_title = None
        
        for chapter in puzzle_info["chapters"]:
            if chapter["id"] == chapter_id:
                for puzzle in chapter["puzzle"]:
                    if puzzle["id"] == int(puzzle_id):
                        for hint in puzzle.get("hints", []):
                            if hint["id"] == int(hint_id):
                                hint_cost = hint["cost"]
                                hint_content = hint["content"]
                                hint_title = hint["title"]
                                break
                        break
                break
        
        if hint_cost is None:
            return False, "未找到该提示"
        
        # 3. 检查队伍点数是否足够
        cursor.execute("SELECT points FROM teams WHERE team_id = ?", (team_id,))
        team_points = cursor.fetchone()[0]
        
        if team_points < hint_cost:
            return False, f"{POINT_NAME}不足，需要{hint_cost}{POINT_NAME}，当前只有{team_points}{POINT_NAME}"
        
        # 4. 扣除点数并记录解锁状态
        cursor.execute('''
            UPDATE teams 
            SET points = points - ? 
            WHERE team_id = ?
        ''', (hint_cost, team_id))
        
        current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cursor.execute('''
            INSERT INTO team_unlocked_hints 
            (team_id, chapter_id, puzzle_id, hint_id, unlock_time)
            VALUES (?, ?, ?, ?, ?)
        ''', (team_id, chapter_id, puzzle_id, hint_id, current_time))
        
        conn.commit()
        return True, f"{hint_id}.{hint_title}（已解锁）\n{hint_content}"
    
    except sqlite3.Error as e:
        return False, f"解锁失败：{str(e)}"
    finally:
        conn.close()

def add_submit_count(team_id, chapter_id, puzzle_id):
    """增加题目提交次数"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # 1. 检查队伍是否存在并获取当前点数
        cursor.execute("SELECT points FROM teams WHERE team_id = ?", (team_id,))
        team_data = cursor.fetchone()
        if not team_data:
            return False, "队伍不存在"
        current_points = team_data[0]
        
        # 2. 检查点数是否足够
        if current_points < ADD_SUBMIT_COUNT_COST:
            return False, f"{POINT_NAME}不足，需要{ADD_SUBMIT_COUNT_COST}{POINT_NAME}，当前剩余{current_points}{POINT_NAME}"
        
        # 3. 检查题目状态记录是否存在
        cursor.execute('''
            SELECT 1 FROM team_puzzle_status 
            WHERE team_id = ? AND chapter_id = ? AND puzzle_id = ?
        ''', (team_id, chapter_id, puzzle_id))
        if not cursor.fetchone():
            return False, "该题目尚未有提交记录，无需增加次数"
        
        # 4. 检查是否已通过
        cursor.execute('''
            SELECT is_passed FROM team_puzzle_status 
            WHERE team_id = ? AND chapter_id = ? AND puzzle_id = ?
        ''', (team_id, chapter_id, puzzle_id))
        result = cursor.fetchone()
        if result:
            is_passed = result[0]
            # 只有当题目已通过，且不允许给已通过题目增加次数时，才阻止操作
            if is_passed and not CAN_ADD_PASSED_PUZZLE_SUBMIT_COUNT:
                return False, "该题目已通过，无需增加次数"
        
        # 5. 扣除点数并增加提交次数
        cursor.execute('''
            UPDATE teams 
            SET points = points - ? 
            WHERE team_id = ?
        ''', (ADD_SUBMIT_COUNT_COST, team_id))
        
        cursor.execute('''
            UPDATE team_puzzle_status 
            SET remaining_attempts = remaining_attempts + ? 
            WHERE team_id = ? AND chapter_id = ? AND puzzle_id = ?
        ''', (ADD_SUBMIT_COUNT, team_id, chapter_id, puzzle_id))
        
        conn.commit()
        return True, f"成功增加{ADD_SUBMIT_COUNT}次提交次数，花费{ADD_SUBMIT_COUNT_COST}{POINT_NAME}"
    
    except sqlite3.Error as e:
        return False, f"操作失败：{str(e)}"
    finally:
        conn.close()

def get_all_teams_submission_history(page=1, per_page=10):
    """获取所有队伍的提交记录（管理员用，支持分页）"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # 先查询总记录数
        cursor.execute("SELECT COUNT(*) FROM team_puzzle_submissions")
        total = cursor.fetchone()[0]
        
        # 计算分页偏移量
        offset = (page - 1) * per_page
        
        # 查询所有队伍的提交记录（关联队伍名称）
        cursor.execute('''
            SELECT t.team_name, s.team_id, s.user_name, s.chapter_id, s.chapter_name,
                   s.puzzle_id, s.puzzle_name, s.submitted_answer, s.result, s.submit_time 
            FROM team_puzzle_submissions s
            JOIN teams t ON s.team_id = t.team_id
            ORDER BY s.submit_time DESC 
            LIMIT ? OFFSET ?
        ''', (per_page, offset))
        
        results = cursor.fetchall()
        total_pages = (total + per_page - 1) // per_page
        
        return {
            "records": [
                {
                    "team_name": row[0],
                    "team_id": row[1],
                    "user_name": row[2],
                    "chapter_id": row[3],
                    "chapter_name": row[4],
                    "puzzle_id": row[5],
                    "puzzle_name": row[6],
                    "submitted_answer": row[7],
                    "result": row[8],
                    "submit_time": row[9]
                } for row in results
            ],
            "total": total,
            "total_pages": total_pages,
            "current_page": page,
            "per_page": per_page
        }
    finally:
        conn.close()
# ------------------------------
# 消息
# ------------------------------

"""队员发送消息到队伍"""
def send_team_message(team_id, user_id, user_name, content):
    # 检查字符数是否合法
    if len(content) > MESSAGE_CHAR_LIMIT:
        return False, f"发送失败，一条消息不可超过{MESSAGE_CHAR_LIMIT}个字符，可以分开发送。"

    conn = get_db_connection()
    cursor = conn.cursor()
    current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    try:
        # 队员消息默认is_replied=0（未回复）
        cursor.execute('''
            INSERT INTO team_messages 
            (team_id, sender_id, sender_name, content, is_admin, is_replied, reply_to, create_time)
            VALUES (?, ?, ?, ?, 0, 0, NULL, ?)
        ''', (team_id, user_id, user_name, content, current_time))
        
        # 增加队伍未回复计数
        cursor.execute('''
            UPDATE teams SET unreplied_count = unreplied_count + 1 WHERE team_id = ?
        ''', (team_id,))
        
        conn.commit()
        return True, "消息发送成功"
    except sqlite3.Error as e:
        return False, f"发送失败：{str(e)}"
    finally:
        conn.close()


"""获取队伍消息面板（队员视角）"""
def get_team_message_board(team_id, limit=MESSAGE_SHOW_LIMIT):
    """获取队伍消息面板（队员视角）"""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute('''
            SELECT sender_name, content, is_admin, create_time 
            FROM team_messages 
            WHERE team_id = ? 
            ORDER BY create_time DESC 
            LIMIT ?
        ''', (team_id, limit))
        messages = cursor.fetchall()
        return [
            {
                "sender": sender if is_admin == 0 else f"{ADMIN_NAME}",
                "content": content,
                "time": time
            } for sender, content, is_admin, time in reversed(messages)
        ]
    finally:
        conn.close()


def get_all_teams(page=1, page_size=10):
    """"管理员获取所有队伍列表"""
    offset = (page - 1) * page_size
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        # 按未回复消息数降序排序
        cursor.execute('''
            SELECT team_id, team_name, create_time, current_chapter_id,
                   passed_puzzle_count, points, unreplied_count
            FROM teams 
            ORDER BY unreplied_count DESC, create_time DESC
            LIMIT ? OFFSET ?
        ''', (page_size, offset))
        teams = cursor.fetchall()
        # 总页数计算
        cursor.execute("SELECT COUNT(*) FROM teams")
        total = cursor.fetchone()[0]
        total_pages = (total + page_size - 1) // page_size
        return {
            "teams": [
                {
                    "team_id": t[0],
                    "team_name": t[1],
                    "create_time": t[2],
                    "current_chapter": t[3],
                    "passed_puzzles": t[4],
                    "points": t[5],
                    "unreplied_count": t[6]  # 显示未回复消息数
                } for t in teams
            ],
            "total_pages": total_pages,
            "current_page": page
        }
    finally:
        conn.close()


def admin_get_team_board(team_id, limit=MESSAGE_SHOW_LIMIT):
    """管理员获取队伍面板"""
    team = get_team_by_id(team_id)
    if not team:
        return None, "队伍不存在"
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        # 获取所有消息（包含回复关联）
        cursor.execute('''
            SELECT id, sender_name, content, is_admin, is_replied, reply_to, create_time 
            FROM team_messages 
            WHERE team_id = ? 
            ORDER BY create_time DESC
            LIMIT ?
        ''', (team_id, limit))
        messages = cursor.fetchall()
        
        # 构建消息链（关联回复）
        msg_dict = {msg[0]: msg for msg in messages}
        message_list = []
        for msg in messages:
            msg_id, sender, content, is_admin, is_replied, reply_to, time = msg
            # 检查是否有回复
            reply_content = None
            if reply_to:
                reply_msg = msg_dict.get(reply_to)
                if reply_msg:
                    reply_content = f"→ 管理员回复：{reply_msg[2]}"
            
            message_list.append({
                "id": msg_id,
                "sender": sender if is_admin == 0 else f"{ADMIN_NAME}",
                "content": content,
                "time": time,
                "is_admin": is_admin,
                "is_replied": is_replied == 1,  # 队员消息是否已回复
                "reply": reply_content
            })
        
        return {
            "team_info": team,
            "messages": message_list
        }, None
    except sqlite3.Error as e:
        return None, f"获取失败：{str(e)}"
    finally:
        conn.close()


"""管理员回复队伍消息（自动标记所有未回复的队员消息为已回复）"""
def admin_reply_team(team_id, admin_id, admin_name, content):
    """管理员回复队伍消息（自动标记所有未回复的队员消息为已回复）"""

    # 检查权限
    if not is_admin(admin_id):
        return False, "权限不足"
    
    # 检查字符数是否合法
    if len(content) > MESSAGE_CHAR_LIMIT:
        return False, f"发送失败，一条消息不可超过{MESSAGE_CHAR_LIMIT}个字符，可以分开发送。"
    conn = get_db_connection()
    cursor = conn.cursor()
    current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    try:
        # 1. 插入管理员回复消息
        cursor.execute('''
            INSERT INTO team_messages 
            (team_id, sender_id, sender_name, content, is_admin, is_replied, reply_to, create_time)
            VALUES (?, ?, ?, ?, 1, 1, NULL, ?)
        ''', (team_id, admin_id, admin_name, content, current_time))
        
        # 2. 查询队伍中所有未回复的队员消息数量
        cursor.execute('''
            SELECT COUNT(*) FROM team_messages 
            WHERE team_id = ? AND is_admin = 0 AND is_replied = 0
        ''', (team_id,))
        unreplied_count = cursor.fetchone()[0]
        
        if unreplied_count > 0:
            # 3. 标记所有未回复的队员消息为已回复
            cursor.execute('''
                UPDATE team_messages 
                SET is_replied = 1 
                WHERE team_id = ? AND is_admin = 0 AND is_replied = 0
            ''', (team_id,))
            
            # 4. 减少队伍未回复计数（减去实际标记的数量）
            cursor.execute('''
                UPDATE teams SET unreplied_count = unreplied_count - ? 
                WHERE team_id = ? AND unreplied_count >= ?
            ''', (unreplied_count, team_id, unreplied_count))
        
        conn.commit()
        return True, f"回复成功"
    except sqlite3.Error as e:
        return False, f"回复失败：{str(e)}"
    finally:
        conn.close()


"""修改队伍点数"""
def update_team_points(team_id, amount, admin_id):
    """修改队伍点数"""
    if not is_admin(admin_id):
        return False, "权限不足"
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        # 检查队伍是否存在
        cursor.execute("SELECT 1 FROM teams WHERE team_id = ?", (team_id,))
        if not cursor.fetchone():
            return False, "队伍不存在"
        # 更新点数（支持正负）
        cursor.execute('''
            UPDATE teams SET points = points + ? WHERE team_id = ?
        ''', (amount, team_id))
        conn.commit()
        return True, f"{POINT_NAME}已调整{amount}，当前{POINT_NAME}：{get_team_by_id(team_id)['points']}"
    except sqlite3.Error as e:
        return False, f"操作失败：{str(e)}"
    finally:
        conn.close()

# ------------------------------
# 定时器与点数，信息展示
# ------------------------------
def add_points_to_all_teams(amount=10):
    """给所有队伍增加指定点数"""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("UPDATE teams SET points = points + ?", (amount,))
        conn.commit()
        return True, f"所有队伍已增加{amount}{POINT_NAME}"
    except sqlite3.Error as e:
        return False, f"增加{POINT_NAME}失败：{str(e)}"
    finally:
        conn.close()


"""获取队伍排行榜数据"""
def get_teams_ranking(page=1, per_page=20):
    """获取队伍排行榜数据"""
    offset = (page - 1) * per_page
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        # 先获取所有队伍，按排序规则排序
        # 完赛队伍排在前面，按completed_time升序；未完赛按current_chapter_id降序，再按passed_puzzle_count降序
        cursor.execute('''
            SELECT team_id, team_name, is_completed, completed_time, 
                   valid_chapter_id, valid_passed_puzzle_count
            FROM teams 
            ORDER BY 
                is_completed DESC,  -- 完赛的排在前面
                CASE WHEN is_completed = 1 THEN completed_time END ASC,  -- 完赛队伍按用时升序
                CASE WHEN is_completed = 0 THEN valid_chapter_id END DESC,  -- 未完赛按有效章节ID降序
                CASE WHEN is_completed = 0 THEN valid_passed_puzzle_count END DESC  -- 章节相同按有效过题数降序
            LIMIT ? OFFSET ?
        ''', (per_page, offset))
        
        teams = cursor.fetchall()
        
        # 获取总队伍数，用于计算总页数
        cursor.execute("SELECT COUNT(*) FROM teams")
        total = cursor.fetchone()[0]
        total_pages = (total + per_page - 1) // per_page
        
        # 转换时间格式：小时 -> xx:xx:xx
        def format_time(hours):
            if not hours:
                return ""
            total_seconds = int(hours * 3600)
            h = total_seconds // 3600
            m = (total_seconds % 3600) // 60
            s = total_seconds % 60
            return f"{h:02d}:{m:02d}:{s:02d}"
        
        return {
            "teams": [
                {
                    "team_id": t[0],
                    "team_name": t[1],
                    "is_completed": t[2] == 1,
                    "completed_time": format_time(t[3]),
                    "current_chapter_id": t[4],
                    "passed_puzzle_count": t[5]
                } for t in teams
            ],
            "total_pages": total_pages,
            "current_page": page,
            "total_teams": total
        }
    finally:
        conn.close()

def get_puzzle_submit_records(chapter_id, puzzle_id, page=1, page_size=10):
    """
    查询指定章节、题目的提交记录（分页）
    :param chapter_id: 章节ID
    :param puzzle_id: 题目ID
    :param page: 页码（默认第1页）
    :param page_size: 每页条数（默认10条）
    :return: 提交记录列表（字典格式）
    """
    # 类型转换与参数校验
    try:
        chapter_id = int(chapter_id)
        puzzle_id = int(puzzle_id)
        page = max(int(page), 1)  # 页码至少为1
        page_size = max(int(page_size), 1)  # 每页条数至少为1
    except ValueError:
        return []
    
    # 计算分页偏移量
    offset = (page - 1) * page_size
    
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        # 查询提交记录（按提交时间降序，最新的在前）
        cursor.execute('''
            SELECT team_id, team_name, user_name, submitted_answer, result, submit_time 
            FROM team_puzzle_submissions 
            WHERE chapter_id = ? AND puzzle_id = ?
            ORDER BY submit_time DESC
            LIMIT ? OFFSET ?
        ''', (chapter_id, puzzle_id, page_size, offset))
        
        # 解析结果为字典列表
        records = []
        columns = ["team_id", "team_name", "user_name", "submitted_answer", "result", "submit_time"]
        for row in cursor.fetchall():
            record = dict(zip(columns, row))
            # 转换result为文本
            result_map = {
                "correct": "✅正确",
                "milestone": "🚩里程碑",
                "incorrect": "❌错误"
            }
            record["result"] = result_map.get(record["result"], record["result"])
            records.append(record)
        
        return records
    except sqlite3.Error as e:
        print(f"查询提交记录失败：{str(e)}")
        return []
    finally:
        conn.close()


def start_points_timer():
    """启动定时任务，每分钟给所有队伍增加点数"""
    def timer_task():
        while True:
            #检查是否开赛
            if is_competition_started():
                add_points_to_all_teams(ADD_POINT_PER_MINUTE)
                # 等待60秒
                time.sleep(60)
    
    # 在后台线程运行定时任务
    thread = threading.Thread(target=timer_task, daemon=True)
    thread.start()
    return thread