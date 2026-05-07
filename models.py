def format_time(seconds):
    """вспомогательная функция для перевода секунд минуты + секунды"""
    minutes = int(seconds // 60)
    seconds = int(seconds % 60)
    return f"{minutes:02d}:{seconds:02d}"

class Track:
    def __str__(self):
        # возвращаем заголовок или имя файла
        return self.title
    
    def __init__(self, title, artist, duration, file_path):
        self.title = title 
        self.artist = artist 
        self.duration = duration 
        self.file_path = file_path 

    def get_info(self):
        # задаем формат времени
        return f"{self.artist} - {self.title} ({format_time(self.duration)})"

class Playlist:
    def __init__(self, name):
        self.name = name 
        self.tracks = [] 

    def add_track(self, track):
        self.tracks.append(track) 

    def remove_track(self, track):
        if track in self.tracks:
            self.tracks.remove(track) 

    def get_total_duration(self):
        return sum(track.duration for track in self.tracks) 