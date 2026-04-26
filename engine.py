import random
import pygame

class PlaybackManager:
    def __init__(self):
        pygame.mixer.init()  # Инициализация звукового движка
        self.current_queue = []
        self.original_queue = []
        self.current_index = -1
        self.is_shuffle = False
        self.repeat_mode = "None"
        self.is_paused = False

    def play_track(self):
        track = self.get_current_track()
        if track:
            try:
                pygame.mixer.music.load(track.file_path) # Загрузка файла
                pygame.mixer.music.play() # Запуск звука
                self.is_paused = False
            except Exception as e:
                print(f"Ошибка воспроизведения: {e}")

    def pause_track(self):
        if not self.is_paused:
            pygame.mixer.music.pause()
            self.is_paused = True
        else:
            pygame.mixer.music.unpause()
            self.is_paused = False

    def stop_track(self):
        pygame.mixer.music.stop()


    def load_queue(self, tracks):
        self.original_queue = tracks.copy()
        self.current_queue = tracks.copy()
        self.current_index = 0 if tracks else -1
        if self.is_shuffle:
            self.shuffle_queue()

    def shuffle_queue(self):
        # Изменение порядка на случайный 
        self.is_shuffle = not self.is_shuffle
        if self.is_shuffle:
            random.shuffle(self.current_queue)
        else:
            self.current_queue = self.original_queue.copy()

    def set_repeat(self, mode):
        # Зацикливание одного трека или всего плейлиста [cite: 13]
        self.repeat_mode = mode 

    def next_track(self):
        if not self.current_queue:
            return None
            
        if self.repeat_mode == "Track":
            return self.current_queue[self.current_index]

        self.current_index += 1
        if self.current_index >= len(self.current_queue):
            if self.repeat_mode == "Playlist":
                self.current_index = 0
            else:
                self.current_index = -1
                return None
        return self.current_queue[self.current_index]
        
    def prev_track(self):
        if not self.current_queue or self.current_index <= 0:
            return None
        if self.repeat_mode == "Track":
            return self.current_queue[self.current_index]
        self.current_index -= 1
        return self.current_queue[self.current_index]

    def get_current_track(self):
        if 0 <= self.current_index < len(self.current_queue):
            return self.current_queue[self.current_index]
        return None
    
