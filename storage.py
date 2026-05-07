import json
import os
from models import Track, Playlist

class DataStorage:
    def __init__(self, filename="library.json"):
        self.filename = filename

    def load_data(self):
        if not os.path.exists(self.filename):
            # возвращаем обычную структуру, если нет файла
            return {"playlists": [], "settings": {"last_playlist": "", "volume": 70}}
        
        try:
            with open(self.filename, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return data
        except (json.JSONDecodeError, IOError) as e:
            print(f"Ошибка загрузки БД: {e}")
            return {"playlists": [], "settings": {}}

    def save_data(self, playlists, settings):
        data = {"playlists": [], "settings": settings}
        for pl in playlists:
            pl_data = {
                "name": pl.name,
                "tracks": [
                    {"title": t.title, "artist": t.artist, "duration": t.duration, "path": t.file_path}
                    for t in pl.tracks
                ]
            }
            data["playlists"].append(pl_data)

        try:
            with open(self.filename, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=4)
        except IOError as e:
            print(f"Ошибка сохранения БД: {e}")