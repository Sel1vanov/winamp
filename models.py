def format_time(seconds):
    """Вспомогательная функция для перевода секунд в ММ:СС"""
    minutes = int(seconds // 60)
    seconds = int(seconds % 60)
    return f"{minutes:02d}:{seconds:02d}"

class Track:
    def __str__(self):
        # Возвращаем заголовок или имя файла
        return self.title
    
    def __init__(self, title, artist, duration, file_path):
        self.title = title # [cite: 20]
        self.artist = artist # [cite: 20]
        self.duration = duration # [cite: 20]
        self.file_path = file_path # [cite: 20]

    def get_info(self):
        # Вместо "(120 сек.)" будет "(02:00)"
        return f"{self.artist} - {self.title} ({format_time(self.duration)})"

class Playlist:
    def __init__(self, name):
        self.name = name # [cite: 21]
        self.tracks = [] # [cite: 21]

    def add_track(self, track):
        self.tracks.append(track) # [cite: 21]

    def remove_track(self, track):
        if track in self.tracks:
            self.tracks.remove(track) # [cite: 21]

    def get_total_duration(self):
        return sum(track.duration for track in self.tracks) # [cite: 21]