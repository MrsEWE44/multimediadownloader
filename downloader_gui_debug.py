import os
import re
import sys
import shutil
import subprocess
import yt_dlp
import requests
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLineEdit, QPushButton, QLabel, QFileDialog, QTextEdit, QProgressBar,
    QMessageBox, QFrame, QSizePolicy, QTabWidget, QCheckBox, QComboBox,
    QSpinBox, QTableWidget, QTableWidgetItem, QHeaderView, QMenu, QStyle,
    QStyleOptionSpinBox,
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QUrl, QSize, QRect, QPoint, QThreadPool, QRunnable, QObject
from PyQt6.QtGui import QFont, QCursor, QDesktopServices, QPixmap, QColor, QPainter, QAction

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DEFAULT_SAVE_DIR = os.path.join(BASE_DIR, 'abc')

try:
    from musicdl import musicdl
    MUSICDL_AVAILABLE = True
except ImportError:
    musicdl = None
    MUSICDL_AVAILABLE = False

os.environ['PYTHONIOENCODING'] = 'utf-8'
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
sys.stderr.reconfigure(encoding='utf-8', errors='replace')

GLOBAL_STYLE = """
QMainWindow { background-color: #f5f5f5; }
QTabWidget::pane { border: 1px solid #d1d5db; background: #f5f5f5; }
QTabBar::tab { background: #e5e7eb; color: #374151; padding: 10px 24px;
    margin-right: 2px; border-top-left-radius: 6px; border-top-right-radius: 6px;
    font-size: 13pt; font-weight: bold; }
QTabBar::tab:selected { background: #2196F3; color: white; }
QTabBar::tab:hover { background: #bfdbfe; }
QLineEdit { border: 1px solid #d1d5db; border-radius: 6px; padding: 6px 10px;
    background: #ffffff; color: #1f2937; font-size: 13pt; }
QLineEdit:focus { border: 1px solid #2196F3; }
QPushButton { border: none; border-radius: 6px; padding: 8px 18px;
    background-color: #2196F3; color: white; font-weight: bold; font-size: 12pt; }
QPushButton:hover { background-color: #1976D2; }
QPushButton:pressed { background-color: #1565C0; }
QPushButton:disabled { background-color: #9ca3af; color: #f3f4f6; }
QProgressBar { border: none; border-radius: 4px; background-color: #e5e7eb; height: 22px; text-align: center;
    font-size: 11pt; color: #374151; }
QProgressBar::chunk { background-color: #2196F3; border-radius: 4px; }
QTextEdit { border: 1px solid #d1d5db; border-radius: 6px; background-color: #1e1e1e; color: #d4d4d4; }
QLabel { color: #374151; }
QCheckBox { color: #4b5563; font-size: 12pt; }
QCheckBox:hover { color: #2196F3; }
QComboBox { border: 1px solid #d1d5db; border-radius: 6px; padding: 6px 10px;
    background: #ffffff; color: #1f2937; font-size: 12pt; min-height: 24px; }
QComboBox:focus { border: 1px solid #2196F3; }
QComboBox QAbstractItemView { border: 1px solid #d1d5db; background-color: #ffffff;
    selection-background-color: #e0f2fe; selection-color: #0369a1; }
QSpinBox { border: 1px solid #d1d5db; border-radius: 6px; padding: 6px 10px;
    background: #ffffff; color: #1f2937; font-size: 12pt; }
QTableWidget { border: 1px solid #e5e7eb; border-radius: 8px; background: #ffffff;
    alternate-background-color: #f9fafb; color: #374151; selection-background-color: #e0f2fe;
    selection-color: #0369a1; font-size: 12pt; }
QHeaderView::section { background: #f3f4f6; color: #4b5563; font-weight: bold; border: none;
    border-bottom: 1px solid #e5e7eb; border-right: 1px solid #e5e7eb; padding: 6px 8px; }
QScrollBar:vertical { border: none; background: #f3f4f6; width: 8px; border-radius: 4px; }
QScrollBar::handle:vertical { background: #d1d5db; min-height: 20px; border-radius: 4px; }
QScrollBar::handle:vertical:hover { background: #9ca3af; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0px; }
"""


def check_node_installed():
    return shutil.which('node') is not None


def is_douyin_url(url):
    return bool(re.search(r'(douyin|tiktok)', url, re.IGNORECASE))


def sanitize_filename(filename):
    return re.sub(r'[\\/*?:"<>|]', "_", str(filename))


def extract_numeric_value(text):
    text = str(text).strip()
    if not text:
        return 0
    try:
        return float(text)
    except ValueError:
        pass
    if ":" in text:
        parts = text.split(":")
        try:
            if len(parts) == 2:
                return int(parts[0]) * 60 + float(parts[1])
        except ValueError:
            pass
    m = re.match(r"([\d.]+)", text)
    return float(m.group(1)) if m else 0


class NumericTableItem(QTableWidgetItem):
    def __lt__(self, other):
        if isinstance(other, QTableWidgetItem):
            my_val = self.data(Qt.ItemDataRole.UserRole)
            other_val = other.data(Qt.ItemDataRole.UserRole)
            if my_val is not None and other_val is not None:
                try:
                    return float(my_val) < float(other_val)
                except (ValueError, TypeError):
                    pass
        return super().__lt__(other)


class ImageWorkerSignals(QObject):
    finished = pyqtSignal(int, QPixmap)
    error = pyqtSignal(int)


class ImageDownloadTask(QRunnable):
    def __init__(self, row, image_url):
        super().__init__()
        self.row = row
        self.image_url = image_url
        self.signals = ImageWorkerSignals()

    def run(self):
        try:
            if not self.image_url:
                self.signals.error.emit(self.row)
                return
            response = requests.get(self.image_url, timeout=5)
            if response.status_code == 200:
                pixmap = QPixmap()
                pixmap.loadFromData(response.content)
                scaled = pixmap.scaled(44, 44, Qt.AspectRatioMode.KeepAspectRatio,
                                       Qt.TransformationMode.SmoothTransformation)
                self.signals.finished.emit(self.row, scaled)
            else:
                self.signals.error.emit(self.row)
        except Exception:
            self.signals.error.emit(self.row)


# ==================== Music Tab ====================
class MusicSearchThread(QThread):
    finished = pyqtSignal(dict)
    error = pyqtSignal(str)

    def __init__(self, music_client, keyword, search_type):
        super().__init__()
        self.music_client = music_client
        self.keyword = keyword
        self.search_type = search_type

    def run(self):
        try:
            if self.search_type == "搜索歌曲":
                results = self.music_client.search(keyword=self.keyword)
            else:
                results = self.music_client.parseplaylist(self.keyword)
                if not isinstance(results, dict):
                    results = {"歌单": results}
            self.finished.emit(results)
        except Exception as e:
            self.error.emit(str(e))


class MusicDownloadThread(QThread):
    finished = pyqtSignal(int)
    error = pyqtSignal(str)

    def __init__(self, music_client, song_infos, target_dir):
        super().__init__()
        self.music_client = music_client
        self.song_infos = song_infos
        self.target_dir = target_dir

    def _get_val(self, obj, key, default=""):
        if isinstance(obj, dict):
            return obj.get(key, default)
        return getattr(obj, key, default) if hasattr(obj, key) else default

    def run(self):
        try:
            downloaded_songs = self.music_client.download(song_infos=self.song_infos)
            success_count = 0
            for song in downloaded_songs:
                save_path = self._get_val(song, "save_path")
                if not save_path or not os.path.exists(save_path):
                    continue
                song_name = self._get_val(song, "song_name", "未知歌曲")
                singers = self._get_val(song, "singers", "未知歌手")
                if isinstance(singers, list):
                    singer = "&".join([str(s) for s in singers])
                else:
                    singer = str(singers)
                album = self._get_val(song, "album", "")
                identifier = self._get_val(song, "identifier", "")
                ext = os.path.splitext(save_path)[1].lstrip(".")
                if not ext:
                    ext = self._get_val(song, "ext", "mp3")
                parts = [song_name, singer]
                if album:
                    parts.append(str(album))
                if identifier:
                    parts.append(str(identifier))
                base_name = sanitize_filename("-".join(parts))
                new_audio_path = os.path.join(self.target_dir, f"{base_name}.{ext}")
                try:
                    if os.path.exists(new_audio_path):
                        os.remove(new_audio_path)
                    shutil.move(save_path, new_audio_path)
                    success_count += 1
                except Exception:
                    pass
                old_lrc_path = os.path.splitext(save_path)[0] + ".lrc"
                if os.path.exists(old_lrc_path):
                    new_lrc_path = os.path.join(self.target_dir, f"{base_name}.lrc")
                    try:
                        if os.path.exists(new_lrc_path):
                            os.remove(new_lrc_path)
                        shutil.move(old_lrc_path, new_lrc_path)
                    except Exception:
                        pass
            self.finished.emit(success_count)
        except Exception as e:
            self.error.emit(str(e))


class MusicTab(QWidget):
    def __init__(self):
        super().__init__()
        self.source_map_cn_to_en = {
            "酷我音乐": "KuwoMusicClient", "酷狗音乐": "KugouMusicClient",
            "网易云音乐": "NeteaseMusicClient", "QQ音乐": "QQMusicClient",
            "咪咕音乐": "MiguMusicClient", "千千音乐": "QianqianMusicClient",
            "5sing": "FiveSingMusicClient", "汽水音乐": "SodaMusicClient",
            "SoundCloud": "SoundCloudMusicClient", "Spotify": "SpotifyMusicClient",
            "TIDAL": "TIDALMusicClient", "Qobuz": "QobuzMusicClient",
            "Jamendo": "JamendoMusicClient", "Deezer": "DeezerMusicClient",
            "苹果音乐": "AppleMusicClient", "Joox": "JooxMusicClient",
            "StreetVoice": "StreetVoiceMusicClient",
        }
        self.source_map_en_to_cn = {v: k for k, v in self.source_map_cn_to_en.items()}
        self.search_results = {}
        self.music_records = {}
        self.music_client = None
        self.current_right_click_row = -1
        self.thread_pool = QThreadPool.globalInstance()
        self.thread_pool.setMaxThreadCount(10)
        self.current_dir = os.getcwd()
        self.save_dir = os.path.join(self.current_dir, "已下载音乐")
        os.makedirs(self.save_dir, exist_ok=True)
        self.auto_download_after_search = False
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(16, 16, 16, 16)

        src_label = QLabel("选择音乐源:")
        src_label.setFont(QFont('Microsoft YaHei', 13))
        layout.addWidget(src_label)

        src_frame = QFrame()
        src_frame.setStyleSheet("QFrame { background: #ffffff; border: 1px solid #e5e7eb; border-radius: 8px; padding: 8px; }")
        src_layout = QHBoxLayout(src_frame)
        src_layout.setSpacing(10)
        self.source_checkboxes = []
        default_checked = ["酷我音乐", "酷狗音乐"]
        for cn_name in self.source_map_cn_to_en.keys():
            cb = QCheckBox(cn_name)
            if cn_name in default_checked:
                cb.setChecked(True)
            self.source_checkboxes.append(cb)
            src_layout.addWidget(cb)
        src_layout.addStretch()
        layout.addWidget(src_frame)

        opt_row = QHBoxLayout()
        opt_row.addWidget(QLabel("数量:"))
        self.spin_limit = QSpinBox()
        self.spin_limit.setRange(1, 100)
        self.spin_limit.setValue(10)
        self.spin_limit.setSuffix(" 条")
        self.spin_limit.setFixedWidth(100)
        self.spin_limit.setFont(QFont('Microsoft YaHei', 12))
        opt_row.addWidget(self.spin_limit)
        opt_row.addSpacing(20)
        opt_row.addWidget(QLabel("保存目录:"))
        self.save_dir_edit = QLineEdit(self.save_dir)
        self.save_dir_edit.setReadOnly(True)
        opt_row.addWidget(self.save_dir_edit, 1)
        browse_btn = QPushButton("选择")
        browse_btn.setFixedWidth(80)
        browse_btn.clicked.connect(self._on_browse)
        opt_row.addWidget(browse_btn)
        open_btn = QPushButton("打开")
        open_btn.setFixedSize(80, 36)
        open_btn.setStyleSheet("QPushButton { background-color: #FF9800; } QPushButton:hover { background-color: #F57C00; }")
        open_btn.clicked.connect(self._on_open_dir)
        opt_row.addWidget(open_btn)
        layout.addLayout(opt_row)

        search_row = QHBoxLayout()
        self.search_mode = QComboBox()
        self.search_mode.addItems(["搜索歌曲", "解析歌单链接"])
        self.search_mode.setFixedWidth(140)
        self.search_mode.setFont(QFont('Microsoft YaHei', 12))
        search_row.addWidget(self.search_mode)
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("请输入关键词或歌单链接...")
        self.search_edit.returnPressed.connect(self._on_search)
        search_row.addWidget(self.search_edit)
        self.btn_search = QPushButton("搜索")
        self.btn_search.setFixedWidth(120)
        self.btn_search.setStyleSheet("QPushButton { background-color: #10b981; } QPushButton:hover { background-color: #059669; }")
        self.btn_search.clicked.connect(self._on_search)
        search_row.addWidget(self.btn_search)
        layout.addLayout(search_row)

        dl_row = QHBoxLayout()
        scope_label = QLabel("下载范围:")
        scope_label.setFont(QFont('Microsoft YaHei', 12))
        dl_row.addWidget(scope_label)
        self.combo_scope = QComboBox()
        self.combo_scope.addItems(["勾选", "全选", "未勾选"])
        self.combo_scope.setFixedWidth(100)
        self.combo_scope.setFont(QFont('Microsoft YaHei', 12))
        dl_row.addWidget(self.combo_scope)
        dl_row.addStretch()
        self.btn_download = QPushButton("下载选中")
        self.btn_download.setFixedWidth(120)
        self.btn_download.setEnabled(False)
        self.btn_download.clicked.connect(self._on_download)
        dl_row.addWidget(self.btn_download)
        layout.addLayout(dl_row)

        self.results_table = QTableWidget()
        self.results_table.setColumnCount(9)
        self.results_table.setHorizontalHeaderLabels(
            ["选择", "封面", "歌曲名", "歌手", "专辑", "格式", "大小", "时长", "来源"])
        self.results_table.horizontalHeader().setStretchLastSection(True)
        self.results_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.results_table.verticalHeader().setVisible(False)
        self.results_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.results_table.setAlternatingRowColors(True)
        self.results_table.setShowGrid(False)
        self.results_table.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.results_table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.results_table.customContextMenuRequested.connect(self._show_context_menu)
        self.results_table.setColumnWidth(0, 40)
        self.results_table.setColumnWidth(1, 65)
        self.results_table.setColumnWidth(2, 260)
        self.results_table.setColumnWidth(3, 150)
        self.results_table.setColumnWidth(4, 180)
        self.results_table.setColumnWidth(5, 55)
        self.results_table.setColumnWidth(6, 75)
        self.results_table.setColumnWidth(7, 65)
        self.results_table.verticalHeader().setDefaultSectionSize(54)
        self.results_table.setSortingEnabled(True)
        layout.addWidget(self.results_table)

    def _on_browse(self):
        d = QFileDialog.getExistingDirectory(self, "选择保存目录", self.current_dir)
        if d:
            self.save_dir = d
            self.save_dir_edit.setText(d)

    def _on_open_dir(self):
        path = self.save_dir_edit.text().strip()
        if path and os.path.isdir(path):
            subprocess.Popen(['explorer', os.path.normpath(path)])

    def _get_selected_sources(self):
        return [self.source_map_cn_to_en[cb.text()] for cb in self.source_checkboxes if cb.isChecked()]

    def _init_music_client(self):
        if not MUSICDL_AVAILABLE:
            QMessageBox.warning(self, "提示", "musicdl 库未安装！\n请运行: pip install musicdl")
            return None
        os.makedirs(self.save_dir, exist_ok=True)
        temp_work_dir = os.path.join(self.current_dir, ".musicdl_temp")
        os.makedirs(temp_work_dir, exist_ok=True)
        src_names = self._get_selected_sources()
        if not src_names:
            QMessageBox.warning(self, "提示", "请至少选择一个音乐来源！")
            return None
        cfg = {src: {"search_size_per_source": self.spin_limit.value(), "work_dir": temp_work_dir} for src in src_names}
        try:
            if musicdl:
                return musicdl.MusicClient(music_sources=src_names, init_music_clients_cfg=cfg)
            return None
        except Exception as e:
            QMessageBox.critical(self, "错误", f"初始化失败：{e}")
            return None

    def _get_file_format(self, song_info):
        for field in ["format", "ext", "file_format", "type"]:
            if song_info.get(field):
                return str(song_info[field]).upper()
        return "未知"

    def _get_album_image_url(self, song_info):
        for field in ["cover", "album_cover", "pic", "picture", "img", "image",
                       "album_img", "album_pic", "cover_url", "pic_url"]:
            url = str(song_info.get(field, ""))
            if url.startswith("http"):
                return url
        return ""

    def _show_context_menu(self, pos):
        item = self.results_table.itemAt(pos)
        if not item:
            return
        self.current_right_click_row = item.row()
        menu = QMenu(self)
        song_name_item = self.results_table.item(item.row(), 2)
        singer_item = self.results_table.item(item.row(), 3)
        action_text = f"下载: {song_name_item.text()} - {singer_item.text()}" if (song_name_item and singer_item) else "下载此歌曲"
        download_action = QAction(action_text, self)
        download_action.triggered.connect(self._download_current_row)
        menu.addAction(download_action)
        menu.addSeparator()
        select_all = QAction("全选", self)
        select_all.triggered.connect(self._select_all)
        menu.addAction(select_all)
        deselect_all = QAction("取消全选", self)
        deselect_all.triggered.connect(self._deselect_all)
        menu.addAction(deselect_all)
        menu.exec(self.results_table.mapToGlobal(pos))

    def _download_current_row(self):
        if self.current_right_click_row < 0 or not self.music_client:
            return
        cell_widget = self.results_table.cellWidget(self.current_right_click_row, 0)
        if not cell_widget:
            return
        checkbox = cell_widget.findChild(QCheckBox)
        song_info = getattr(checkbox, "song_info", None) or self.music_records.get(str(self.current_right_click_row))
        if not song_info:
            return
        self._start_download([song_info])

    def _select_all(self):
        for row in range(self.results_table.rowCount()):
            cw = self.results_table.cellWidget(row, 0)
            if cw:
                cb = cw.findChild(QCheckBox)
                if cb:
                    cb.setChecked(True)

    def _deselect_all(self):
        for row in range(self.results_table.rowCount()):
            cw = self.results_table.cellWidget(row, 0)
            if cw:
                cb = cw.findChild(QCheckBox)
                if cb:
                    cb.setChecked(False)

    def _load_results(self, search_results):
        self.results_table.setSortingEnabled(False)
        self.results_table.setRowCount(0)
        self.search_results = search_results
        self.music_records = {}
        self.thread_pool.clear()
        all_songs = []
        for songs in search_results.values():
            all_songs.extend(songs)
        self.results_table.setRowCount(len(all_songs))
        row = 0
        for _, per_source in search_results.items():
            for info in per_source:
                w = QWidget()
                lay = QHBoxLayout(w)
                cb = QCheckBox()
                cb.song_info = info
                lay.addWidget(cb)
                lay.setAlignment(Qt.AlignmentFlag.AlignCenter)
                lay.setContentsMargins(0, 0, 0, 0)
                self.results_table.setCellWidget(row, 0, w)
                columns = [
                    (2, str(info.get("song_name", ""))),
                    (3, str(info.get("singers", ""))),
                    (4, str(info.get("album", ""))),
                    (5, self._get_file_format(info)),
                    (6, str(info.get("file_size", ""))),
                    (7, str(info.get("duration", ""))),
                    (8, str(self.source_map_en_to_cn.get(info.get("source", ""), ""))),
                ]
                for col, text in columns:
                    if col in (6, 7):
                        ti = NumericTableItem(text)
                        ti.setData(Qt.ItemDataRole.UserRole, extract_numeric_value(text))
                    else:
                        ti = QTableWidgetItem(text)
                    align = Qt.AlignmentFlag.AlignLeft if col in [2, 3, 4] else Qt.AlignmentFlag.AlignHCenter
                    ti.setTextAlignment(Qt.AlignmentFlag.AlignVCenter | align)
                    self.results_table.setItem(row, col, ti)
                self.music_records[str(row)] = info
                img_url = self._get_album_image_url(info)
                if img_url:
                    task = ImageDownloadTask(row, img_url)
                    task.signals.finished.connect(self._on_image_ok)
                    task.signals.error.connect(self._on_image_err)
                    self.thread_pool.start(task)
                else:
                    self._on_image_err(row)
                row += 1
        self.btn_download.setEnabled(row > 0)
        self.results_table.setSortingEnabled(True)

    def _on_image_ok(self, row, pixmap):
        label = QLabel()
        label.setPixmap(pixmap)
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.results_table.setCellWidget(row, 1, label)

    def _on_image_err(self, row):
        label = QLabel("♪")
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        label.setStyleSheet("font-size: 20px; color: #d1d5db;")
        self.results_table.setCellWidget(row, 1, label)

    def _get_songs_by_scope(self):
        scope = self.combo_scope.currentText()
        songs = []
        for row in range(self.results_table.rowCount()):
            cw = self.results_table.cellWidget(row, 0)
            if not cw:
                continue
            cb = cw.findChild(QCheckBox)
            checked = cb.isChecked() if cb else False
            if scope == "全选" or (scope == "勾选" and checked) or (scope == "未勾选" and not checked):
                info = getattr(cb, "song_info", None)
                if not info and str(row) in self.music_records:
                    info = self.music_records[str(row)]
                if info:
                    songs.append(info)
        return songs

    def _start_download(self, songs_list):
        self.download_thread = MusicDownloadThread(self.music_client, songs_list, self.save_dir)
        def on_finished(count):
            QMessageBox.information(self, "完成", f"成功下载 {count} 首歌曲！\n保存在: {self.save_dir}")
        def on_error(msg):
            QMessageBox.critical(self, "错误", f"下载失败: {msg}")
        self.download_thread.finished.connect(on_finished)
        self.download_thread.error.connect(on_error)
        self.download_thread.start()

    def _on_search(self):
        keyword = self.search_edit.text().strip()
        if not keyword:
            QMessageBox.warning(self, "提示", "请输入搜索关键词！")
            return
        self.music_client = self._init_music_client()
        if not self.music_client:
            return
        self.btn_search.setEnabled(False)
        self.btn_search.setText("搜索中...")
        self.search_thread = MusicSearchThread(self.music_client, keyword, self.search_mode.currentText())
        def on_finished(results):
            self.btn_search.setEnabled(True)
            self.btn_search.setText("搜索")
            self._load_results(results)
        def on_error(msg):
            self.btn_search.setEnabled(True)
            self.btn_search.setText("搜索")
            QMessageBox.critical(self, "错误", f"搜索失败: {msg}")
        self.search_thread.finished.connect(on_finished)
        self.search_thread.error.connect(on_error)
        self.search_thread.start()

    def _on_download(self):
        if not self.music_client:
            return
        songs = self._get_songs_by_scope()
        if not songs:
            QMessageBox.warning(self, "提示", "没有选中的歌曲！")
            return
        self._start_download(songs)


# ==================== Video Tab ====================
NODE_HELP_TEXT = """
下载 YouTube 视频需要安装 Node.js。

YouTube 视频使用了 JS 加密保护，需要 Node.js 来解密。

请安装 Node.js >= 22:
  官网: https://nodejs.org/
  国内镜像: https://npmmirror.com/mirrors/node/

安装步骤:
  1. 打开上方链接，下载 LTS 版本
  2. 双击安装，一路下一步
  3. 安装时勾选 "Add to PATH"
  4. 安装完成后重启本程序
"""

COOKIE_HELP_TEXT = """
【如何获取 Cookie 文件】

1. 在 Chrome 浏览器安装扩展: Get cookies.txt LOCALLY
2. 打开目标网站并登录
3. 点击浏览器工具栏的扩展图标
4. 点击 "Export" 保存为 .txt 文件
5. 将文件路径填入 Cookie 输入框

注意:
- 不同网站需分别获取
- Cookie 可能过期需重新获取
- 抖音必须提供 Cookie
"""


class VideoDownloadWorker(QThread):
    progress_update = pyqtSignal(str)
    progress_bar_update = pyqtSignal(int, int, str)
    download_done = pyqtSignal(str, bool, str)

    def __init__(self, url, save_dir, cookie_file=None, proxy=None):
        super().__init__()
        self.url = url
        self.save_dir = save_dir
        self.cookie_file = cookie_file
        self.proxy = proxy

    def run(self):
        try:
            base_opts = {'quiet': True, 'noprogress': True, 'js_runtimes': {'node': {}}}
            if self.cookie_file and os.path.exists(self.cookie_file):
                base_opts['cookiefile'] = self.cookie_file
            if self.proxy:
                base_opts['proxy'] = self.proxy

            self.progress_update.emit('正在解析链接...')
            with yt_dlp.YoutubeDL(base_opts) as ydl:
                info = ydl.extract_info(self.url, download=False)
            platform = info.get('extractor', 'unknown')
            self.progress_update.emit(f'平台: {platform}')

            download_dir = os.path.join(self.save_dir, platform)
            os.makedirs(download_dir, exist_ok=True)

            def progress_hook(d):
                if d['status'] == 'downloading':
                    total = d.get('total_bytes') or d.get('total_bytes_estimate') or 0
                    downloaded = d.get('downloaded_bytes') or 0
                    speed = d.get('speed')
                    eta = d.get('eta')
                    speed_str = f'{speed / 1024 / 1024:.1f} MB/s' if speed else '未知'
                    eta_str = f'{eta}s' if eta else '未知'
                    self.progress_bar_update.emit(downloaded, total, f'{speed_str} | ETA: {eta_str}')
                    self.progress_update.emit(f'下载中... {speed_str} | 剩余: {eta_str}')
                elif d['status'] == 'finished':
                    self.progress_update.emit('下载完成，处理中...')

            ydl_opts = {
                'outtmpl': os.path.join(download_dir, '%(title)s.%(ext)s'),
                'ignoreerrors': True, 'quiet': True, 'noprogress': True,
                'js_runtimes': {'node': {}},
                'format': 'bestvideo+bestaudio/best',
                'progress_hooks': [progress_hook],
            }
            if self.cookie_file and os.path.exists(self.cookie_file):
                ydl_opts['cookiefile'] = self.cookie_file
            if self.proxy:
                ydl_opts['proxy'] = self.proxy

            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([self.url])

            files = os.listdir(download_dir)
            if files:
                latest = max([os.path.join(download_dir, f) for f in files], key=os.path.getctime)
                size_mb = os.path.getsize(latest) / (1024 * 1024)
                self.download_done.emit(f'{os.path.basename(latest)} ({size_mb:.2f} MB)', True, platform)
            else:
                self.download_done.emit('下载完成', True, platform)
        except Exception as e:
            error_msg = str(e)
            if 'ffmpeg' in error_msg.lower():
                error_msg = '需要安装 ffmpeg 才能合并音视频'
            self.download_done.emit(error_msg, False, '')


class HelpWindow(QMainWindow):
    def __init__(self, title, text):
        super().__init__()
        self.setWindowTitle(title)
        self.setFixedSize(600, 480)
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        te = QTextEdit()
        te.setReadOnly(True)
        te.setPlainText(text.strip())
        te.setFont(QFont('Microsoft YaHei', 13))
        layout.addWidget(te)

        link_layout = QHBoxLayout()
        official_btn = QPushButton('打开 Node.js 官网')
        official_btn.setFixedHeight(42)
        official_btn.setFont(QFont('Microsoft YaHei', 12))
        official_btn.clicked.connect(lambda: QDesktopServices.openUrl(QUrl('https://nodejs.org/')))
        link_layout.addWidget(official_btn)
        mirror_btn = QPushButton('打开国内镜像')
        mirror_btn.setFixedHeight(42)
        mirror_btn.setFont(QFont('Microsoft YaHei', 12))
        mirror_btn.clicked.connect(lambda: QDesktopServices.openUrl(QUrl('https://npmmirror.com/mirrors/node/')))
        link_layout.addWidget(mirror_btn)
        layout.addLayout(link_layout)

        btn = QPushButton('我知道了')
        btn.setFixedHeight(42)
        btn.setFont(QFont('Microsoft YaHei', 13))
        btn.clicked.connect(self.close)
        layout.addWidget(btn)


class VideoTab(QWidget):
    def __init__(self):
        super().__init__()
        self.worker = None
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(16, 16, 16, 16)

        url_label = QLabel('视频地址:')
        url_label.setFont(QFont('Microsoft YaHei', 14))
        layout.addWidget(url_label)
        self.url_input = QLineEdit()
        self.url_input.setPlaceholderText('输入视频链接（支持 B站、抖音、小红书、YouTube 等）')
        self.url_input.setFont(QFont('Microsoft YaHei', 14))
        self.url_input.setFixedHeight(42)
        layout.addWidget(self.url_input)

        save_label = QLabel('保存路径:')
        save_label.setFont(QFont('Microsoft YaHei', 14))
        layout.addWidget(save_label)
        save_row = QHBoxLayout()
        self.save_input = QLineEdit()
        self.save_input.setText(DEFAULT_SAVE_DIR)
        self.save_input.setFont(QFont('Microsoft YaHei', 14))
        self.save_input.setFixedHeight(42)
        save_row.addWidget(self.save_input)
        save_btn = QPushButton('选择')
        save_btn.setFixedSize(80, 42)
        save_btn.clicked.connect(self._select_save_path)
        save_row.addWidget(save_btn)
        open_btn = QPushButton('打开')
        open_btn.setFixedSize(80, 42)
        open_btn.setStyleSheet("QPushButton { background-color: #FF9800; } QPushButton:hover { background-color: #F57C00; }")
        open_btn.clicked.connect(self._open_save_path)
        save_row.addWidget(open_btn)
        layout.addLayout(save_row)

        cookie_label = QLabel('Cookie 文件 (可选):')
        cookie_label.setFont(QFont('Microsoft YaHei', 14))
        layout.addWidget(cookie_label)
        cookie_row = QHBoxLayout()
        self.cookie_input = QLineEdit()
        self.cookie_input.setPlaceholderText('抖音等网站需要提供 Cookie 文件')
        self.cookie_input.setFont(QFont('Microsoft YaHei', 14))
        self.cookie_input.setFixedHeight(42)
        cookie_row.addWidget(self.cookie_input)
        cookie_btn = QPushButton('选择')
        cookie_btn.setFixedSize(80, 42)
        cookie_btn.clicked.connect(self._select_cookie_file)
        cookie_row.addWidget(cookie_btn)
        help_btn = QPushButton('?')
        help_btn.setFixedSize(42, 42)
        help_btn.setFont(QFont('Microsoft YaHei', 14, QFont.Weight.Bold))
        help_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        help_btn.setStyleSheet(
            'QPushButton { background-color: #4CAF50; color: white; border-radius: 21px; font-weight: bold; }'
            'QPushButton:hover { background-color: #45a049; }')
        help_btn.setToolTip('Cookie 获取帮助')
        help_btn.clicked.connect(lambda: self._show_help('Cookie 获取帮助', COOKIE_HELP_TEXT))
        cookie_row.addWidget(help_btn)
        layout.addLayout(cookie_row)

        proxy_label = QLabel('代理 (可选):')
        proxy_label.setFont(QFont('Microsoft YaHei', 14))
        layout.addWidget(proxy_label)
        self.proxy_input = QLineEdit()
        self.proxy_input.setPlaceholderText('例如: http://127.0.0.1:7897 或 socks5://127.0.0.1:1080')
        self.proxy_input.setFont(QFont('Microsoft YaHei', 14))
        self.proxy_input.setFixedHeight(42)
        layout.addWidget(self.proxy_input)

        node_row = QHBoxLayout()
        self.node_status = QLabel()
        self.node_status.setFont(QFont('Microsoft YaHei', 13))
        if check_node_installed():
            self.node_status.setText('Node.js: 已安装')
            self.node_status.setStyleSheet('color: #4CAF50;')
        else:
            self.node_status.setText('Node.js: 未安装 (YouTube 下载需要)')
            self.node_status.setStyleSheet('color: #f44336;')
        node_row.addWidget(self.node_status)
        node_help_btn = QPushButton('?')
        node_help_btn.setFixedSize(42, 42)
        node_help_btn.setFont(QFont('Microsoft YaHei', 14, QFont.Weight.Bold))
        node_help_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        node_help_btn.setStyleSheet(
            'QPushButton { background-color: #FF9800; color: white; border-radius: 21px; font-weight: bold; }'
            'QPushButton:hover { background-color: #F57C00; }')
        node_help_btn.setToolTip('Node.js 安装帮助')
        node_help_btn.clicked.connect(lambda: self._show_help('安装 Node.js', NODE_HELP_TEXT))
        node_row.addWidget(node_help_btn)
        node_row.addStretch()
        layout.addLayout(node_row)

        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setFrameShadow(QFrame.Shadow.Sunken)
        layout.addWidget(line)

        self.download_btn = QPushButton('开始下载')
        self.download_btn.setFixedHeight(55)
        self.download_btn.setFont(QFont('Microsoft YaHei', 18, QFont.Weight.Bold))
        self.download_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        layout.addWidget(self.download_btn)
        self.download_btn.clicked.connect(self._start_download)

        self.progress_bar = QProgressBar()
        self.progress_bar.setFixedHeight(28)
        self.progress_bar.setValue(0)
        layout.addWidget(self.progress_bar)

        self.status_label = QLabel('就绪')
        self.status_label.setFont(QFont('Microsoft YaHei', 13))
        self.status_label.setStyleSheet('color: #666;')
        layout.addWidget(self.status_label)

        log_label = QLabel('下载日志:')
        log_label.setFont(QFont('Microsoft YaHei', 13))
        layout.addWidget(log_label)
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setFont(QFont('Consolas', 12))
        self.log_text.setMinimumHeight(150)
        self.log_text.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        layout.addWidget(self.log_text)

    def _select_save_path(self):
        path = QFileDialog.getExistingDirectory(self, '选择保存路径', self.save_input.text())
        if path:
            self.save_input.setText(path)

    def _open_save_path(self):
        path = self.save_input.text().strip()
        if path and os.path.isdir(path):
            subprocess.Popen(['explorer', os.path.normpath(path)])
        else:
            QMessageBox.warning(self, '提示', '路径不存在')

    def _select_cookie_file(self):
        path, _ = QFileDialog.getOpenFileName(self, '选择 Cookie 文件', '', '文本文件 (*.txt);;所有文件 (*)')
        if path:
            self.cookie_input.setText(path)

    def _show_help(self, title, text):
        self._help_win = HelpWindow(title, text)
        self._help_win.show()

    def _start_download(self):
        url = self.url_input.text().strip()
        if not url:
            QMessageBox.warning(self, '提示', '请输入视频地址')
            return
        save_dir = self.save_input.text().strip()
        if not save_dir:
            QMessageBox.warning(self, '提示', '请选择保存路径')
            return
        if not check_node_installed():
            reply = QMessageBox.question(
                self, '提示', '未检测到 Node.js，下载 YouTube 视频需要它。\n\n是否查看安装帮助？',
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            if reply == QMessageBox.StandardButton.Yes:
                self._show_help('安装 Node.js', NODE_HELP_TEXT)
            return

        cookie_file = self.cookie_input.text().strip() or None
        proxy = self.proxy_input.text().strip() or None

        self.download_btn.setEnabled(False)
        self.download_btn.setText('下载中...')
        self.progress_bar.setValue(0)
        self.log_text.clear()
        self.status_label.setText('正在下载...')
        self.status_label.setStyleSheet('color: #666;')

        self.worker = VideoDownloadWorker(url, save_dir, cookie_file, proxy)
        self.worker.progress_update.connect(self._on_progress_text)
        self.worker.progress_bar_update.connect(self._on_progress_bar)
        self.worker.download_done.connect(self._on_done)
        self.worker.start()

    def _on_progress_text(self, msg):
        self.status_label.setText(msg)
        self.log_text.append(msg)

    def _on_progress_bar(self, downloaded, total, text):
        if total > 0:
            percent = int(downloaded / total * 100)
            self.progress_bar.setValue(percent)
            size_mb = downloaded / (1024 * 1024)
            total_mb = total / (1024 * 1024)
            self.progress_bar.setFormat(f'{size_mb:.1f}/{total_mb:.1f} MB ({percent}%) | {text}')
        else:
            size_mb = downloaded / (1024 * 1024)
            self.progress_bar.setFormat(f'{size_mb:.1f} MB | {text}')

    def _on_done(self, message, success, platform):
        self.download_btn.setEnabled(True)
        self.download_btn.setText('开始下载')
        if success:
            self.progress_bar.setValue(100)
            self.progress_bar.setFormat('下载完成')
            self.status_label.setText(f'下载成功: {message}')
            self.status_label.setStyleSheet('color: #4CAF50; font-weight: bold;')
            self.log_text.append(f'[成功] {message}')
        else:
            self.progress_bar.setValue(0)
            self.progress_bar.setFormat('下载失败')
            self.status_label.setText(f'下载失败: {message}')
            self.status_label.setStyleSheet('color: #f44336; font-weight: bold;')
            self.log_text.append(f'[失败] {message}')


# ==================== Main Window ====================
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle('音视频下载器')
        self.setMinimumSize(900, 700)
        self.resize(1000, 780)

        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        title = QLabel('音视频下载器')
        title.setFont(QFont('Microsoft YaHei', 22, QFont.Weight.Bold))
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet('padding: 12px; color: #1f2937; background: #e0f2fe;')
        layout.addWidget(title)

        tabs = QTabWidget()
        tabs.setFont(QFont('Microsoft YaHei', 13))
        self.music_tab = MusicTab()
        self.video_tab = VideoTab()
        tabs.addTab(self.music_tab, '音乐下载')
        tabs.addTab(self.video_tab, '视频下载')
        layout.addWidget(tabs)


if __name__ == '__main__':
    app = QApplication(sys.argv)
    app.setStyle('Fusion')
    app.setStyleSheet(GLOBAL_STYLE)
    font = QFont('Microsoft YaHei', 10)
    font.setStyleStrategy(QFont.StyleStrategy.PreferAntialias)
    app.setFont(font)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
