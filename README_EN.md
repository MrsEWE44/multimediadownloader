<h1 align="center">Multimedia Downloader</h1>

<p align="center">
  🇺🇸 <a href="./README_EN.md">English</a> | 🇨🇳 <a href="./README.md">简体中文</a>
</p>

<p align="center">
<a href="https://peps.python.org/pep-0719"><img alt="PyPI - Python Version" src="https://img.shields.io/pypi/pyversions/musicdl"></a>
 <a href="https://pypi.org/project/musicdl"><img alt="PyPI - Version" src="https://img.shields.io/pypi/v/musicdl"></a>
 <a href="https://github.com/MrsEWE44/multimediadownloader/releases"><img alt="GitHub Release" src="https://img.shields.io/github/v/release/MrsEWE44/multimediadownloader"></a>
 <a><img alt="GitHub Repo stars" src="https://img.shields.io/github/stars/MrsEWE44/multimediadownloader?style=flat"></a>
 <a><img alt="GitHub forks" src="https://img.shields.io/github/forks/MrsEWE44/multimediadownloader?style=flat"></a>
 <a><img alt="GitHub Downloads (all assets, all releases)" src="https://img.shields.io/github/downloads/MrsEWE44/multimediadownloader/total"></a>
 <a><img alt="GitHub watchers" src="https://img.shields.io/github/watchers/MrsEWE44/multimediadownloader?style=flat"></a>
</p>

<p align="center">
A unified music + video downloader with a PyQt6 tabbed interface. Supports multi-platform music search & download and multi-platform video download.
</p>

---

### Features

#### Music Download

- 17+ music platforms: Kuwo, Kugou, NetEase Cloud, QQ Music, Migu, Qianqian, 5sing, Soda Music, SoundCloud, Spotify, TIDAL, Qobuz, Jamendo, Deezer, Apple Music, Joox, StreetVoice
- Keyword search and playlist URL parsing
- Displays album cover, song name, artist, album, format, size, duration, source
- Table sorting, right-click menu download, batch download (selected / all / unselected)
- Auto-download lyrics (.lrc files)
- Multi-source simultaneous search

#### Video Download

- Supports Bilibili, Douyin (TikTok), Xiaohongshu (RED), YouTube, and more
- Auto platform detection, downloads saved by platform subfolder
- Cookie file support (for sites requiring login like Douyin)
- Proxy support (HTTP / SOCKS5)
- Node.js status check with install guidance (required for YouTube)
- Real-time progress bar with speed display
- Download log viewer

### Screenshots

<table align="center" border="0" cellpadding="10">
  <tr>
    <td align="center">
      <img src="images/1.png" width="350"><br>
      <b>Music Download</b>
    </td>
    <td align="center">
      <img src="images/2.png" width="350"><br>
      <b>Video Download</b>
    </td>
  </tr>
</table>

---

### Run Example：

```bash
# Using Python 3.10+
git clone https://github.com/MrsEWE44/multimediadownloader.git
cd multimediadownloader
python -m venv gqb313
gqb313\Script\Activate.bat
pip install -r requirements.txt
python downloader_gui.py
```

### Build Release Example：

```bash
# Complete the environment setup above first, then install PyInstaller
pip install pyinstaller

# Windows
.\make_release.bat

# Linux / MacOS
bash make_release.sh
```

After building, the `dist/` directory will contain:
- `downloader_gui.exe` — Windowed version (double-click to run)
- `downloader_gui_debug.exe` — Console version (for debugging)

### How to Get Cookie Files

1. Install Chrome extension: [Get cookies.txt LOCALLY](https://chrome.google.com/webstore/detail/get-cookiestxt-locally/cclelndahbckbenkjhflpdbgdldlbecc)
2. Open the target website and log in
3. Click the extension icon in the browser toolbar
4. Click "Export" to save as a `.txt` file
5. Paste the file path into the Cookie input field

### FAQ

| Problem | Solution |
|---------|----------|
| YouTube download fails | Install Node.js >= 22. Official: https://nodejs.org/ |
| Douyin download fails | Provide a Cookie file |
| Bilibili video & audio separate | Install ffmpeg to merge (optional) |
| Slow download from foreign sites | Configure a proxy (e.g. `http://127.0.0.1:7897`) |

### Credits

- [musicdl](https://github.com/CharlesPikachu/musicdl) - Music download engine
- [yt-dlp](https://github.com/yt-dlp/yt-dlp) - Video download engine
- [PyQt6](https://pypi.org/project/PyQt6/) - GUI framework
