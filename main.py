import sys
import os
import random
import time
import json
import threading
import requests
from dotenv import load_dotenv
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                            QHBoxLayout, QPushButton, QLabel, QTextEdit, 
                            QGridLayout, QFrame, QMessageBox, QInputDialog)
from PyQt5.QtCore import Qt, QTimer, pyqtSignal, QObject
from PyQt5.QtGui import QFont, QPixmap, QColor

# 加载环境变量
load_dotenv()

# 获取API密钥
API_KEY = os.getenv("COZE_API_KEY")
if not API_KEY:
    raise ValueError("请在.env文件中设置COZE_API_KEY")

# 智能体配置
AGENTS = {
    "agent1": {
        "name": "谁是卧底1",
        "bot_id": "7516937350422462500",
        "user_id": "user1",
        "color": "#FFB6C1"  # 浅粉色
    },
    "agent2": {
        "name": "谁是卧底2",
        "bot_id": "7516949959041105960",
        "user_id": "user2",
        "color": "#ADD8E6"  # 浅蓝色
    },
    "agent3": {
        "name": "谁是卧底3",
        "bot_id": "7516952335664021558",
        "user_id": "user3",
        "color": "#90EE90"  # 浅绿色
    },
    "agent4": {
        "name": "谁是卧底4",
        "bot_id": "7516953397153792036",
        "user_id": "user4",
        "color": "#FFFACD"  # 浅黄色
    }
}

# 游戏主题配置
GAME_THEMES = [
    {"majority": "电脑", "minority": "笔记本"},
    {"majority": "西瓜", "minority": "南瓜"},
    {"majority": "足球", "minority": "篮球"},
    {"majority": "电影", "minority": "电视剧"},
    {"majority": "苹果", "minority": "梨"},
    {"majority": "咖啡", "minority": "奶茶"},
    {"majority": "微信", "minority": "QQ"},
    {"majority": "地铁", "minority": "公交车"},
    {"majority": "风扇", "minority": "空调"},
    {"majority": "太阳", "minority": "月亮"}
]

# 游戏事件信号类
class GameSignals(QObject):
    update_log = pyqtSignal(str)
    update_status = pyqtSignal(str)
    round_complete = pyqtSignal(dict)
    game_over = pyqtSignal(dict)
    player_eliminated = pyqtSignal(str, bool)  # player_key, is_undercover
    update_player_status = pyqtSignal(str, str, str)  # player_key, status, message

# 游戏逻辑类
class WhoIsUndercoverGame:
    def __init__(self, agents, game_themes):
        self.agents = agents
        self.game_themes = game_themes
        self.current_theme = None
        self.undercover = None
        self.players_alive = list(agents.keys())
        self.eliminated_players = []
        self.round = 0
        self.game_history = []
        self.signals = GameSignals()
        
    def log(self, message):
        """记录游戏日志"""
        print(message)
        self.signals.update_log.emit(message)
        
    def update_status(self, status):
        """更新游戏状态"""
        self.signals.update_status.emit(status)
        
    def update_player_status(self, player_key, status, message=""):
        """更新玩家状态"""
        self.signals.update_player_status.emit(player_key, status, message)
        
    def send_message_to_agent(self, agent_key, message):
        """向指定智能体发送消息并获取回复"""
        agent = self.agents[agent_key]
        self.update_player_status(agent_key, "thinking")
        
        headers = {
            "Authorization": f"Bearer {API_KEY}",
            "Content-Type": "application/json"
        }
        
        # 第一步：发起对话
        data = {
            "bot_id": agent["bot_id"],
            "user_id": agent["user_id"],
            "stream": False,
            "additional_messages": [
                {
                    "content": message,
                    "content_type": "text",
                    "role": "user",
                    "type": "question"
                }
            ]
        }
        
        try:
            # 发送初始请求
            self.log(f"正在向 {agent['name']} 发送请求...")
            response = requests.post("https://api.coze.cn/v3/chat", headers=headers, json=data)
            response.raise_for_status()
            result = response.json()
            
            # 获取conversation_id并等待对话执行完毕
            if 'data' in result and 'conversation_id' in result['data']:
                conversation_id = result['data']['conversation_id']
                id = result['data']['id']
                status = result['data'].get('status', 'unknown')
                # 等待处理完成
                time.sleep(5)
                while status != "completed":
                    time.sleep(2)
                    url = "https://api.coze.cn/v3/chat/retrieve"
                    params = {
                        "conversation_id": f"{conversation_id}",
                        "chat_id": f"{id}"
                    }
                    headers = {
                        "Authorization": f"Bearer {API_KEY}",
                        "Content-Type": "application/json"
                    }

                    response = requests.get(url, headers=headers, params=params)
                    result = response.json()
                    status = result['data']['status']
                
                # 获取消息内容
                message_url = "https://api.coze.cn/v3/chat/message/list"
                message_params = {
                    "conversation_id": f"{conversation_id}",
                    "chat_id": f"{id}"
                }
                message_headers = {
                    "Authorization": f"Bearer {API_KEY}",
                    "Content-Type": "application/json"
                }
                
                response = requests.get(message_url, headers=message_headers, params=message_params)
                result = response.json()
                answer = result['data'][0]['content']
                
                self.update_player_status(agent_key, "normal", answer)
                return answer
            elif 'error' in result:
                self.log(f"错误信息: {result['error']}")
                self.update_player_status(agent_key, "error", "API错误")
                return None
            else:
                self.log(f"无法获取conversation_id，响应内容: {json.dumps(result, ensure_ascii=False)}")
                self.update_player_status(agent_key, "error", "请求失败")
                return None
        except Exception as e:
            self.log(f"与智能体 {agent['name']} 通信时出错: {str(e)}")
            self.update_player_status(agent_key, "error", str(e))
            return None
    
    def initialize_game(self):
        """初始化游戏，分配词语"""
        self.round = 0
        self.players_alive = list(self.agents.keys())
        self.eliminated_players = []
        self.game_history = []
        
        self.update_status("初始化游戏...")
        
        # 随机选择一个主题
        self.current_theme = random.choice(self.game_themes)
        
        # 随机选择一个卧底
        self.undercover = random.choice(self.players_alive)
        
        # 初始化所有玩家状态
        for player in self.agents:
            self.update_player_status(player, "normal")
        
        # 向玩家发送他们的词语
        for player in self.players_alive:
            word = self.current_theme["minority"] if player == self.undercover else self.current_theme["majority"]
            message = f"游戏开始！你是: {self.agents[player]['name']} 你的词语是: {word}。请记住这个词语，不用给出描述"
            response = self.send_message_to_agent(player, message)
            
            if response:
                self.log(f"{self.agents[player]['name']} 已收到词语")
            
        self.log(f"游戏初始化完成！卧底是: {self.agents[self.undercover]['name']}")
        self.log(f"多数派词语: {self.current_theme['majority']}")
        self.log(f"卧底词语: {self.current_theme['minority']}")
        
        self.update_status("游戏已初始化")
    
    def play_round(self):
        """进行一轮游戏"""
        self.round += 1
        self.log(f"\n====== 第 {self.round} 轮 ======")
        self.update_status(f"第 {self.round} 轮")
        
        round_responses = {}
        
        # 每个玩家描述词语
        for player in self.players_alive:
            word = self.current_theme["minority"] if player == self.undercover else self.current_theme["majority"]
            message = f"你的词语是: {word}。请根据你的词语进行一句话描述，不要直接说出这个词。"
            description = self.send_message_to_agent(player, message)
            
            if description:
                round_responses[player] = description
                self.log(f"{self.agents[player]['name']} 描述: {description}")
            else:
                round_responses[player] = "无法获取有效回复"
                self.log(f"{self.agents[player]['name']} 无法获取有效回复")
        
        # 记录本轮历史
        self.game_history.append(round_responses)
        
        # 发送轮次完成信号
        self.signals.round_complete.emit({
            "round": self.round,
            "responses": round_responses
        })
        
        # 让每个玩家投票
        votes = self.conduct_voting()
        
        # 处理投票结果
        self.process_votes(votes)
        
        # 检查游戏是否结束
        return self.check_game_over()
    
    def conduct_voting(self):
        """进行投票"""
        votes = {}
        self.update_status("投票中...")
        
        # 构建投票信息
        vote_info = "你是: {self.agents[player]['name']}，请不要投票给自己，请根据以下描述，投票选出你认为是卧底的玩家(输入对应数字)，但请不要投给自己:\n"
        for i, player in enumerate(self.players_alive, 1):
            last_description = self.game_history[-1][player]
            vote_info += f"{i}. {self.agents[player]['name']}: {last_description}\n"
        
        # 收集每个玩家的投票
        for player in self.players_alive:
            message = vote_info
            vote_text = self.send_message_to_agent(player, message)
            
            if vote_text:
                # 尝试从回复中提取数字
                try:
                    # 简单处理：查找第一个数字
                    for char in vote_text:
                        if char.isdigit() and 1 <= int(char) <= len(self.players_alive):
                            vote_num = int(char)
                            voted_player = self.players_alive[vote_num - 1]
                            votes[player] = voted_player
                            self.log(f"{self.agents[player]['name']} 投票给了 {self.agents[voted_player]['name']}")
                            break
                    else:
                        # 如果没找到有效数字，随机投票
                        voted_player = random.choice([p for p in self.players_alive if p != player])
                        votes[player] = voted_player
                        self.log(f"{self.agents[player]['name']} 投票无效，系统随机分配给了 {self.agents[voted_player]['name']}")
                except Exception as e:
                    # 出错也随机投票
                    self.log(f"处理投票时出错: {str(e)}")
                    voted_player = random.choice([p for p in self.players_alive if p != player])
                    votes[player] = voted_player
                    self.log(f"{self.agents[player]['name']} 投票处理出错，系统随机分配给了 {self.agents[voted_player]['name']}")
            else:
                # 响应出错也随机投票
                voted_player = random.choice([p for p in self.players_alive if p != player])
                votes[player] = voted_player
                self.log(f"{self.agents[player]['name']} 无法获取投票，系统随机分配给了 {self.agents[voted_player]['name']}")
                
        return votes
    
    def process_votes(self, votes):
        """处理投票结果"""
        # 统计每个玩家获得的票数
        vote_count = {}
        for player in self.players_alive:
            vote_count[player] = 0
            
        for voter, voted in votes.items():
            vote_count[voted] += 1
        
        # 找出得票最多的玩家
        max_votes = max(vote_count.values())
        most_voted = [player for player, count in vote_count.items() if count == max_votes]
        
        # 如果有平票，随机选择一个
        eliminated = random.choice(most_voted)
        
        # 输出投票结果
        self.log("\n投票结果:")
        for player in self.players_alive:
            self.log(f"{self.agents[player]['name']}: {vote_count[player]} 票")
        
        # 移除被淘汰的玩家
        self.players_alive.remove(eliminated)
        self.eliminated_players.append(eliminated)
        
        self.log(f"\n{self.agents[eliminated]['name']} 被淘汰了！")
        is_undercover = (eliminated == self.undercover)
        if is_undercover:
            self.log("卧底被淘汰了！")
        else:
            self.log("平民被淘汰了！")
            
        # 发送玩家淘汰信号
        self.signals.player_eliminated.emit(eliminated, is_undercover)
        
        self.update_player_status(eliminated, "eliminated")
    
    def check_game_over(self):
        """检查游戏是否结束"""
        game_over = False
        winner = None
        
        # 如果卧底已被淘汰，平民获胜
        if self.undercover in self.eliminated_players:
            self.log("\n游戏结束！平民获胜！")
            game_over = True
            winner = "平民"
        
        # 如果只剩下卧底和一个平民，卧底获胜
        elif len(self.players_alive) <= 2 and self.undercover in self.players_alive:
            self.log("\n游戏结束！卧底获胜！")
            game_over = True
            winner = "卧底"
        
        if game_over:
            # 发送游戏结束信号
            self.signals.game_over.emit({
                "undercover": self.agents[self.undercover]['name'],
                "winner": winner,
                "rounds": self.round,
                "theme": self.current_theme
            })
            self.update_status(f"游戏结束 - {winner}获胜")
            
        return game_over
    
    def run_game(self):
        """运行完整游戏"""
        self.initialize_game()
        
        game_over = False
        while not game_over:
            game_over = self.play_round()
            if not game_over:
                time.sleep(2)  # 暂停几秒，便于阅读
        
        # 游戏结束，显示结果
        self.log("\n====== 游戏结果 ======")
        self.log(f"卧底是: {self.agents[self.undercover]['name']}")
        self.log(f"卧底词语: {self.current_theme['minority']}")
        self.log(f"多数派词语: {self.current_theme['majority']}")
        
        return {
            "undercover": self.agents[self.undercover]['name'],
            "winner": "平民" if self.undercover in self.eliminated_players else "卧底",
            "rounds": self.round,
            "theme": self.current_theme
        }

# UI组件 - 玩家卡片
class PlayerCard(QFrame):
    def __init__(self, player_key, player_info):
        super().__init__()
        self.player_key = player_key
        self.player_info = player_info
        self.status = "normal"  # normal, thinking, eliminated, error
        self.description = ""
        self.setupUI()
        
    def setupUI(self):
        self.setFrameShape(QFrame.Box)
        self.setLineWidth(2)
        self.setStyleSheet(f"background-color: {self.player_info['color']}; border-radius: 10px;")
        
        layout = QVBoxLayout()
        
        # 玩家名称
        self.name_label = QLabel(self.player_info['name'])
        self.name_label.setAlignment(Qt.AlignCenter)
        self.name_label.setFont(QFont("Arial", 14, QFont.Bold))
        
        # 状态指示
        self.status_label = QLabel("准备中")
        self.status_label.setAlignment(Qt.AlignCenter)
        self.status_label.setFont(QFont("Arial", 10))
        
        # 描述文本
        self.description_text = QTextEdit()
        self.description_text.setReadOnly(True)
        self.description_text.setPlaceholderText("等待描述...")
        self.description_text.setMaximumHeight(100)
        
        layout.addWidget(self.name_label)
        layout.addWidget(self.status_label)
        layout.addWidget(self.description_text)
        
        self.setLayout(layout)
        self.setMinimumSize(200, 150)
        
    def update_status(self, status, message=""):
        self.status = status
        
        if status == "normal":
            self.status_label.setText("正常")
            self.setStyleSheet(f"background-color: {self.player_info['color']}; border-radius: 10px;")
            if message:
                self.description_text.setText(message)
                self.description = message
        elif status == "thinking":
            self.status_label.setText("思考中...")
            self.setStyleSheet(f"background-color: {self.player_info['color']}; border: 2px dashed #666; border-radius: 10px;")
        elif status == "eliminated":
            self.status_label.setText("已淘汰")
            self.setStyleSheet("background-color: #D3D3D3; border-radius: 10px;")
        elif status == "error":
            self.status_label.setText(f"错误: {message}")
            self.setStyleSheet("background-color: #FFCCCB; border-radius: 10px;")
        elif status == "undercover":
            self.status_label.setText("卧底")
            self.setStyleSheet("background-color: #FF9999; border-radius: 10px;")
        elif status == "civilian":
            self.status_label.setText("平民")
            self.setStyleSheet("background-color: #99CCFF; border-radius: 10px;")

# 主窗口
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.game = WhoIsUndercoverGame(AGENTS, GAME_THEMES)
        self.setupUI()
        self.connectSignals()
        
    def setupUI(self):
        self.setWindowTitle("谁是卧底")
        self.setMinimumSize(800, 600)
        
        # 主窗口部件
        central_widget = QWidget()
        main_layout = QVBoxLayout(central_widget)
        
        # 顶部状态栏
        top_layout = QHBoxLayout()
        self.status_label = QLabel("准备开始游戏")
        self.status_label.setFont(QFont("Arial", 12, QFont.Bold))
        self.round_label = QLabel("回合: 0")
        
        top_layout.addWidget(self.status_label)
        top_layout.addStretch()
        top_layout.addWidget(self.round_label)
        
        # 玩家区域
        players_layout = QGridLayout()
        self.player_cards = {}
        
        row, col = 0, 0
        for player_key, player_info in AGENTS.items():
            card = PlayerCard(player_key, player_info)
            self.player_cards[player_key] = card
            players_layout.addWidget(card, row, col)
            col += 1
            if col > 1:
                col = 0
                row += 1
        
        # 游戏日志区域
        log_layout = QVBoxLayout()
        log_label = QLabel("游戏日志")
        log_label.setFont(QFont("Arial", 12, QFont.Bold))
        
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        
        log_layout.addWidget(log_label)
        log_layout.addWidget(self.log_text)
        
        # 控制按钮区域
        control_layout = QHBoxLayout()
        
        self.start_button = QPushButton("开始游戏")
        self.start_button.setFont(QFont("Arial", 12))
        self.start_button.setMinimumHeight(40)
        
        self.next_round_button = QPushButton("下一轮")
        self.next_round_button.setFont(QFont("Arial", 12))
        self.next_round_button.setMinimumHeight(40)
        self.next_round_button.setEnabled(False)
        
        self.new_game_button = QPushButton("新游戏")
        self.new_game_button.setFont(QFont("Arial", 12))
        self.new_game_button.setMinimumHeight(40)
        self.new_game_button.setEnabled(False)
        
        control_layout.addWidget(self.start_button)
        control_layout.addWidget(self.next_round_button)
        control_layout.addWidget(self.new_game_button)
        
        # 主布局
        main_layout.addLayout(top_layout)
        main_layout.addLayout(players_layout)
        main_layout.addLayout(log_layout)
        main_layout.addLayout(control_layout)
        
        self.setCentralWidget(central_widget)
    
    def connectSignals(self):
        # 连接游戏信号
        self.game.signals.update_log.connect(self.updateLog)
        self.game.signals.update_status.connect(self.updateStatus)
        self.game.signals.round_complete.connect(self.onRoundComplete)
        self.game.signals.game_over.connect(self.onGameOver)
        self.game.signals.player_eliminated.connect(self.onPlayerEliminated)
        self.game.signals.update_player_status.connect(self.updatePlayerStatus)
        
        # 连接按钮信号
        self.start_button.clicked.connect(self.startGame)
        self.next_round_button.clicked.connect(self.nextRound)
        self.new_game_button.clicked.connect(self.newGame)
    
    def updateLog(self, message):
        self.log_text.append(message)
        # 滚动到底部
        self.log_text.verticalScrollBar().setValue(self.log_text.verticalScrollBar().maximum())
    
    def updateStatus(self, status):
        self.status_label.setText(status)
    
    def updatePlayerStatus(self, player_key, status, message=""):
        if player_key in self.player_cards:
            self.player_cards[player_key].update_status(status, message)
    
    def onRoundComplete(self, data):
        self.round_label.setText(f"回合: {data['round']}")
        self.next_round_button.setEnabled(True)
    
    def onGameOver(self, data):
        self.next_round_button.setEnabled(False)
        self.new_game_button.setEnabled(True)
        
        # 显示游戏结果
        result_message = (
            f"游戏结束!\n\n"
            f"卧底是: {data['undercover']}\n"
            f"多数派词语: {data['theme']['majority']}\n"
            f"卧底词语: {data['theme']['minority']}\n"
            f"经过 {data['rounds']} 轮后，{data['winner']}获胜!"
        )
        
        QMessageBox.information(self, "游戏结束", result_message)
        
        # 揭示所有玩家身份
        for player_key in AGENTS:
            if player_key == self.game.undercover:
                self.updatePlayerStatus(player_key, "undercover")
            else:
                self.updatePlayerStatus(player_key, "civilian")
    
    def onPlayerEliminated(self, player_key, is_undercover):
        # 可以添加动画或特效
        pass
    
    def startGame(self):
        self.start_button.setEnabled(False)
        self.next_round_button.setEnabled(False)
        self.new_game_button.setEnabled(False)
        
        # 清空日志
        self.log_text.clear()
        self.round_label.setText("回合: 0")
        
        # 在新线程中初始化游戏
        threading.Thread(target=self.game.initialize_game, daemon=True).start()
        
        # 初始化完成后启用下一轮按钮
        QTimer.singleShot(2000, lambda: self.next_round_button.setEnabled(True))
    
    def nextRound(self):
        self.next_round_button.setEnabled(False)
        
        # 在新线程中进行下一轮
        threading.Thread(target=self.game.play_round, daemon=True).start()
    
    def newGame(self):
        self.start_button.setEnabled(True)
        self.next_round_button.setEnabled(False)
        self.new_game_button.setEnabled(False)
        
        # 重置所有玩家状态
        for player_key in self.player_cards:
            self.player_cards[player_key].update_status("normal")
            self.player_cards[player_key].description_text.clear()

# 应用程序入口
def main():
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()