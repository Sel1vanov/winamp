# engine.py
import random
import pygame
import os

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
                # Останавливаем предыдущий поток перед загрузкой нового файла
                pygame.mixer.music.stop()
                pygame.mixer.music.load(track.file_path) # Загрузка файла
                pygame.mixer.music.play() # Запуск звука
                self.is_paused = False
            except Exception as e:
                # Детальный лог для диагностики сбоев вроде "Out of memory"
                file_exists = os.path.exists(track.file_path)
                file_size = os.path.getsize(track.file_path) if file_exists else "N/A"
                print(
                    "Ошибка воспроизведения:",
                    f"{e}; file='{track.file_path}'; exists={file_exists}; size={file_size}; pygame='{pygame.get_error()}'"
                )

                # Fallback: иногда backend аудио падает и помогает переинициализация mixer
                try:
                    pygame.mixer.quit()
                    pygame.mixer.init()
                    pygame.mixer.music.load(track.file_path)
                    pygame.mixer.music.play()
                    self.is_paused = False
                except Exception as retry_error:
                    print(f"Повторный запуск после re-init не удался: {retry_error}")

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
        # Зацикливание одного трека или всего плейлиста 
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
    
    def remove_track(self, index):
        if 0 <= index < len(self.current_queue):
            removed_current = (index == self.current_index)
            self.current_queue.pop(index)
            if index < len(self.original_queue):
                self.original_queue.pop(index)
            if not self.current_queue:
                self.current_index = -1
            elif index < self.current_index:
                self.current_index -= 1
            elif index >= len(self.current_queue):
                self.current_index = len(self.current_queue) - 1
            return removed_current
        return False

    def save_library(self):
        import json
        data = []
        for track in self.current_queue:
            data.append({
                "title": track.title,
                "artist": track.artist,
                "duration": track.duration,
                "file_path": track.file_path  # Именно file_path, как в твоем __init__
            })
        
        with open("library.json", "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4, ensure_ascii=False)