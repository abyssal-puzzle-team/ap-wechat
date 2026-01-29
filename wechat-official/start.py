import sqlite3
import datetime  # 用来记录创建/加入时间
import db_utils

# 连接数据库
conn = sqlite3.connect("abyssal_puzzle.db")
cursor = conn.cursor()

# 把所有队伍章节设为1
cursor.execute('''
UPDATE teams
SET current_chapter_id = 1, valid_chapter_id = 1
''')

# 获取所有队伍ID
cursor.execute("SELECT team_id FROM teams")
teams = cursor.fetchall()
start_time_str = db_utils.START_TIME.strftime("%Y-%m-%d %H:%M:%S")  # 与db_utils中的START_TIME一致

for team in teams:
    team_id = team[0]
    # 初始化第一章（chapter_id=1）
    success, msg = db_utils.init_chapter_puzzle_status(cursor, team_id, 1, start_time_str)
    if not success:
        print(f"队伍{team_id}第一章初始化失败：{msg}")


conn.commit()
conn.close()


print("设置完成")

