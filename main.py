import numpy as num
import requests
import json
import random
import time
import os
from dotenv import load_dotenv

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
        "user_id": "user1"
    },
    "agent2": {
        "name": "谁是卧底2",
        "bot_id": "7516949959041105960",
        "user_id": "user2"
    },
    "agent3": {
        "name": "谁是卧底3",
        "bot_id": "7516952335664021558",
        "user_id": "user3"
    },
    "agent4": {
        "name": "谁是卧底4",
        "bot_id": "7516953397153792036",
        "user_id": "user4"
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
        
    def send_message_to_agent(self, agent_key, message):
        """向指定智能体发送消息并获取回复"""
        agent = self.agents[agent_key]
        
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
            print(f"正在向 {agent_key} 发送请求...")
            response = requests.post("https://api.coze.cn/v3/chat", headers=headers, json=data)
            response.raise_for_status()
            result = response.json()
            
            # 获取conversation_id并等待对话执行完毕
            if 'data' in result and 'conversation_id' in result['data']:
                conversation_id = result['data']['conversation_id']
                id = result['data']['id']
                # print(f"获取到conversation_id和id: {conversation_id}, {id}")
                status = result['data'].get('status', 'unknown')
                # 等待处理完成
                time.sleep(5)
                while status != "completed":

                   # print(f"当前状态: {status}，等待中...")
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
                    # print(result) 
            
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
                #print(result['data'])
                answer = result['data'][0]['content']
                # 找到最后一条assistant的回复
                return answer
            elif 'error' in result:
                print(f"错误信息: {result['error']}")
                return None
            elif 'data' in result and 'conversation_id' not in result['data']:
                # 如果没有找到conversation_id，可能是请求格式或参数有误
                print("未找到模型回复")
                return None
            else:
                print(f"无法获取conversation_id，响应内容: {json.dumps(result, ensure_ascii=False)}")
                return None
        except Exception as e:
            print(f"与智能体 {agent_key} 通信时出错: {str(e)}")
            return None
    
    def initialize_game(self):
        """初始化游戏，分配词语"""
        self.round = 0
        self.players_alive = list(self.agents.keys())
        self.eliminated_players = []
        self.game_history = []
        
        # 随机选择一个主题
        self.current_theme = random.choice(self.game_themes)
        
        # 随机选择一个卧底
        self.undercover = random.choice(self.players_alive)
        
        # 向玩家发送他们的词语
        for player in self.players_alive:
            word = self.current_theme["minority"] if player == self.undercover else self.current_theme["majority"]
            message = f"游戏开始！你的词语是: {word}。请记住这个词语，不用给出描述"
            response = self.send_message_to_agent(player, message)
            #print(response)
            # 这里可以处理响应，比如打印出来或保存
            if response:
                print(f"{self.agents[player]['name']} 已收到词语")
            
        print(f"游戏初始化完成！卧底是: {self.agents[self.undercover]['name']}")
        print(f"多数派词语: {self.current_theme['majority']}")
        print(f"卧底词语: {self.current_theme['minority']}")
    
    def play_round(self):
        """进行一轮游戏"""
        self.round += 1
        print(f"\n====== 第 {self.round} 轮 ======")
        
        round_responses = {}
        
        # 每个玩家描述词语
        for player in self.players_alive:
            word = self.current_theme["minority"] if player == self.undercover else self.current_theme["majority"]
            message = f"你的词语是: {word}。请根据你的词语进行一句话描述，不要直接说出这个词。"
            description = self.send_message_to_agent(player, message)
            
            if description:
                round_responses[player] = description
                print(f"{self.agents[player]['name']} 描述: {description}")
            else:
                round_responses[player] = "无法获取有效回复"
                print(f"{self.agents[player]['name']} 无法获取有效回复")
        
        # 记录本轮历史
        self.game_history.append(round_responses)
        
        # 让每个玩家投票
        votes = self.conduct_voting()
        
        # 处理投票结果
        self.process_votes(votes)
        
        # 检查游戏是否结束
        return self.check_game_over()
    
    def conduct_voting(self):
        """进行投票"""
        votes = {}
        
        # 构建投票信息
        vote_info = "请根据以下描述，投票选出你认为是卧底的玩家(输入对应数字)，但请不要投给自己:\n"
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
                            print(f"{self.agents[player]['name']} 投票给了 {self.agents[voted_player]['name']}")
                            break
                    else:
                        # 如果没找到有效数字，随机投票
                        voted_player = random.choice([p for p in self.players_alive if p != player])
                        votes[player] = voted_player
                        print(f"{self.agents[player]['name']} 投票无效，系统随机分配给了 {self.agents[voted_player]['name']}")
                except Exception as e:
                    # 出错也随机投票
                    print(f"处理投票时出错: {str(e)}")
                    voted_player = random.choice([p for p in self.players_alive if p != player])
                    votes[player] = voted_player
                    print(f"{self.agents[player]['name']} 投票处理出错，系统随机分配给了 {self.agents[voted_player]['name']}")
            else:
                # 响应出错也随机投票
                voted_player = random.choice([p for p in self.players_alive if p != player])
                votes[player] = voted_player
                print(f"{self.agents[player]['name']} 无法获取投票，系统随机分配给了 {self.agents[voted_player]['name']}")
                
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
        print("\n投票结果:")
        for player in self.players_alive:
            print(f"{self.agents[player]['name']}: {vote_count[player]} 票")
        
        # 移除被淘汰的玩家
        self.players_alive.remove(eliminated)
        self.eliminated_players.append(eliminated)
        
        print(f"\n{self.agents[eliminated]['name']} 被淘汰了！")
        if eliminated == self.undercover:
            print("卧底被淘汰了！")
        else:
            print("平民被淘汰了！")
    
    def check_game_over(self):
        """检查游戏是否结束"""
        # 如果卧底已被淘汰，平民获胜
        if self.undercover in self.eliminated_players:
            print("\n游戏结束！平民获胜！")
            return True
        
        # 如果只剩下卧底和一个平民，卧底获胜
        if len(self.players_alive) <= 2 and self.undercover in self.players_alive:
            print("\n游戏结束！卧底获胜！")
            return True
            
        # 游戏继续
        return False
    
    def run_game(self):
        """运行完整游戏"""
        self.initialize_game()
        
        game_over = False
        while not game_over:
            game_over = self.play_round()
            if not game_over:
                time.sleep(2)  # 暂停几秒，便于阅读
        
        # 游戏结束，显示结果
        print("\n====== 游戏结果 ======")
        print(f"卧底是: {self.agents[self.undercover]['name']}")
        print(f"卧底词语: {self.current_theme['minority']}")
        print(f"多数派词语: {self.current_theme['majority']}")
        
        return {
            "undercover": self.agents[self.undercover]['name'],
            "winner": "平民" if self.undercover in self.eliminated_players else "卧底",
            "rounds": self.round,
            "theme": self.current_theme
        }

# 主函数
def main():
    print("谁是卧底游戏启动...")
    game = WhoIsUndercoverGame(AGENTS, GAME_THEMES)
    
    while True:
        result = game.run_game()
        print(f"\n游戏统计: {result['rounds']}轮后，{result['winner']}获胜")
        
        play_again = input("\n是否再玩一局? (y/n): ").lower()
        if play_again != 'y':
            break
    
    print("谢谢参与游戏！")

if __name__ == "__main__":
    main()