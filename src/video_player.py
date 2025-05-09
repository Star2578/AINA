from PyQt6.QtWidgets import QWidget, QVBoxLayout, QGraphicsView, QGraphicsScene
from PyQt6.QtGui import QPainter, QTransform
from PyQt6.QtMultimedia import QMediaPlayer
from PyQt6.QtMultimediaWidgets import QGraphicsVideoItem
from PyQt6.QtCore import QUrl, Qt, QRectF, QPointF, QTimer
import os

class VideoPlayer(QWidget):
    def __init__(self, video_path):
        super().__init__()
        self.video_path = video_path
        self.setWindowFlags(Qt.WindowType.Window | Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint)
        
        self.init_ui()
        self.setup_player()
        
        self.check_video_timer = QTimer(self)
        self.check_video_timer.setInterval(100)
        self.check_video_timer.timeout.connect(self.check_video_size)
        self.check_video_timer.start()
        self.video_initialized = False
        self.loop_point_reached = False

    def init_ui(self):
        """Initialize the video player UI"""
        self.layout = QVBoxLayout()
        self.layout.setContentsMargins(0, 0, 0, 0)

        self.scene = QGraphicsScene(self)
        self.view = QGraphicsView(self.scene, self)
        self.view.setFrameShape(QGraphicsView.Shape.NoFrame)
        self.view.setStyleSheet("background: transparent;")
        self.view.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.view.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.view.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        self.video_item = QGraphicsVideoItem()
        self.scene.addItem(self.video_item)
        self.layout.addWidget(self.view)
        self.setLayout(self.layout)

    def setup_player(self):
        """Set up the media player"""
        self.player = QMediaPlayer()
        self.player.setVideoOutput(self.video_item)

        # Load initial video
        self.set_video(self.video_path)

        # Enable looping
        self.player.positionChanged.connect(self.check_loop_point)

        # Start playback
        self.player.play()

    def set_video(self, video_path):
        """Change the video file"""
        if os.path.exists(video_path):
            self.video_path = video_path
            self.player.setSource(QUrl.fromLocalFile(video_path))

            self.video_initialized = False
            self.loop_point_reached = False

            self.player.play()
        else:
            print(f"Video file not found: {video_path}")


    def check_loop_point(self, position):
        """Check if we are near the end of the video and prepare to loop"""
        duration = self.player.duration()
        if duration > 0 and position > duration - 100: # Check if within 100 ms of the end
            if not self.loop_point_reached:
                self.player.setPosition(0)
                self.loop_point_reached = True
        elif self.loop_point_reached and position > 10: # Reset flag if playback has restarted
            self.loop_point_reached = False

    def check_video_size(self):
        """Check if video has loaded and has a valid size"""
        size = self.video_item.size()
        
        if not self.video_initialized and size.width() > 0 and size.height() > 0:
            # Only initialize once we have a valid video size
            self.video_initialized = True
            self.on_video_available()
            
    def on_video_available(self):
        """Called when the video becomes available"""
        video_size = self.video_item.size()
        print(f"Video loaded with size: {video_size.width()}x{video_size.height()}")

        self.resize(200, 200)  # or whatever fixed size you want
        self.apply_center_clip()

    
    def apply_center_clip(self):
        """Center the video in the view while showing only part of it"""
        view_width = self.width()
        view_height = self.height()

        video_size = self.video_item.size()
        if video_size.width() == 0 or video_size.height() == 0:
            return

        # Calculate the offset to center the video in the view
        offset_x = (video_size.width() - view_width) / 2
        offset_y = (video_size.height() - view_height) / 2

        scene_rect = QRectF(offset_x, offset_y, view_width, view_height)
        self.view.setSceneRect(scene_rect)
        self.view.centerOn(QPointF(video_size.width() / 2, video_size.height() / 2))

