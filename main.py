# main.py
import tkinter as tk
from tkinter import messagebox, filedialog, simpledialog
import os
import pygame
from mutagen.mp3 import MP3
from mutagen.wave import WAVE

# импорт наших модулей / den
from models import Track, Playlist, format_time
from engine import PlaybackManager
from storage import DataStorage


class MusicPlayerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Winamp")
        try:
            #проверка на наличие иконки в папке
            self.icon_img = tk.PhotoImage(file='logo.png') 
            self.root.iconphoto(False, self.icon_img)
        except Exception as e:
            print(f"Иконка не найдена: {e}")

        self.storage = DataStorage()
        self.engine = PlaybackManager()
        self.playlists = []
        
        # переменные состояния
        self.is_dragging = False 
        self.start_time_offset = 0
        
        # загрузка данных
        self.init_data()
        
        # создание gui
        self.build_gui()

    def get_selected_queue_index(self):
        selection = self.queue_listbox.curselection()
        if not selection:
            return None

        listbox_index = selection[0]
        if 0 <= listbox_index < len(self.filtered_indices):
            return self.filtered_indices[listbox_index]
        return None


    def remove_track_action(self):
        index = self.get_selected_queue_index()
        if index is None:
            return

        if messagebox.askyesno("Удаление", "Удалить трек из очереди?"):
            # удаляем трек из самого движка
            removed_current = self.engine.remove_track(index)
            if removed_current:
                pygame.mixer.music.stop()
                self.engine.is_paused = False
                self.reset_playback_ui()
            
            # обновляем объекты плейлиста, чтобы подгрузить их в storage / den
            if self.playlists:
                self.playlists[0].tracks = self.engine.current_queue.copy()
            
            # структура для json
            settings = {"last_playlist": "", "volume": int(self.engine.volume_var.get() * 100 if hasattr(self.engine, 'volume_var') else 70)}
            self.storage.save_data(self.playlists, settings)
            
            # обновляем интерфейс
            self.update_queue_ui()
            self.update_info_ui("Остановлено")
        

    def seek_track_action(self, value):
        """Метод для перемотки, когда пользователь двигает ползунок"""
        track = self.engine.get_current_track()
        if track:
            pygame.mixer.music.play(start=float(value))

    def add_track_action(self):
        file_path = filedialog.askopenfilename(
            title="Выберите аудиофайл",
            filetypes=(("Audio Files", "*.mp3 *.wav"), ("All Files", "*.*"))
        )
        
        if file_path:
            # достаем имя файла для подгрузки в плеер / den
            filename = os.path.basename(file_path)
            actual_duration = 0
            
            try:
                # определяем длительность трека с помощью mutagen / den
                if file_path.lower().endswith('.mp3'):
                    audio = MP3(file_path)
                    actual_duration = int(audio.info.length)
                elif file_path.lower().endswith('.wav'):
                    audio = WAVE(file_path)
                    actual_duration = int(audio.info.length)
            except Exception as e:
                print(f"Ошибка чтения метаданных: {e}")
                actual_duration = 0 #если ошибка в подгрузке то оставляем 0 в длительности

            artist = simpledialog.askstring("Артист", "Введите имя артиста:", parent=self.root)
            if artist is None:
                return

            title = simpledialog.askstring("Название", "Введите название песни:", parent=self.root)
            if title is None:
                return

            new_track = Track(
                title=title.strip() or filename,
                artist=artist.strip() or "Неизвестен",
                duration=actual_duration, 
                file_path=file_path
            )
            
            if self.playlists:
                self.playlists[0].add_track(new_track)
                self.engine.load_queue(self.playlists[0].tracks)
                self.update_queue_ui()

    def play_selected_track(self, event=None):
        index = self.get_selected_queue_index()
        if index is None:
            return

        if not (0 <= index < len(self.engine.current_queue)):
            return

        self.engine.current_index = index
        self.reset_playback_ui()
        self.progress_scale.config(to=self.engine.current_queue[index].duration)
        self.engine.play_track()
        self.update_info_ui("Играет")

    def rename_track_action(self): # метод для возможности переименовать трек внутри программы, после ее загрузки / den
        index = self.get_selected_queue_index()
        if index is None:
            return

        track = self.engine.current_queue[index]

        new_artist = simpledialog.askstring("Переименовать", "Новый артист:", initialvalue=track.artist, parent=self.root)
        if new_artist is None:
            return

        new_title = simpledialog.askstring("Переименовать", "Новое название:", initialvalue=track.title, parent=self.root)
        if new_title is None:
            return

        track.artist = new_artist.strip() or track.artist
        track.title = new_title.strip() or track.title
        self.update_queue_ui()
        self.update_info_ui("Обновлено")

    def show_queue_context_menu(self, event):
        if self.queue_listbox.size() == 0:
            return
        self.queue_listbox.selection_clear(0, tk.END)
        self.queue_listbox.selection_set(self.queue_listbox.nearest(event.y))
        self.queue_menu.tk_popup(event.x_root, event.y_root)

    def on_search_change(self, event=None):
        self.update_queue_ui()

    def init_data(self):
        # подгрузка плейлиста из json 
        data = self.storage.load_data()
        
        for pl_data in data.get("playlists", []):
            pl = Playlist(pl_data["name"])
            for t in pl_data["tracks"]:
                pl.add_track(Track(t["title"], t["artist"], t["duration"], t["path"]))
            self.playlists.append(pl)
            
        if not self.playlists:
            # тестовые данные, если плейлист пустой
            pl = Playlist("Избранное")
            pl.add_track(Track("Song Name", "Artist", 210, "C:/music/song.mp3"))
            self.playlists.append(pl)
            
        # загружаем первый плейлист в плеер, сделано для возможности масштабирования проекта 
        self.engine.load_queue(self.playlists[0].tracks)

    def build_gui(self):
        BG_COLOR = "#212121"    # темно-серый
        FG_COLOR = "#FFFFFF"    # белый текст
        ACCENT_COLOR = "#1DB954" # зеленый
        BTN_COLOR = "#333333"   # цвет кнопок

        self.root.configure(bg=BG_COLOR)

        #объявляем переменные
        self.info_var = tk.StringVar(value="Остановлено")
        self.progress_var = tk.DoubleVar(value=0)
        self.volume_var = tk.DoubleVar(value=0.05)
        self.shuffle_var = tk.BooleanVar(value=False)
        self.repeat_var = tk.StringVar(value="None")
        self.search_var = tk.StringVar(value="")
        self.filtered_indices = []

        # задаем параметры для кнопок
        btn_params = {
            "bg": BTN_COLOR, 
            "fg": FG_COLOR, 
            "activebackground": ACCENT_COLOR, 
            "relief": "flat", 
            "font": ("Segoe UI", 10),
            "width": 10
        }

        # информ.панель (название трека)
        tk.Label(
            self.root, 
            textvariable=self.info_var, 
            bg=BG_COLOR, 
            fg=ACCENT_COLOR, 
            font=("Segoe UI", 14, "bold")
        ).pack(pady=15)

        search_frame = tk.Frame(self.root, bg=BG_COLOR)
        search_frame.pack(pady=3, padx=10, fill=tk.X)
        tk.Label(search_frame, text="Поиск:", bg=BG_COLOR, fg=FG_COLOR, font=("Segoe UI", 10)).pack(side=tk.LEFT)
        self.search_entry = tk.Entry(search_frame, textvariable=self.search_var, font=("Segoe UI", 10))
        self.search_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=6)
        self.search_entry.bind("<KeyRelease>", self.on_search_change)

        # список с треками
        self.queue_listbox = tk.Listbox(
            self.root, 
            width=50, 
            height=10,
            bg="#181818", 
            fg=FG_COLOR, 
            borderwidth=0, 
            highlightthickness=1,
            highlightcolor=ACCENT_COLOR,
            selectbackground=ACCENT_COLOR,
            font=("Segoe UI", 10)
        )
        self.queue_listbox.pack(pady=5, padx=10)
        self.queue_listbox.bind("<Double-Button-1>", self.play_selected_track)
        self.queue_listbox.bind("<Button-3>", self.show_queue_context_menu)

        self.queue_menu = tk.Menu(self.root, tearoff=0)
        self.queue_menu.add_command(label="Переименовать", command=self.rename_track_action)
        self.update_queue_ui()

        # блок управления треком
        control_frame = tk.Frame(self.root, bg=BG_COLOR)
        control_frame.pack(pady=5)

        tk.Button(control_frame, text="⏮ Prev", command=self.prev_action, **btn_params).pack(side=tk.LEFT, padx=5)
        tk.Button(control_frame, text="▶ Play", command=self.play_action, **btn_params).pack(side=tk.LEFT, padx=5)
        tk.Button(control_frame, text="⏸ Pause", command=self.pause_action, **btn_params).pack(side=tk.LEFT, padx=5)
        tk.Button(control_frame, text="⏭ Next", command=self.next_action, **btn_params).pack(side=tk.LEFT, padx=5)

        # кнопки работы с файлами
        file_ops_frame = tk.Frame(self.root, bg=BG_COLOR)
        file_ops_frame.pack(pady=5)
        
        tk.Button(file_ops_frame, text="Добавить", command=self.add_track_action, **btn_params).pack(side=tk.LEFT, padx=5)
        # кнопка удаления трека
        del_params = btn_params.copy()
        del_params["fg"] = "#FF4444"
        tk.Button(file_ops_frame, text="Удалить", command=self.remove_track_action, **del_params).pack(side=tk.LEFT, padx=5)

        # блок для перемешки треков и репита
        mode_frame = tk.Frame(self.root, bg=BG_COLOR)
        mode_frame.pack(pady=5)

        tk.Checkbutton(
            mode_frame, text="🔀 Shuffle", variable=self.shuffle_var, 
            command=self.toggle_shuffle, bg=BG_COLOR, fg=FG_COLOR, 
            selectcolor=BTN_COLOR, activebackground=BG_COLOR
        ).pack(side=tk.LEFT, padx=5)

        for text, mode in [("None", "None"), ("All", "Playlist"), ("One", "Track")]:
            tk.Radiobutton(
                mode_frame, text=text, variable=self.repeat_var, value=mode,
                command=self.toggle_repeat,
                bg=BG_COLOR, fg=FG_COLOR, selectcolor=ACCENT_COLOR, activebackground=BG_COLOR
            ).pack(side=tk.LEFT, padx=2)

        # ползунок
        slider_frame = tk.Frame(self.root, bg=BG_COLOR)
        slider_frame.pack(pady=10, fill=tk.X, padx=20)

        self.time_label = tk.Label(slider_frame, text="00:00 / 00:00", bg=BG_COLOR, fg=FG_COLOR, font=("Consolas", 10))
        self.time_label.pack()

        self.progress_scale = tk.Scale(
            slider_frame, 
            variable=self.progress_var, 
            from_=0, to=100, 
            orient=tk.HORIZONTAL,
            
            #приблизительное оформление как в винампе

            bg=BG_COLOR,              # фон
            troughcolor="#111111",    # дорожка
            activebackground=ACCENT_COLOR, # при нажатии цвет
            
            width=10,                 # толщина 
            sliderlength=25,          # длина кирпичика (переключателя)
            
            relief="flat",            # плоские края
            borderwidth=0,            # рамок нет
            highlightthickness=0,     # убирает фокус с ползунка
            showvalue=False           # убирает цифры под ползунком
        )
        self.progress_scale.bind("<ButtonPress-1>", self.on_slider_press)
        self.progress_scale.bind("<B1-Motion>", self.on_slider_motion)
        self.progress_scale.bind("<ButtonRelease-1>", self.on_slider_release)
        self.progress_scale.pack(fill=tk.X)

        # громкость
        volume_frame = tk.Frame(self.root, bg=BG_COLOR)
        volume_frame.pack(pady=5)

        tk.Label(volume_frame, text="🔊", bg=BG_COLOR, fg=FG_COLOR).pack(side=tk.LEFT)
        self.volume_scale = tk.Scale(
            volume_frame, from_=0, to=1, resolution=0.05,
            orient=tk.HORIZONTAL, variable=self.volume_var,
            showvalue=False, command=self.change_volume,
            bg=BG_COLOR, fg=FG_COLOR, highlightthickness=0,
            troughcolor=BTN_COLOR, activebackground=ACCENT_COLOR, sliderrelief="flat"
        )
        self.volume_scale.pack(side=tk.LEFT, padx=5)

        # запуск движка
        pygame.mixer.music.set_volume(self.volume_var.get())
        self.update_slider()

    def change_volume(self, val):
        """Метод слайдера громкости"""
        volume = float(val)
        pygame.mixer.music.set_volume(volume)
        # устанавливает громкость, очевидно)

    def update_slider(self):
        track = self.engine.get_current_track()
        
        # если трека нет, перезапускаем слайдер
        if not track or track.duration <= 0:
            self.root.after(500, self.update_slider)
            return

        # синхронизация ползунка с его длительностью
        if float(self.progress_scale['to']) != float(track.duration):
            self.progress_scale.config(to=track.duration)

        # получаем позицию от pygame
        current_ms = pygame.mixer.music.get_pos()
        
        if current_ms != -1 and not self.is_dragging:
            # считаем текущую секунду + прогресс
            current_sec = self.start_time_offset + (current_ms / 1000)
            
            # обновляем ползунок и таймер
            self.progress_var.set(current_sec)
            self.time_label.config(text=f"{format_time(current_sec)} / {format_time(track.duration)}")

            # проверка автовоспроизведения
            if track.duration - current_sec < 1.0:
                self.next_action()
                return

        # перезапускаем цикл
        self.root.after(500, self.update_slider)


    def update_queue_ui(self):
        self.queue_listbox.delete(0, tk.END)
        self.filtered_indices = []
        query = self.search_var.get().strip().lower() if hasattr(self, 'search_var') else ""

        for idx, track in enumerate(self.engine.current_queue):
            # вытаскиваем данные из трека для наименования
            artist = getattr(track, 'artist', 'Unknown')
            title = getattr(track, 'title', 'Unknown')

            if query and query not in artist.lower() and query not in title.lower():
                continue
            
            # оформление трека на автомате
            if artist != 'Unknown' or title != 'Unknown':
                display_text = f"{artist} — {title}"
            else:
                #если нет данных - оставляем путь
                import os
                path = getattr(track, 'path', str(track))
                display_text = os.path.basename(path)

            self.queue_listbox.insert(tk.END, display_text)
            self.filtered_indices.append(idx)

        current_index = self.engine.current_index
        if current_index in self.filtered_indices:
            visible_index = self.filtered_indices.index(current_index)
            self.queue_listbox.selection_clear(0, tk.END)
            self.queue_listbox.selection_set(visible_index)
            self.queue_listbox.activate(visible_index)
            self.queue_listbox.see(visible_index)

    def update_info_ui(self, status="Играет"):
        # переключение статуса проигрывания
        track = self.engine.get_current_track()
        if track:
            self.info_var.set(f"{status}: {track.artist} - {track.title}")
        else:
            self.info_var.set("Остановлено. Конец очереди.")

    def play_action(self):
        track = self.engine.get_current_track()
        if track:
            # продолжение трека на паузе
            if self.engine.is_paused:
                self.engine.pause_track() #снимает с паузы трек
            else:
                self.reset_playback_ui()
                self.engine.play_track()
            self.update_info_ui("Играет")
            self.update_queue_ui()

    def pause_action(self):
        if self.engine.get_current_track():
            self.engine.pause_track() # поставит на паузу трек или снимает с паузы
            status = "Пауза" if self.engine.is_paused else "Играет"
            self.update_info_ui(status)

    def next_action(self, fade_ms=0):
        if fade_ms > 0:
            pygame.mixer.music.fadeout(fade_ms)
            self.root.after(fade_ms, lambda: self.next_action(fade_ms=0))
            return

        # сбрасываем ползунок на 0
        self.progress_var.set(0)
        self.start_time_offset = 0

        repeat_mode = self.repeat_var.get()
        self.engine.set_repeat(repeat_mode)

        if repeat_mode == "Track":
            # если повторение трека - не меняем трек
            track = self.engine.get_current_track()
        else:
            # иначе - меняем трек
            pygame.mixer.music.stop()
            track = self.engine.next_track()

        if track:
            # обновляем масштаб, если трек изменился
            self.progress_scale.config(to=track.duration)
            self.engine.play_track()
            self.update_info_ui("Играет")
            self.update_queue_ui()
        else:
            self.info_var.set("Конец плейлиста")
            

    def prev_action(self):
        self.reset_playback_ui() #сначала чистим интерфейс
        track = self.engine.prev_track()
        if track:
            self.engine.play_track()
            self.progress_scale.config(to=track.duration)
            self.update_info_ui("Играет")
            self.update_queue_ui()

    def toggle_shuffle(self):
        # перемешать или вернуть обратно
        if self.shuffle_var.get():
            self.engine.shuffle_queue()
        else:
            # возвращаем обратный порядок
            if self.playlists:
                self.engine.load_queue(self.playlists[0].tracks)
        
        # сбрасываем время, чтобы оно не приклеилось к новому значению
        self.start_time_offset = 0
        pygame.mixer.music.stop() # останавливаем старый поток
        
        # обновляем интерфейс и синхронизируем с движком
        self.update_queue_ui()
        self.update_info_ui("Список перемешан")

    def toggle_repeat(self):
        self.engine.set_repeat(self.repeat_var.get())
    
    def on_slider_press(self, event):
        self.is_dragging = True

    def on_slider_motion(self, event):
        track = self.engine.get_current_track()
        if track:
            current_val = self.progress_scale.get()
            current_str = format_time(current_val)
            total_str = format_time(track.duration)
            self.time_label.config(text=f"{current_str} / {total_str}")

    def on_slider_release(self, event):
        new_pos = self.progress_scale.get()
        self.start_time_offset = new_pos # запоминаем куда перемотали трек
        pygame.mixer.music.play(start=float(new_pos))
        self.is_dragging = False

    def reset_playback_ui(self):
        """Полный сброс всех переменных времени перед новым треком"""
        self.start_time_offset = 0
        self.progress_var.set(0)
        # сброс текста
        self.time_label.config(text="00:00 / 00:00")

    def smooth_next(self, fade_ms=1500):
        """Плавно гасит звук и переключает на следующий трек""" # den
        # затухание звука
        pygame.mixer.music.fadeout(fade_ms)
        
        # сначала затухание, потом следующий трек
        self.root.after(fade_ms, self.next_action)

    def update_slider(self):
        track = self.engine.get_current_track()
        
        # проверяем масштаб, если есть слеюущий трек
        if track and track.duration > 0:
            if float(self.progress_scale['to']) != float(track.duration):
                self.progress_scale.config(to=track.duration)

            # если играет музыка
            if pygame.mixer.music.get_busy() and not self.is_dragging:
                current_ms = pygame.mixer.music.get_pos()
                
                if current_ms != -1:
                    current_sec = self.start_time_offset + (current_ms / 1000)
                    current_sec = min(current_sec, track.duration)
                    
                    # обновляем ползунок и цифры
                    self.progress_var.set(current_sec)
                    self.time_label.config(text=f"{format_time(current_sec)} / {format_time(track.duration)}")

                    # затухание за 2 сек до конца трека / den
                    if track.duration - current_sec < 2.0:
                        self.next_action(fade_ms=1500)
                        self.root.after(2000, self.update_slider)
                        return

        # цикл не прерывается
        self.root.after(500, self.update_slider)
if __name__ == "__main__":
    root = tk.Tk()
    app = MusicPlayerApp(root)
    
    # сохранение
    def on_closing():
        app.storage.save_data(app.playlists, {"last_playlist": "Избранное", "volume": 70})
        root.destroy()
        
    root.protocol("WM_DELETE_WINDOW", on_closing)
    root.mainloop()