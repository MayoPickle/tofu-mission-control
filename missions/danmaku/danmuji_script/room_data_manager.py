# room_data_manager.py

import os
import json
import inquirer

class RoomDataManager:
    def __init__(self, filename="room_ids.json"):
        self.filename = filename

    def save_room_data(self, room_data):
        with open(self.filename, "w", encoding="utf-8") as file:
            json.dump(room_data, file, indent=4)

    def load_room_data(self):
        if not os.path.exists(self.filename):
            return []
        with open(self.filename, "r", encoding="utf-8") as file:
            return json.load(file)

    def get_user_choice(self, room_data):
        """
        在终端中询问用户选择已有的房间信息，或输入新的Room ID和备注。
        返回一个整数类型的room_id。
        """
        choices = [f"{item['room_id']} ({item['remark']})" for item in room_data] + ["Enter a new room ID with remark"]
        questions = [inquirer.List('choice', message="Choose a room ID or add new one with remark", choices=choices)]
        answer = inquirer.prompt(questions)
        selected = answer['choice']
        
        if selected == "Enter a new room ID with remark":
            while True:
                room_id_str = input("Enter new room ID: ")
                if room_id_str.isdigit():
                    room_id = int(room_id_str)
                    remark = input("Enter remark for this room ID: ")
                    room_data.append({"room_id": room_id, "remark": remark})
                    self.save_room_data(room_data)
                    return room_id
                else:
                    print("Error: Room ID must be a number.")
        else:
            return int(selected.split(" ")[0])
