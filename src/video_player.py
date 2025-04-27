from PyQt6.QtWidgets import QWidget, QVBoxLayout, QGraphicsView, QGraphicsScene
from PyQt6.QtGui import QPainter
from PyQt6.QtMultimedia import QMediaPlayer
from PyQt6.QtMultimediaWidgets import QGraphicsVideoItem
from PyQt6.QtCore import QUrl, Qt, QRectF, QPointF, QTimer
import os

class VideoPlayer(QWidget):
    def __init__(self, video_path):
        super().__init__()
        self.video_path = video_path
        self.setWindowFlags(Qt.WindowType.Window | Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint)
        
        # Default crop settings
        self.crop_enabled = False
        self.crop_rect = QRectF(0, 0, 0, 0)
        self.pending_crop = None  # Store crop settings to apply after video loads
        
        self.init_ui()
        self.setup_player()
        
        # Use a timer to check when video is available
        self.check_video_timer = QTimer(self)
        self.check_video_timer.setInterval(100)  # Check every 100ms
        self.check_video_timer.timeout.connect(self.check_video_size)
        self.check_video_timer.start()
        self.video_initialized = False

    def init_ui(self):
        """Initialize the video player UI"""
        self.layout = QVBoxLayout()
        self.layout.setContentsMargins(0, 0, 0, 0)

        # Create scene and view
        self.scene = QGraphicsScene(self)
        self.view = QGraphicsView(self.scene, self)
        self.view.setFrameShape(QGraphicsView.Shape.NoFrame)  # No border
        self.view.setStyleSheet("background: transparent;")   # Make background transparent
        self.view.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.view.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.view.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        # Create video item
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
        self.player.mediaStatusChanged.connect(self.handle_media_status)

        # Start playback
        self.player.play()

    def set_video(self, video_path):
        """Change the video file"""
        if os.path.exists(video_path):
            self.video_path = video_path
            self.player.setSource(QUrl.fromLocalFile(video_path))
            self.video_initialized = False  # Reset initialization flag
            self.player.play()
        else:
            print(f"Video file not found: {video_path}")

    def handle_media_status(self, status):
        """Handle media status changes to enable looping"""
        if status == QMediaPlayer.MediaStatus.EndOfMedia:
            self.player.setPosition(0)
            self.player.play()

    def check_video_size(self):
        """Check if video has loaded and has a valid size"""
        size = self.video_item.size()
        
        if not self.video_initialized and size.width() > 0 and size.height() > 0:
            # Only initialize once we have a valid video size
            self.video_initialized = True
            self.on_video_available()
            
    def on_video_available(self):
        """Called when the video becomes available"""
        # Get the video's natural size
        video_size = self.video_item.size()
        print(f"Video loaded with size: {video_size.width()}x{video_size.height()}")
        
        # Initialize the crop rectangle to the full video size
        self.crop_rect = QRectF(0, 0, video_size.width(), video_size.height())
        
        # Update the view to show the whole video initially
        self.view.setSceneRect(0, 0, video_size.width(), video_size.height())
        self.resize(int(video_size.width()), int(video_size.height()))
        
        # Apply pending crop if available
        if self.pending_crop:
            x, y, width, height = self.pending_crop
            self.set_crop(x, y, width, height)
            self.enable_crop(True)
            self.pending_crop = None
        elif self.crop_enabled:
            self.apply_crop()

    def enable_crop(self, enabled=True):
        """Enable or disable cropping"""
        self.crop_enabled = enabled
        
        if not self.video_initialized:
            return
            
        if enabled:
            self.apply_crop()
        else:
            # Reset to show the whole video
            video_size = self.video_item.size()
            self.view.setSceneRect(0, 0, video_size.width(), video_size.height())
            self.resize(int(video_size.width()), int(video_size.height()))

    def set_crop(self, x, y, width, height):
        """Set the crop rectangle"""
        if not self.video_initialized:
            # Store crop settings to apply after video loads
            self.pending_crop = (x, y, width, height)
            return
            
        video_size = self.video_item.size()
        print(f"Setting crop: x={x}, y={y}, w={width}, h={height} on video {video_size.width()}x{video_size.height()}")
        
        # Make sure crop values are within video bounds
        x = max(0, min(x, video_size.width()))
        y = max(0, min(y, video_size.height()))
        width = max(10, min(width, video_size.width() - x))  # Minimum crop width of 10
        height = max(10, min(height, video_size.height() - y))  # Minimum crop height of 10
        
        self.crop_rect = QRectF(x, y, width, height)
        
        if self.crop_enabled:
            self.apply_crop()
        else:
            self.enable_crop(True)
    
    def apply_crop(self):
        """Apply the current crop settings"""
        if not self.crop_enabled or self.crop_rect.isEmpty():
            return
            
        print(f"Applying crop: {self.crop_rect.x()},{self.crop_rect.y()},{self.crop_rect.width()}x{self.crop_rect.height()}")
        
        # Set the view to show only the cropped area
        self.view.setSceneRect(self.crop_rect)
        
        # Resize the window to match the crop size
        self.resize(int(self.crop_rect.width()), int(self.crop_rect.height()))
        
        # Center the cropped area in the view
        self.view.centerOn(self.crop_rect.center())