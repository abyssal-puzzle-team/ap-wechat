import sqlite3
import datetime  # 用来记录创建/加入时间

# 连接数据库（如果文件不存在，会自动在当前文件夹创建）
conn = sqlite3.connect("abyssal_puzzle.db")
cursor = conn.cursor()  # 用来执行SQL语句的工具

# 创建队伍表（teams）：存队伍信息
cursor.execute('''
CREATE TABLE IF NOT EXISTS teams (
    team_id INTEGER PRIMARY KEY AUTOINCREMENT,
    team_name TEXT NOT NULL,
    create_time TEXT NOT NULL,
    invitation_code TEXT NOT NULL,
    current_chapter_id INTEGER DEFAULT 0,
    valid_chapter_id INTEGER DEFAULT 0,
    passed_puzzle_count INTEGER DEFAULT 0,
    valid_passed_puzzle_count INTEGER DEFAULT 0,
    points INTEGER DEFAULT 0,
    unreplied_count INTEGER DEFAULT 0,
    is_completed INTEGER DEFAULT 0,
    completed_time REAL DEFAULT 0,
               
   UNIQUE(team_name)
)
''')

# 创建队员表（team_members）：存用户和队伍的关联
cursor.execute('''
CREATE TABLE IF NOT EXISTS team_members (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    team_id INTEGER NOT NULL,
    user_id TEXT NOT NULL,
    user_name TEXT NOT NULL,
    join_time TEXT NOT NULL,
    is_leader BOOLEAN DEFAULT 0,
    
    UNIQUE(team_id, user_id),
    
    FOREIGN KEY(team_id) REFERENCES teams(team_id)
)
''')
# 确保一个用户不能重复加入同一个队伍
# 关联队伍表（如果队伍不存在，就不能加队员）


# 队伍的题目状态表
cursor.execute('''
CREATE TABLE IF NOT EXISTS team_puzzle_status (
    team_id INTEGER NOT NULL,
    team_name TEXT NOT NULL,
    chapter_id INTEGER NOT NULL,
    chapter_name TEXT NOT NULL,
    puzzle_id INTEGER NOT NULL,
    puzzle_name TEXT NOT NULL,
    remaining_attempts INTEGER DEFAULT 20,
    is_passed BOOLEAN DEFAULT 0,
    unlock_time DATETIME,
    last_submit_time DATETIME,
    
    PRIMARY KEY (team_id, chapter_id, puzzle_id),
    FOREIGN KEY(team_id) REFERENCES teams(team_id) ON DELETE CASCADE
)
''')


# team_puzzle_submissions 表
cursor.execute('''
CREATE TABLE IF NOT EXISTS team_puzzle_submissions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    team_id INTEGER NOT NULL,
    team_name TEXT NOT NULL,
    user_id TEXT NOT NULL,
    user_name TEXT NOT NULL,
    chapter_id INTEGER NOT NULL,
    chapter_name TEXT NOT NULL,
    puzzle_id INTEGER NOT NULL,
    puzzle_name TEXT NOT NULL,
    submitted_answer TEXT NOT NULL,
    result TEXT NOT NULL, -- 'correct'正确, 'milestone'里程碑, 'incorrect'错误
    submit_time TEXT NOT NULL,
    
    FOREIGN KEY(team_id) REFERENCES teams(team_id) ON DELETE CASCADE
)
''')


# 队伍解锁的提示状态表
cursor.execute('''
CREATE TABLE IF NOT EXISTS team_unlocked_hints (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    team_id INTEGER NOT NULL,
    chapter_id INTEGER NOT NULL,
    puzzle_id INTEGER NOT NULL,
    hint_id INTEGER NOT NULL,
    unlock_time TEXT NOT NULL,
    
    UNIQUE(team_id, chapter_id, puzzle_id, hint_id),
    FOREIGN KEY(team_id) REFERENCES teams(team_id) ON DELETE CASCADE
)
''')


# 队伍消息表
cursor.execute('''CREATE TABLE IF NOT EXISTS team_messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    team_id INTEGER NOT NULL,
    sender_id TEXT NOT NULL, -- 发送者ID（队员/管理员）
    sender_name TEXT NOT NULL, -- 发送者名称
    content TEXT NOT NULL,
    is_admin INTEGER DEFAULT 0, -- 0:队员 1:管理员
    is_replied INTEGER DEFAULT 1, -- 对管理员而言是否已回复（1:已回复）
    reply_to INTEGER DEFAULT NULL,
    create_time TEXT NOT NULL,
    FOREIGN KEY (team_id) REFERENCES teams(team_id)
)
''')


# 提交操作并关闭连接
conn.commit()
conn.close()

print("数据库创建成功")