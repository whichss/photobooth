import os
import cv2
import time
import json
import qrcode
import random
import threading
import queue
import collections
import customtkinter as ctk
from PIL import Image, ImageTk, ImageDraw, ImageFont, ImageEnhance
import tempfile
import subprocess
import numpy as np
import hashlib
import socket
import zipfile
import shutil
import requests

# 전역 변수 - 모듈 레벨에서 선언    
ALL_SESSIONS = {}  # 해시값: 세션 정보 매핑

# 필요한 폴더 생성
for folder in ['frames', 'frame_configs', 'photos', 'output', 'assets']:
    os.makedirs(folder, exist_ok=True)

# 기본 설정
class Config:
    def __init__(self):
        self.camera_port = 0  # 웹캠 포트 (기본: 0)
        self.countdown_time = 5  # 촬영 전 카운트다운 시간 (초)
        self.default_countdown = 10  # 기본 타이머 (초)
        self.total_photos = 6  # 총 촬영 사진 수
        self.selected_photos = 4  # 선택할 사진 수
        self.frame_path = "frames/default_frame.png"  # 기본 프레임 경로
        self.qr_position = (1050, 50)  # QR 코드 위치
        self.qr_size = 50  # QR 코드 크기 (작게 수정)
        self.output_width = 1200  # 출력 이미지 너비 (4x6 인치)
        self.output_height = 1800  # 출력 이미지 높이 (4x6 인치)
        self.printer_name = "Kodak Dock ERA 6-inch"  # 기본 프린터
        self.frame_buffer_size = 3  # 프레임 버퍼 크기
        self.current_filter = "none"
        self.flash_enabled = True  # 플래시 활성화 여부
        self.image_cache = {}
        self.filter_cache = {}
        self.capture_in_progress = False  # 촬영 중복 방지 플래그
        self.qr_url = None  # QR 코드 URL 초기화

        # 프레임 설정 불러오기 (없으면 기본값)
        try:
            with open("frame_configs/default_frame.json", "r") as f:
                self.frame_config = json.load(f)
                self.frame_config["qr_position"] = {"x": 1000, "y": 50}
        except:
            # 2x2 그리드 레이아웃
            self.frame_config = {
                "photo_positions": [
                    {"x": 120, "y": 220, "width": 410, "height": 710},  # 좌상단
                    {"x": 660, "y": 220, "width": 410, "height": 710},  # 우상단
                    {"x": 120, "y": 1000, "width": 410, "height": 710},  # 좌하단
                    {"x": 660, "y": 1000, "width": 410, "height": 710}  # 우하단
                ],
                "qr_position": {"x": 1200, "y": 50},
                }

    def _get_default_printer(self):
        """기본 프린터 이름 가져오기"""
        try:
            if os.name == 'nt':  # Windows
                printer_info = subprocess.check_output(
                    'wmic printer get name,default', shell=True).decode('utf-8')
                for line in printer_info.split('\n'):
                    if 'TRUE' in line:  # 기본 프린터 찾기
                        return line.replace('TRUE', '').strip()
                return "Microsoft Print to PDF"
            else:  # macOS/Linux
                return "Default"
        except:
            return "Default Printer"

# 프레임 버퍼 클래스
class FrameBuffer:
    def __init__(self, buffer_size=3):
        self.buffer = collections.deque(maxlen=buffer_size)
        self.lock = threading.Lock()

    def add_frame(self, frame):
        with self.lock:
            self.buffer.append(frame)

    def get_latest_frame(self):
        with self.lock:
            if not self.buffer:
                return None
            return self.buffer[-1].copy()

# 코닥 프린터 지원 클래스
class KodakPrinter:
    """코닥 프린터 지원 클래스"""
    def __init__(self, printer_name=None):
        self.printer_name = printer_name
        if self.printer_name is None:
            self.printer_name = self._get_default_printer()
    
    def _get_default_printer(self):
        """기본 프린터 가져오기"""
        try:
            import os
            if os.name == 'nt':  # Windows
                printer_info = subprocess.check_output(
                    'wmic printer get name,default', shell=True).decode('utf-8')
                for line in printer_info.split('\n'):
                    if 'TRUE' in line:  # 기본 프린터 찾기
                        return line.replace('TRUE', '').strip()
                return "Microsoft Print to PDF"
            else:
                return "Default"
        except:
            return "Default Printer"
    
    def print_image(self, image_path):
        """이미지 인쇄 실행"""
        try:
            if os.name == 'nt':  # Windows
                cmd = f'mspaint /pt "{image_path}" "{self.printer_name}"'
                subprocess.call(cmd, shell=True)
                return True
            else:  # macOS/Linux
                cmd = f'lpr -P "{self.printer_name}" "{image_path}"'
                subprocess.call(cmd, shell=True)
                return True
        except Exception as e:
            print(f"인쇄 오류: {e}")
            return False

config = Config()

class PhotoBooth:
    def __init__(self, root):
        self.root = root
        self.config = config
        self.camera = None
        self.session_id = int(time.time())
        self.photos = []
        self.selected_indices = []
        self.frame_colors = ["black", "white", "gray"]  # 프레임 색상 변경
        self.current_frame_color = "black"  # 기본 프레임 색상
        self.frames = []
        self.current_frame_index = 0
        self.photos_taken = False
        self.current_photo_index = 0
        self.current_filter = "none"
        self.image_cache = {}
        self.filter_cache = {}
        self.capture_in_progress = False
        self.max_image_cache = 20
        self.timer_running = False  # 타이머 상태 추적
        self.preview_panel = None  # preview_panel 초기화 추가
        self.ngrok_domain = None  # ngrok 도메인 저장용
        self.camera_initialized = False  # 카메라 초기화 상태 추적 변수 추가

        # 스레드 및 큐 초기화
        self.running = False
        self.frame_buffer = FrameBuffer(self.config.frame_buffer_size)
        self.capture_queue = queue.Queue(maxsize=30)
        self.processing_queue = queue.Queue(maxsize=30)
        self.threads = []

        # UI 설정 및 스타일 초기화
        self.initialize_styles()
        self.frames = self.load_available_frames()
        self.setup_ui()

        self.preview_thread = None
        self.preview_queue = queue.Queue(maxsize=2)
        self.preview_running = False
        self.ngrok_domain = "tight-scorpion-comic.ngrok-free.app"

    def initialize_styles(self):
        """모던한 스타일 테마 설정"""
        # 다크 테마 설정
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("dark-blue")

        # 폰트 설정
        self.fonts = {
            "title": ctk.CTkFont(family="Pretendard", size=36, weight="bold"),
            "subtitle": ctk.CTkFont(family="Pretendard", size=24, weight="bold"),
            "body": ctk.CTkFont(family="Pretendard", size=16),
            "button": ctk.CTkFont(family="Pretendard", size=18, weight="bold"),
            "small": ctk.CTkFont(family="Pretendard", size=14)
        }

        # 모던한 색상 테마
        self.colors = {
            "primary": "#2D3250",      # 진한 네이비
            "primary_dark": "#1A1D2E",  # 더 진한 네이비
            "secondary": "#424769",     # 중간 톤 네이비
            "background": "#0F111A",    # 어두운 배경
            "surface": "#161823",       # 약간 밝은 배경
            "text": "#FFFFFF",          # 흰색 텍스트
            "text_secondary": "#B3B3B3", # 회색 텍스트
            "border": "#2D3250",        # 테두리 색상
            "accent": "#7077A1",        # 강조 색상
            # 프레임 색상
            "frame_black": "#0F111A",
            "frame_white": "#F5F5F5",
            "frame_gray": "#424769"
        }

    def load_available_frames(self):
        """사용 가능한 프레임 로드"""
        frames = []
        # 기본 색상 프레임 생성
        self.create_colored_frames()
        if os.path.exists("frames"):
            for file in os.listdir("frames"):
                if file.endswith(".png"):
                    frames.append(os.path.join("frames", file))
        return frames

    def create_colored_frames(self):
        """여러 색상의 기본 프레임 생성"""
        colors = {
            "black": (18, 18, 18),   # 블랙
            "white": (245, 245, 245), # 화이트
            "gray": (66, 66, 66)     # 그레이
        }

        for color_name, rgb in colors.items():
            try:
                # 빈 프레임 생성 (4x6, 1200x1800)
                frame_img = Image.new('RGBA', (self.config.output_width, self.config.output_height), rgb)
                draw = ImageDraw.Draw(frame_img)

                # 2x2 그리드로 사진 영역 표시
                for pos in self.config.frame_config["photo_positions"]:
                    # 테두리로 사진 영역 표시
                    border_color = (255, 255, 255) if color_name == "black" else (30, 30, 30)
                    draw.rectangle([(pos["x"]-5, pos["y"]-5),
                                  (pos["x"] + pos["width"]+5, (pos["y"] + pos["height"]+5))],
                                 fill=rgb, outline=border_color, width=3)

                # 저장
                frame_path = f"frames/{color_name}_frame.png"
                frame_img.save(frame_path)
                print(f"{color_name} 프레임 생성 완료")
            except Exception as e:
                print(f"{color_name} 프레임 생성 중 오류: {e}")

    def load_image(self, path, size=None):
        """이미지 로드 및 캐싱"""
        cache_key = f"{path}_{size}"
        if cache_key in self.image_cache:
            return self.image_cache[cache_key]

        try:
            img = Image.open(path)
            if size:
                img = img.resize(size, Image.LANCZOS)
            photo = ImageTk.PhotoImage(img)
            
            # 캐시 관리
            if len(self.image_cache) > self.max_image_cache:
                keys = list(self.image_cache.keys())
                for _ in range(len(keys) - self.max_image_cache + 1):
                    key_to_remove = random.choice(keys)
                    if key_to_remove in self.image_cache:
                        del self.image_cache[key_to_remove]
                        keys.remove(key_to_remove)
            
            self.image_cache[cache_key] = photo
            return photo
        except Exception as e:
            print(f"이미지 로딩 오류: {e}")
            return None

    def setup_ui(self):
        """UI 초기화 및 설정"""
        self.root.title("photobooth")
        # 창 크기 설정
        self.root.geometry("1280x800")
        self.root.resizable(True, True)

        # Esc 키로 창 닫기
        self.root.bind("<Escape>", lambda event: self.cleanup_and_quit())
        self.root.protocol("WM_DELETE_WINDOW", self.cleanup_and_quit)

        # 메인 프레임
        self.main_frame = ctk.CTkFrame(self.root, corner_radius=0, fg_color=self.colors["background"])
        self.main_frame.pack(fill="both", expand=True)

        # 시작 화면
        self.setup_start_screen()

    def cleanup_and_quit(self):
        """모든 자원 정리 후 종료"""
        self.running = False
        # 모든 스레드 종료 대기
        for thread in self.threads:
            if thread.is_alive() and thread != threading.current_thread():
                thread.join(timeout=1.0)
        
        # 카메라 자원 해제
        if self.camera is not None:
            self.camera.release()

        # 캐시 비우기
        self.image_cache.clear()
        self.filter_cache.clear()

        # 애플리케이션 종료
        self.root.quit()
        self.root.destroy()

    def toggle_fullscreen(self):
        """전체화면 모드 전환"""
        is_fullscreen = self.root.attributes('-fullscreen')
        self.root.attributes('-fullscreen', not is_fullscreen)

    def get_available_cameras(self):
        """사용 가능한 카메라 목록 가져오기"""
        available_cameras = []
        for i in range(5):  # 0~4까지 카메라 확인
            try:
                if os.name == 'nt':
                    cap = cv2.VideoCapture(i, cv2.CAP_DSHOW)
                else:
                    cap = cv2.VideoCapture(i)
                    
                if cap.isOpened():
                    ret, _ = cap.read()
                    if ret:
                        available_cameras.append(i)
                cap.release()
            except Exception as e:
                print(f"카메라 {i} 확인 중 오류: {e}")
        return available_cameras

    def get_working_camera(self):
        """작동하는 카메라 포트 찾기"""
        for port in range(4):  # 0~3 포트 확인
            try:
                print(f">>> 카메라 포트 {port} 테스트 중")
                cam = cv2.VideoCapture(port, cv2.CAP_MSMF)  # Media Foundation 사용
                if cam.isOpened():
                    ret, frame = cam.read()
                    if ret and frame is not None and frame.size > 0:
                        print(f">>> 카메라 포트 {port} 사용 가능")
                        cam.release()
                        return port
                cam.release()
            except Exception as e:
                print(f">>> 카메라 포트 {port} 테스트 중 오류: {e}")
        return -1  # 사용 가능한 카메라 없음

    def setup_start_screen(self):
        """심플한 시작 화면"""
        # 기존 위젯 정리
        for widget in self.main_frame.winfo_children():
            widget.destroy()

        # 배경 설정
        self.main_frame.configure(fg_color=self.colors["background"])

        # 로고 패널
        logo_panel = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        logo_panel.pack(pady=(80, 20))

        # 로고 텍스트
        title_label = ctk.CTkLabel(
            logo_panel,
            text="photobooth",
            font=self.fonts["title"],
            text_color=self.colors["text"],
            fg_color="transparent"
        )
        title_label.pack()

        # 설명 텍스트
        desc_label = ctk.CTkLabel(
            self.main_frame,
            text="오늘, 이 순간을 걸작인 당신으로 남겨보세요",
            font=self.fonts["body"],
            text_color=self.colors["text_secondary"],
            fg_color="transparent"
        )
        desc_label.pack(pady=(10, 40))

        # 중앙 패널
        center_panel = ctk.CTkFrame(
            self.main_frame,
            fg_color=self.colors["surface"],
            corner_radius=20,
            border_width=1,
            border_color=self.colors["border"],
            width=600,
            height=400
        )
        center_panel.pack(pady=20)
        center_panel.pack_propagate(False)

        # 촬영 시작 버튼
        start_button = ctk.CTkButton(
            center_panel,
            text="촬영 시작",
            font=self.fonts["button"],
            fg_color=self.colors["primary"],
            hover_color=self.colors["primary_dark"],
            text_color=self.colors["text"],
            corner_radius=15,
            width=280,
            height=100,
            command=self.start_photo_session
        )
        start_button.pack(pady=(80, 30))

        # 하단 버튼 패널
        bottom_panel = ctk.CTkFrame(center_panel, fg_color="transparent")
        bottom_panel.pack(side="bottom", pady=30)

        # 설정 버튼
        settings_button = ctk.CTkButton(
            bottom_panel,
            text="설정",
            font=self.fonts["body"],
            fg_color=self.colors["secondary"],
            text_color=self.colors["text"],
            hover_color=self.colors["primary_dark"],
            corner_radius=10,
            width=160,
            height=50,
            command=self.show_printer_settings
        )
        settings_button.pack(side="left", padx=10)

    def debug_camera_test(self):
        """카메라 테스트 디버깅 함수"""
        print("카메라 직접 테스트 시작")
        self.show_notification("카메라 테스트 시작...")
        try:
            cam = cv2.VideoCapture(self.config.camera_port)
            if cam.isOpened():
                print("카메라 열림 성공")
                ret, frame = cam.read()
                if ret:
                    print("프레임 읽기 성공")
                    # 읽은 프레임을 파일로 저장
                    cv2.imwrite("camera_test.jpg", frame)
                    print("테스트 이미지 저장 완료")
                    self.show_notification("카메라 테스트 성공! camera_test.jpg 저장됨")
                else:
                    print("프레임 읽기 실패")
                    self.show_error("프레임을 읽을 수 없습니다")
                cam.release()
            else:
                print("카메라 열기 실패")
                self.show_error("카메라를 열 수 없습니다")
        except Exception as e:
            print(f"카메라 테스트 오류: {e}")
            self.show_error(f"카메라 테스트 오류: {e}")

    def show_camera_selection(self):
        """카메라 선택 화면"""
        # 기존 위젯 정리
        for widget in self.main_frame.winfo_children():
            widget.destroy()

        # 배경 패널
        background_panel = ctk.CTkFrame(self.main_frame, fg_color=self.colors["background"])
        background_panel.pack(fill="both", expand=True)

        # 제목 패널
        header_panel = ctk.CTkFrame(background_panel, fg_color=self.colors["primary"], corner_radius=0, height=100)
        header_panel.pack(fill="x", side="top")
        title_label = ctk.CTkLabel(
            header_panel,
            text="카메라 선택",
            font=self.fonts["title"],
            text_color=self.colors["text"]
        )
        title_label.pack(pady=30)

        # 카메라 목록 가져오기
        cameras = self.get_available_cameras()

        # 카메라 선택 영역
        camera_panel = ctk.CTkFrame(background_panel, fg_color=self.colors["surface"], corner_radius=15)
        camera_panel.pack(fill="both", expand=True, padx=40, pady=40)

        if not cameras:
            # 카메라가 없는 경우
            error_label = ctk.CTkLabel(
                camera_panel,
                text="사용 가능한 카메라가 없습니다.",
                font=self.fonts["subtitle"],
                text_color=self.colors["text"]
            )
            error_label.pack(pady=100)
        else:
            # 카메라 설명 텍스트
            desc_label = ctk.CTkLabel(
                camera_panel,
                text="사용할 카메라를 선택하세요",
                font=self.fonts["body"],
                text_color=self.colors["text"]
            )
            desc_label.pack(pady=(40, 30))

            # 카메라 목록
            for i, cam_index in enumerate(cameras):
                camera_name = f"카메라 {cam_index}"
                # Logitech 웹캠 탐지 시도
                if cam_index == 0:
                    camera_name = f"Logitech Webcam (카메라 {cam_index})"
                
                camera_button = ctk.CTkButton(
                    camera_panel,
                    text=camera_name,
                    font=self.fonts["body"],
                    fg_color=self.colors["primary"] if cam_index == self.config.camera_port else self.colors["secondary"],
                    text_color=self.colors["text"],
                    hover_color=self.colors["primary_dark"],
                    corner_radius=15,
                    width=500,
                    height=70,
                    command=lambda idx=cam_index: self.select_camera(idx)
                )
                camera_button.pack(pady=10)

        # 뒤로 가기 버튼
        back_button = ctk.CTkButton(
            background_panel,
            text="뒤로 가기",
            font=self.fonts["button"],
            fg_color=self.colors["secondary"],
            text_color=self.colors["text"],
            hover_color="#333333",
            corner_radius=15,
            width=200,
            height=60,
            command=self.setup_start_screen
        )
        back_button.pack(pady=30)

    def select_camera(self, camera_index):
        """카메라 선택"""
        self.config.camera_port = camera_index
        self.show_notification(f"카메라 {camera_index}번이 선택되었습니다.")
        self.setup_start_screen()

    def show_frame_selection(self):
        """프레임 선택 화면"""
        # 기존 위젯 정리
        for widget in self.main_frame.winfo_children():
            widget.destroy()

        # 배경 패널
        background_panel = ctk.CTkFrame(self.main_frame, fg_color=self.colors["background"])
        background_panel.pack(fill="both", expand=True)

        # 제목 패널
        header_panel = ctk.CTkFrame(background_panel, fg_color=self.colors["primary"], corner_radius=0, height=100)
        header_panel.pack(fill="x", side="top")
        title_label = ctk.CTkLabel(
            header_panel,
            text="프레임 선택",
            font=self.fonts["title"],
            text_color=self.colors["text"]
        )
        title_label.pack(pady=30)

        # 프레임 선택 영역
        frame_panel = ctk.CTkFrame(background_panel, fg_color=self.colors["surface"], corner_radius=15)
        frame_panel.pack(fill="both", expand=True, padx=40, pady=40)

        # 프레임 컬러 선택 패널
        color_panel = ctk.CTkFrame(frame_panel, fg_color="transparent")
        color_panel.pack(pady=20)

        # 블랙 프레임 버튼
        black_button = ctk.CTkButton(
            color_panel,
            text="블랙",
            font=self.fonts["body"],
            fg_color=self.colors["frame_black"],
            text_color=self.colors["text"],
            hover_color="#000000",
            corner_radius=15,
            width=120,
            height=40,
            command=lambda: self.select_frame_color("black")
        )
        black_button.pack(side="left", padx=10)

        # 화이트 프레임 버튼
        white_button = ctk.CTkButton(
            color_panel,
            text="화이트",
            font=self.fonts["body"],
            fg_color=self.colors["frame_white"],
            text_color="#000000",
            hover_color="#E0E0E0",
            corner_radius=15,
            width=120,
            height=40,
            command=lambda: self.select_frame_color("white")
        )
        white_button.pack(side="left", padx=10)

        # 그레이 프레임 버튼
        gray_button = ctk.CTkButton(
            color_panel,
            text="그레이",
            font=self.fonts["body"],
            fg_color=self.colors["frame_gray"],
            text_color=self.colors["text"],
            hover_color="#333333",
            corner_radius=15,
            width=120,
            height=40,
            command=lambda: self.select_frame_color("gray")
        )
        gray_button.pack(side="left", padx=10)

        # 현재 선택된 프레임 표시
        if self.frames:
            frame_index = -1
            for idx, frame_path in enumerate(self.frames):
                if self.current_frame_color in frame_path:
                    frame_index = idx
                    break

            if frame_index >= 0:
                try:
                    frame_img = Image.open(self.frames[frame_index])
                    frame_img = frame_img.resize((300, 450), Image.LANCZOS)
                    frame_photo = ImageTk.PhotoImage(frame_img)
                    frame_label = ctk.CTkLabel(frame_panel, text="", image=frame_photo)
                    frame_label.image = frame_photo
                    frame_label.pack(pady=20)
                    frame_name = os.path.basename(self.frames[frame_index]).replace(".png", "")
                    name_label = ctk.CTkLabel(
                        frame_panel,
                        text=f"프레임: {frame_name}",
                        font=self.fonts["body"],
                        text_color=self.colors["text"]
                    )
                    name_label.pack(pady=10)
                except Exception as e:
                    self.show_error(f"프레임을 표시할 수 없습니다: {str(e)}")

        # 선택 완료 버튼
        select_button = ctk.CTkButton(
            background_panel,
            text="이 프레임 선택",
            font=self.fonts["button"],
            fg_color=self.colors["primary"],
            hover_color=self.colors["primary_dark"],
            text_color=self.colors["text"],
            corner_radius=15,
            width=220,
            height=60,
            command=self.setup_start_screen
        )
        select_button.pack(pady=20)

        # 뒤로 가기 버튼
        back_button = ctk.CTkButton(
            background_panel,
            text="뒤로 가기",
            font=self.fonts["button"],
            fg_color=self.colors["secondary"],
            text_color=self.colors["text"],
            hover_color="#333333",
            corner_radius=15,
            width=150,
            height=50,
            command=self.setup_start_screen
        )
        back_button.pack(pady=10)

    def select_frame_color(self, color):
        """프레임 색상 선택"""
        self.current_frame_color = color
        self.show_notification(f"{color.capitalize()} 프레임이 선택되었습니다.")
        # 프레임 인덱스 업데이트
        for idx, frame_path in enumerate(self.frames):
            if color in frame_path:
                self.current_frame_index = idx
                self.config.frame_path = self.frames[idx]
                break
        self.show_frame_selection()  # 화면 갱신

    def initialize_camera(self):
        """간소화된 카메라 초기화 함수"""
        try:
            print(f">>> 카메라 초기화 시도: 포트 {self.config.camera_port}")
            # DirectShow 백엔드 사용 (Windows에서 더 안정적)
            if os.name == 'nt':
                self.camera = cv2.VideoCapture(self.config.camera_port, cv2.CAP_DSHOW)
            else:
                self.camera = cv2.VideoCapture(self.config.camera_port)
                
            # 안정화 대기
            time.sleep(1.0)
            
            # 연결 확인
            if not self.camera.isOpened():
                print(">>> 카메라를 열 수 없습니다.")
                return False
                
            # 테스트 프레임 읽기
            ret, frame = self.camera.read()
            if not ret or frame is None:
                print(">>> 프레임을 읽을 수 없습니다.")
                return False
                
            print(">>> 카메라 초기화 성공!")
            return True
        except Exception as e:
            print(f">>> 카메라 초기화 오류: {e}")
            return False

    def start_photo_session(self):
        """스레드 없이 직접 실행하는 방식으로 변경"""
        print(">>> 촬영 시작 버튼 클릭됨")
        
        # 모든 설정 초기화
        self.photos = []
        self.selected_indices = []
        self.photos_taken = False
        self.current_photo_index = 0
        self.capture_in_progress = False
        self.timer_running = False
        self.current_filter = "none"  # 필터 초기화
        self.current_frame_index = 0  # 프레임 인덱스 초기화
        self.current_frame_color = "black"  # 프레임 색상 초기화
        self.config.frame_path = "frames/black_frame.png"  # 기본 프레임 경로 초기화
        
        # 세션 폴더 및 해시 생성
        timestamp = time.strftime('%Y%m%d_%H%M%S')
        folder_name = f"photos/{timestamp}"
        os.makedirs(folder_name, exist_ok=True)
        self.session_folder = folder_name
        
        # 세션 해시 생성 (임시로 시간 기반으로 생성)
        self.session_hash = self.generate_hash(folder_name)
        
        # 세션 매핑
        ALL_SESSIONS[self.session_hash] = {'folder': folder_name, 'photos': [], 'gif': None, 'created_at': time.time()}
        
        # QR 코드 미리 생성 (세션 폴더 경로가 설정된 후에 호출)
        try:
            self.qr_image = self.generate_qr_code()
            if self.qr_image is None:
                print(">>> QR 코드 생성 실패, 카메라 초기화 계속 진행")
        except Exception as e:
            print(f">>> QR 코드 생성 중 오류: {e}")
        
        # 서버 정보 및 안내 메시지 출력
        local_ip = get_local_ip() if 'get_local_ip' in globals() else 'localhost'
        server_url = f"http://{local_ip}:5000"
        promo_url = f"{server_url}/promo"
        qr_url = f"https://{self.ngrok_domain}/download?img=output/session_{timestamp}_final.png"  # ngrok 도메인 사용
        print(f"[서버] 서버가 {server_url} 에서 실행 중입니다.")
        print(f"[서버] 실시간 사진 전시: {promo_url}")
        print(f"[서버] 새폴더 감지: {folder_name}, 해시: {self.session_hash}")
        print(f"[서버] QR코드 링크: {qr_url}")
        
        try:
            # 기존에 초기화된 카메라가 있다면 정리
            if self.camera is not None:
                print(">>> 기존 카메라 자원 해제 중...")
                self.camera.release()
                self.camera = None
                self.camera_initialized = False
                
                # 스레드 정리
                self.running = False
                self.preview_running = False
                
                if hasattr(self, 'preview_thread') and self.preview_thread and self.preview_thread.is_alive():
                    self.preview_thread.join(timeout=1)
                    
                for thread in self.threads:
                    if thread.is_alive():
                        thread.join(timeout=1)
                
                # 잠시 대기 (자원 해제 시간 확보)
                time.sleep(0.5)
                print(">>> 기존 카메라 정리 완료")
            
            # 카메라 초기화
            print(">>> 새 카메라 초기화 시작...")
            success = self.initialize_camera()
            print(f">>> 카메라 초기화 결과: {success}")
            if success:
                self.running = True
                self.camera_initialized = True  # 카메라 초기화 성공 표시
                self.initialize_camera_threads()
                self.setup_capture_screen()
            else:
                self.show_error("카메라를 초기화할 수 없습니다.")
        except Exception as e:
            print(f">>> 오류 발생: {e}")
            self.show_error(f"촬영 시작 중 오류: {e}")

    def generate_qr_code(self):
        """QR 코드 생성 및 표시"""
        try:
            # 세션 ID 추출 (폴더명에서 숫자만 추출)
            session_id = ''.join(filter(str.isdigit, os.path.basename(self.session_folder)))
            
            # 세션 해시 생성 (server.js와 일치하도록)
            self.session_hash = hashlib.md5(session_id.encode()).hexdigest()[:12]
            
            # ngrok 도메인 사용하여 URL 생성
            qr_url = f"https://{self.ngrok_domain}/download?img=output/session_{session_id}_final.png"
            self.config.qr_url = qr_url
            
            # 품질 향상된 QR 코드 생성
            qr = qrcode.QRCode(
                version=4,  # 더 큰 QR 코드
                error_correction=qrcode.constants.ERROR_CORRECT_H,  # 높은 오류 수정
                box_size=10,  # 박스 크기
                border=4  # 여백
            )
            qr.add_data(qr_url)
            qr.make(fit=True)
            
            qr_img = qr.make_image(fill_color="black", back_color="white")
            
            # 임시 파일로 저장
            qr_path = os.path.join(tempfile.gettempdir(), f"qr_{self.session_hash}.png")
            qr_img.save(qr_path)
            
            # PIL 이미지를 CTkImage로 변환
            qr_pil_img = Image.open(qr_path)
            qr_size = self.config.qr_size * 2  # 크기 2배 증가
            qr_pil_img = qr_pil_img.resize((qr_size, qr_size), Image.LANCZOS)
            
            # CTkImage 생성
            qr_ctk_image = ctk.CTkImage(
                light_image=qr_pil_img,
                dark_image=qr_pil_img,
                size=(qr_size, qr_size)
            )
            
            print(f"QR 코드 생성 완료: {qr_url}")
            return qr_ctk_image
        except Exception as e:
            print(f"QR 코드 생성 오류: {e}")
            return None

    def video_capture_thread(self):
        """카메라 캡처 스레드"""
        print("캡처 스레드 시작")
        while self.running and self.camera and self.camera.isOpened():
            try:
                ret, frame = self.camera.read()
                if ret:
                    if not self.capture_queue.full():
                        self.capture_queue.put(frame)
            except Exception as e:
                print(f"캡처 스레드 오류: {e}")
            time.sleep(0.01)
        print("캡처 스레드 종료")

    def video_processing_thread(self):
        """캡처된 프레임 처리 스레드"""
        print("처리 스레드 시작")
        while self.running:
            try:
                # 캡처 큐에서 프레임 가져오기
                try:
                    frame = self.capture_queue.get(timeout=0.1)
                    # 프레임 처리 (9:16 비율로 크롭)
                    processed_frame = self.process_frame(frame)
                    # 프레임 버퍼에 추가
                    self.frame_buffer.add_frame(processed_frame)
                    # UI 업데이트는 메인 스레드에서
                    if hasattr(self, 'preview_label') and self.preview_label.winfo_exists():
                        self.root.after(0, lambda f=processed_frame: self.update_preview_ui(f))
                except queue.Empty:
                    pass  # 큐가 비어있으면 계속
            except Exception as e:
                print(f"처리 스레드 오류: {e}")

            # CPU 점유율 감소
            time.sleep(0.01)
        print("처리 스레드 종료")

    def process_frame(self, frame):
        """프레임 처리 - 상하반전 및 왼쪽 90도 회전"""
        try:
            if frame is None:
                return None
                
            # 상하반전 적용
            frame = cv2.flip(frame, 0)
            
            # 왼쪽으로 90도 회전
            frame = cv2.rotate(frame, cv2.ROTATE_90_COUNTERCLOCKWISE)
            
            return frame
        except Exception as e:
            print(f"프레임 처리 오류: {e}")
            return None

    def setup_capture_screen(self):
        """심플한 촬영 화면"""
        # 기존 위젯 정리
        for widget in self.main_frame.winfo_children():
            widget.destroy()

        # 배경 패널
        background_panel = ctk.CTkFrame(self.main_frame, fg_color=self.colors["background"])
        background_panel.pack(fill="both", expand=True)

        # 제목 패널
        header_panel = ctk.CTkFrame(background_panel, fg_color=self.colors["primary"], corner_radius=0, height=60)
        header_panel.pack(fill="x", side="top")
        title_label = ctk.CTkLabel(
            header_panel,
            text="photobooth",
            font=self.fonts["title"],
            text_color=self.colors["text"]
        )
        title_label.pack(pady=15)

        # 레이아웃 설정
        self.capture_frame = ctk.CTkFrame(background_panel, fg_color="transparent")
        self.capture_frame.pack(fill="both", expand=True, padx=20, pady=20)

        # 미리보기 화면 (중앙) - 9:16 비율로 설정
        preview_width = 800
        preview_height = int(preview_width * 16 / 9)
        self.preview_frame = ctk.CTkFrame(
            self.capture_frame,
            fg_color=self.colors["surface"],
            corner_radius=15,
            width=preview_width + 20,
            height=preview_height + 20
        )
        self.preview_frame.pack(side="left", padx=10, pady=10, fill="both", expand=True)
        self.preview_frame.pack_propagate(False)

        self.preview_label = ctk.CTkLabel(self.preview_frame, text="")
        self.preview_label.pack(fill="both", expand=True, padx=5, pady=5)

        # 타이머 및 버튼 영역 (오른쪽)
        self.control_frame = ctk.CTkFrame(self.capture_frame, width=300, fg_color=self.colors["surface"], corner_radius=15)
        self.control_frame.pack(side="right", padx=10, pady=10, fill="y")

        # 타이머 레이블
        self.countdown_label = ctk.CTkLabel(
            self.control_frame,
            text="촬영 준비",
            font=self.fonts["title"],
            text_color=self.colors["accent"]
        )
        self.countdown_label.pack(pady=(50, 30))

        # 촬영 버튼
        self.capture_button = ctk.CTkButton(
            self.control_frame,
            text="촬영",
            font=self.fonts["button"],
            fg_color=self.colors["primary"],
            hover_color=self.colors["primary_dark"],
            text_color=self.colors["text"],
            corner_radius=15,
            width=200,
            height=60,
            command=self.start_manual_countdown
        )
        self.capture_button.pack(pady=30)

        # 촬영 횟수 표시
        self.photo_count_label = ctk.CTkLabel(
            self.control_frame,
            text=f"촬영: {self.current_photo_index+1}/{self.config.total_photos}",
            font=self.fonts["body"],
            text_color=self.colors["text_secondary"]
        )
        self.photo_count_label.pack(side="bottom", pady=40)

        # 자동 타이머 시작
        self.start_auto_countdown()

    def start_auto_countdown(self):
        """자동 40초 타이머 시작"""
        if self.timer_running:
            return
            
        self.timer_running = True
        self.remaining_time = self.config.default_countdown  # 40초
        self.update_countdown()

    def start_manual_countdown(self):
        """사용자 클릭 시 5초 타이머 시작"""
        if self.capture_in_progress:
            return
            
        self.capture_in_progress = True
        self.timer_running = True
        self.capture_button.configure(state="disabled")  # 버튼 비활성화
        self.countdown_label.configure(text="촬영 준비 중...")  # 카운트다운 텍스트 업데이트
        self.remaining_time = self.config.countdown_time  # 5초로 설정
        self.update_countdown()
    
    def update_countdown(self):
        """타이머 업데이트"""
        if hasattr(self, 'remaining_time') and self.remaining_time > 0 and self.timer_running:
            self.countdown_label.configure(text=str(self.remaining_time))
            self.capture_button.configure(state="disabled")  # 카운트다운 중 버튼 비활성화
            self.remaining_time -= 1
            self.root.after(1000, self.update_countdown)
        elif self.timer_running:  # 타이머 종료
            self.countdown_label.configure(text="찰칵!")
            self.timer_running = False
            # 타이머가 끝났을 때만 사진 촬영
            self.capture_photo()

    def capture_photo(self):
        """사진 촬영 - GIF 기능 없이 단순화"""
        try:
            # 버튼 비활성화
            if hasattr(self, 'capture_button'):
                self.capture_button.configure(state="disabled")
                
            # 현재 프레임 버퍼에서 최신 프레임 가져오기
            current_frame = self.frame_buffer.get_latest_frame()
            if current_frame is None:
                self.show_error("카메라 프레임을 가져올 수 없습니다.")
                self.capture_button.configure(state="normal")
                self.capture_in_progress = False
                return

            # OpenCV BGR -> RGB 변환
            frame_rgb = cv2.cvtColor(current_frame, cv2.COLOR_BGR2RGB)
            
            # PIL Image로 변환
            self.current_preview_image = Image.fromarray(frame_rgb)
            
            # 단순 사진 저장
            photo_path = f"{self.session_folder}/photo_{self.current_photo_index}.jpg"
            self.current_preview_image.save(photo_path, quality=95)
            
            # 사진 추가
            self.photos.append(photo_path)
            # 세션 매핑에도 추가
            if hasattr(self, 'session_hash') and self.session_hash in ALL_SESSIONS:
                ALL_SESSIONS[self.session_hash]['photos'].append(photo_path)
            
            # 인덱스 증가 및 UI 업데이트
            self.current_photo_index += 1
            self.photo_count_label.configure(
                text=f"촬영: {self.current_photo_index}/{self.config.total_photos}"
            )
            
            # 다음 단계 결정
            if self.current_photo_index < self.config.total_photos:
                # 아직 촬영할 사진이 남아있음
                self.countdown_label.configure(text="다음 촬영 준비 중...")
                self.capture_in_progress = False
                
                # 버튼 활성화 및 타이머 다시 시작
                self.root.after(1000, lambda: self.capture_button.configure(state="normal"))
                self.root.after(1000, lambda: setattr(self, 'capture_in_progress', False))
                self.root.after(2000, self.start_auto_countdown)
            else:
                # 모든 사진 촬영 완료
                self.photos_taken = True
                self.cleanup_camera()
                self.show_photo_selection_screen()
        except Exception as e:
            print(f"촬영 오류: {e}")
            self.show_error(f"촬영 오류: {e}")
            if hasattr(self, 'capture_button'):
                self.capture_button.configure(state="normal")
            self.capture_in_progress = False

    def cleanup_camera(self):
        """카메라 정리"""
        self.running = False
        self.preview_running = False
        
        if self.preview_thread:
            self.preview_thread.join(timeout=1)
            
        for thread in self.threads:
            thread.join(timeout=1)
            
        if self.camera is not None:
            self.camera.release()
            self.camera = None
            self.camera_initialized = False  # 카메라 초기화 상태 재설정

        # 큐 비우기
        while not self.capture_queue.empty():
            try:
                self.capture_queue.get_nowait()
            except:
                pass

        # 프레임 버퍼 초기화
        self.frame_buffer = FrameBuffer(self.config.frame_buffer_size)
        print("카메라 자원 정리 완료")

    def cancel_photo_session(self):
        """촬영 세션 취소"""
        self.timer_running = False  # 타이머 중지
        self.cleanup_camera()
        self.setup_start_screen()

    def get_current_frame_path(self):
        """현재 선택된 프레임 경로 반환"""
        if self.current_frame_index < len(self.frames):
            return self.frames[self.current_frame_index]
        
        # 색상으로 찾기 (백업)
        for path in self.frames:
            if self.current_frame_color in path:
                return path
        return self.frames[0] if self.frames else None


    def show_photo_selection_screen(self):
        """촬영된 사진 중 4개 선택 화면"""
        # 기존 위젯 정리
        for widget in self.main_frame.winfo_children():
            widget.destroy()

        # 배경 설정
        self.main_frame.configure(fg_color=self.colors["background"])

        # 제목 패널
        header_panel = ctk.CTkFrame(self.main_frame, fg_color=self.colors["primary"], corner_radius=0, height=100)
        header_panel.pack(fill="x", side="top")
        
        # 제목과 다음 버튼을 포함할 프레임
        title_frame = ctk.CTkFrame(header_panel, fg_color="transparent")
        title_frame.pack(fill="x", padx=20)
        
        # 제목
        title_label = ctk.CTkLabel(
            title_frame,
            text="사진 선택",
            font=self.fonts["title"],
            text_color=self.colors["text"]
        )
        title_label.pack(side="left", pady=30)
        
        # 다음 버튼
        next_button = ctk.CTkButton(
            title_frame,
            text="다음",
            font=self.fonts["button"],
            fg_color=self.colors["primary"],
            hover_color=self.colors["primary_dark"],
            text_color=self.colors["text"],
            corner_radius=15,
            width=200,
            height=60,
            command=self.show_frame_filter_selection_screen
        )
        next_button.pack(side="right", pady=20)

        # 메인 컨텐츠 영역 (좌측: 사진 선택, 우측: 미리보기)
        content_frame = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        content_frame.pack(fill="both", expand=True, padx=20, pady=20)

        # 좌측 패널: 사진 선택 영역 (크기 조정)
        left_panel = ctk.CTkFrame(content_frame, fg_color=self.colors["surface"], corner_radius=15, width=500)
        left_panel.pack(side="left", fill="both", expand=True, padx=(0, 10))

        # 안내 문구
        instruction_label = ctk.CTkLabel(
            left_panel,
            text=f"{self.config.selected_photos}장의 사진을 선택해주세요",
            font=self.fonts["subtitle"],
            text_color=self.colors["text"]
        )
        instruction_label.pack(pady=(20, 10))

        # 사진 선택 영역
        self.photo_frame = ctk.CTkFrame(left_panel, fg_color="transparent")
        self.photo_frame.pack(fill="both", expand=True, padx=20, pady=10)

        # 선택된 사진 개수 표시
        self.selection_count_label = ctk.CTkLabel(
            left_panel,
            text=f"선택된 사진: 0/{self.config.selected_photos}",
            font=self.fonts["body"]
        )
        self.selection_count_label.pack(pady=10)

        # 사진 표시 및 선택 버튼
        for i, photo_path in enumerate(self.photos):
            try:
                img = Image.open(photo_path)
                img = img.resize((300, 450), Image.LANCZOS)
                photo_img = ctk.CTkImage(
                    light_image=img,
                    dark_image=img,
                    size=(300, 450)
                )
                photo_button = ctk.CTkButton(
                    self.photo_frame,
                    image=photo_img,
                    text="",
                    fg_color=self.colors["surface"],
                    hover_color=self.colors["primary"],
                    border_width=2,
                    border_color=self.colors["border"],
                    corner_radius=15,
                    command=lambda idx=i: self.toggle_photo_selection(idx)
                )
                photo_button.image = photo_img
                photo_button.photo_index = i
                photo_button.grid(row=i // 3, column=i % 3, padx=10, pady=10)
            except Exception as e:
                print(f"사진 {i} 로드 오류: {e}")

        # 우측 패널: 미리보기 영역 (크기 조정)
        right_panel = ctk.CTkFrame(content_frame, fg_color=self.colors["surface"], corner_radius=15, width=700)
        right_panel.pack(side="right", fill="both", expand=True, padx=(10, 0))

        # 미리보기 패널
        self.preview_panel = ctk.CTkFrame(right_panel, fg_color=self.colors["background"], corner_radius=10)
        self.preview_panel.pack(fill="both", expand=True, padx=40, pady=40)

        # 미리보기 초기화
        self.preview_label = ctk.CTkLabel(
            self.preview_panel,
            text="사진을 선택하면\n미리보기가 표시됩니다",
            font=self.fonts["body"]
        )
        self.preview_label.pack(fill="both", expand=True)

    def show_frame_filter_selection_screen(self):
        """프레임과 필터 선택 화면"""
        # 기존 위젯 정리
        for widget in self.main_frame.winfo_children():
            widget.destroy()

        # 메인 컨테이너
        container = ctk.CTkFrame(self.main_frame, fg_color=self.colors["background"])
        container.pack(fill="both", expand=True)

        # 상단 패널
        top_panel = ctk.CTkFrame(container, fg_color=self.colors["primary"], corner_radius=0, height=100)
        top_panel.pack(fill="x", side="top")

        # 제목과 다음 버튼을 포함할 프레임
        title_frame = ctk.CTkFrame(top_panel, fg_color="transparent")
        title_frame.pack(fill="x", padx=20)
        
        # 제목
        title_label = ctk.CTkLabel(
            title_frame,
            text="프레임과 필터 선택",
            font=self.fonts["title"],
            text_color=self.colors["text"]
        )
        title_label.pack(side="left", pady=20)
        
        # 다음 버튼
        next_button = ctk.CTkButton(
            title_frame,
            text="다음",
            font=self.fonts["button"],
            fg_color=self.colors["primary"],
            hover_color=self.colors["primary_dark"],
            text_color=self.colors["text"],
            corner_radius=15,
            width=200,
            height=60,
            command=self.show_printing_screen
        )
        next_button.pack(side="right", pady=20)

        # 중앙 컨테이너
        center_container = ctk.CTkFrame(container, fg_color="transparent")
        center_container.pack(fill="both", expand=True, padx=20, pady=20)

        # 왼쪽 패널 (프레임/필터 선택)
        left_panel = ctk.CTkFrame(center_container, fg_color=self.colors["surface"], corner_radius=15)
        left_panel.pack(side="left", fill="both", expand=True, padx=(0, 10))

        # 탭 뷰
        self.tab_view = ctk.CTkTabview(left_panel, fg_color="transparent")
        self.tab_view.pack(fill="both", expand=True, padx=10, pady=10)

        # 탭 추가
        self.tab_view.add("프레임")
        self.tab_view.add("필터")

        # 탭 컨텐츠
        self.tab_content = self.tab_view.tab("프레임")

        # 오른쪽 패널 (미리보기)
        self.preview_panel = ctk.CTkFrame(center_container, fg_color=self.colors["surface"], corner_radius=15)
        self.preview_panel.pack(side="right", fill="both", expand=True, padx=(10, 0))

        # 선택 정보 표시
        self.selection_info = ctk.CTkLabel(
            self.preview_panel,
            text="선택: 기본 프레임 / 필터: 없음",
            font=self.fonts["body"],
            text_color=self.colors["text_secondary"]
        )
        self.selection_info.pack(pady=10)

        # 선택된 사진 개수 표시
        self.selection_count_label = ctk.CTkLabel(
            self.preview_panel,
            text=f"선택된 사진: {len(self.selected_indices)}/{self.config.selected_photos}",
            font=self.fonts["body"],
            text_color=self.colors["text_secondary"]
        )
        self.selection_count_label.pack(pady=5)

        # 프레임 탭 표시
        self.show_frame_tab()
        
        # 미리보기 업데이트
        self.update_frame_preview()

    def toggle_photo_selection(self, index):
        """사진 선택/해제"""
        button = None
        for widget in self.photo_frame.winfo_children():
            if hasattr(widget, 'photo_index') and widget.photo_index == index:
                button = widget
                break

        if index in self.selected_indices:
            self.selected_indices.remove(index)
            if button:
                button.configure(fg_color=self.colors["surface"], border_color=self.colors["border"])
        else:
            if len(self.selected_indices) < self.config.selected_photos:
                self.selected_indices.append(index)
                if button:
                    button.configure(fg_color=self.colors["primary"], border_color=self.colors["primary_dark"])
            else:
                # 최대 선택 수 초과 시 알림
                self.show_notification(f"최대 {self.config.selected_photos}장만 선택할 수 있습니다.")

        # 선택된 사진 개수 업데이트
        self.selection_count_label.configure(
            text=f"선택된 사진: {len(self.selected_indices)}/{self.config.selected_photos}"
        )

        # 미리보기 업데이트
        self.update_frame_preview()

    def update_frame_preview(self):
        """프레임 미리보기 업데이트"""
        try:
            # 기존 위젯 정리
            for widget in self.preview_panel.winfo_children():
                widget.destroy()

            # 선택 정보 표시
            self.selection_info = ctk.CTkLabel(
                self.preview_panel,
                text=f"선택: {os.path.splitext(os.path.basename(self.get_current_frame_path()))[0]} / 필터: {self.current_filter}",
                font=self.fonts["body"],
                text_color=self.colors["text_secondary"]
            )
            self.selection_info.pack(pady=10)

            # 선택된 사진 개수 표시
            self.selection_count_label = ctk.CTkLabel(
                self.preview_panel,
                text=f"선택된 사진: {len(self.selected_indices)}/{self.config.selected_photos}",
                font=self.fonts["body"],
                text_color=self.colors["text_secondary"]
            )
            self.selection_count_label.pack(pady=5)

            # 미리보기 이미지 생성
            preview_img = self.create_preview_image()
            if preview_img:
                # 이미지 레이블 생성 및 이미지 참조 유지
                self.preview_image_label = ctk.CTkLabel(self.preview_panel, text="")
                self.preview_image_label.pack(pady=10)
                self.preview_image_label.configure(image=preview_img)
                self.preview_image_label.image = preview_img  # 이미지 참조 유지

                # QR 코드가 이미 생성되어 있으면 표시
                if hasattr(self, 'qr_image') and self.qr_image:
                    # QR 코드 레이블 생성 및 이미지 참조 유지
                    self.qr_image_label = ctk.CTkLabel(self.preview_panel, text="")
                    self.qr_image_label.pack(pady=10)
                    self.qr_image_label.configure(image=self.qr_image)
                    self.qr_image_label.image = self.qr_image  # 이미지 참조 유지

        except Exception as e:
            print(f"미리보기 업데이트 오류: {e}")
            self.show_error(f"미리보기 업데이트 오류: {e}")

    def show_frame_tab(self):
        """프레임 선택 탭 표시"""
        # 탭 컨텐츠 초기화
        for widget in self.tab_content.winfo_children():
            widget.destroy()
            
        # 프레임 선택 스크롤 영역
        frame_scroll = ctk.CTkScrollableFrame(self.tab_content, fg_color="transparent")
        frame_scroll.pack(fill="both", expand=True)
        
        # frames 디렉토리에서 모든 프레임 파일 로드
        frames_dir = "frames"
        frame_files = [f for f in os.listdir(frames_dir) if f.endswith(('.png', '.jpg', '.jpeg'))]
        
        if not frame_files:
            # 프레임이 없는 경우 기본 프레임 생성
            self.create_colored_frames()
            frame_files = [f for f in os.listdir(frames_dir) if f.endswith(('.png', '.jpg', '.jpeg'))]
        
        # 프레임 옵션들
        for i, frame_file in enumerate(frame_files):
            try:
                frame_path = os.path.join(frames_dir, frame_file)
                frame_img = Image.open(frame_path)
                frame_img = frame_img.resize((180, 270), Image.LANCZOS)
                frame_photo = ctk.CTkImage(
                    light_image=frame_img,
                    dark_image=frame_img,
                    size=(180, 270)
                )
                
                # 파일명에서 확장자 제거
                frame_name = os.path.splitext(frame_file)[0]
                
                # 프레임 버튼
                frame_button = ctk.CTkButton(
                    frame_scroll,
                    text=frame_name,
                    image=frame_photo,
                    compound="top",
                    font=self.fonts["body"],
                    fg_color=self.colors["primary"] if frame_path == self.get_current_frame_path() else self.colors["secondary"],
                    text_color=self.colors["text"],
                    hover_color=self.colors["primary_dark"],
                    corner_radius=10,
                    width=200,
                    height=300,
                    command=lambda path=frame_path: self.select_frame_by_path(path)
                )
                frame_button.image = frame_photo
                frame_button.grid(row=i//3, column=i%3, padx=5, pady=5, sticky="nsew")
            except Exception as e:
                print(f"프레임 {frame_file} 로드 오류: {e}")
                
        # 그리드 설정
        frame_scroll.grid_columnconfigure(0, weight=1)
        frame_scroll.grid_columnconfigure(1, weight=1)
        frame_scroll.grid_columnconfigure(2, weight=1)

    def show_filter_tab(self):
        """필터 선택 탭 표시"""
        # 탭 컨텐츠 초기화
        for widget in self.tab_content.winfo_children():
            widget.destroy()
        
        # 필터 선택 스크롤 영역
        filter_scroll = ctk.CTkScrollableFrame(self.tab_content, fg_color="transparent")
        filter_scroll.pack(fill="both", expand=True)
        
        # 필터 옵션들
        filters = [
            ("none", "원본"),
            ("grayscale", "흑백"),
            ("sepia", "세피아"),
            ("warm", "따뜻한 톤"),
            ("cool", "차가운 톤"),
            ("vintage", "빈티지"),
            ("boost", "선명하게"),
            ("soft", "부드럽게")
        ]
        
        for i, (filter_id, filter_name) in enumerate(filters):
            try:
                filter_button = ctk.CTkButton(
                    filter_scroll,
                    text=filter_name,
                    font=self.fonts["body"],
                    fg_color=self.colors["primary"] if filter_id == self.current_filter else self.colors["secondary"],
                    text_color=self.colors["text"],
                    hover_color=self.colors["primary_dark"],
                    corner_radius=10,
                    width=200,
                    height=100,
                    command=lambda f_id=filter_id: self.select_filter(f_id)
                )
                filter_button.grid(row=i//3, column=i%3, padx=5, pady=5, sticky="nsew")
            except Exception as e:
                print(f"필터 {filter_id} 로드 오류: {e}")
                
        # 그리드 설정
        filter_scroll.grid_columnconfigure(0, weight=1)
        filter_scroll.grid_columnconfigure(1, weight=1)
        filter_scroll.grid_columnconfigure(2, weight=1)

    def select_frame_by_path(self, frame_path):
        """프레임 선택"""
        try:
            self.current_frame_index = self.frames.index(frame_path)
            self.config.frame_path = frame_path
            
            # 선택 정보 업데이트
            frame_name = os.path.basename(frame_path).replace(".png", "")
            self.selection_info.configure(
                text=f"선택: {frame_name} / 필터: {self.current_filter}"
            )
            
            # 미리보기 업데이트
            self.update_frame_preview()
        except Exception as e:
            print(f"프레임 선택 오류: {e}")

    def select_filter(self, filter_id):
        """필터 선택"""
        try:
            self.current_filter = filter_id
            
            # 선택 정보 업데이트
            frame_name = os.path.basename(self.get_current_frame_path()).replace(".png", "")
            self.selection_info.configure(
                text=f"선택: {frame_name} / 필터: {filter_id}"
            )
            
            # 미리보기 업데이트
            self.update_frame_preview()
        except Exception as e:
            print(f"필터 선택 오류: {e}")

    def update_combined_preview(self):
        """프레임과 필터가 적용된 미리보기 업데이트"""
        # 미리보기 패널 초기화
        for widget in self.preview_panel.winfo_children():
            widget.destroy()
            
        if not self.selected_indices:
            # 선택된 사진이 없으면 안내 메시지 표시
            preview_label = ctk.CTkLabel(
                self.preview_panel,
                text="미리보기를 표시할 수 없습니다",
                font=self.fonts["body"]
            )
            preview_label.pack(fill="both", expand=True)
            return
            
        try:
            # 프레임 이미지 로드
            frame_path = self.get_current_frame_path()
            frame_img = Image.open(frame_path).convert("RGBA")
            
            # 미리보기 크기 증가
            preview_width = 600  # 400에서 600으로 증가
            preview_height = 900  # 600에서 900으로 증가
            frame_img = frame_img.resize((preview_width, preview_height), Image.LANCZOS)
            
            # 선택된 사진들 배치
            for i, idx in enumerate(self.selected_indices):
                if i >= self.config.selected_photos:
                    break
                    
                try:
                    # 사진 로드
                    photo_img = Image.open(self.photos[idx])
                    
                    # 필터 적용
                    photo_img = self.apply_filter(photo_img, self.current_filter)
                    
                    # 프레임 설정에 따라 위치 및 크기 조정
                    pos = self.config.frame_config["photo_positions"][i]
                    scale_x = preview_width / self.config.output_width
                    scale_y = preview_height / self.config.output_height
                    photo_width = int(pos["width"] * scale_x)
                    photo_height = int(pos["height"] * scale_y)
                    photo_x = int(pos["x"] * scale_x)
                    photo_y = int(pos["y"] * scale_y)
                    
                    # 사진 리사이징 및 합성
                    photo_img = photo_img.resize((photo_width, photo_height), Image.LANCZOS)
                    frame_img.paste(photo_img, (photo_x, photo_y))
                except Exception as e:
                    print(f"미리보기 사진 {i} 처리 오류: {e}")
            
            # QR 코드 생성 및 배치
            qr_code = self.generate_qr_code()
            if qr_code:
                qr_size = int(self.config.qr_size * (preview_width / self.config.output_width))
                qr_code = qr_code.resize((qr_size, qr_size), Image.LANCZOS)
                qr_x = preview_width - qr_size - 100
                qr_y = 20
                frame_img.paste(qr_code, (qr_x, qr_y))
            
            # CTkImage로 변환
            preview_photo = ctk.CTkImage(
                light_image=frame_img,
                dark_image=frame_img,
                size=(preview_width, preview_height)
            )
            
            # 미리보기 표시
            preview_label = ctk.CTkLabel(
                self.preview_panel,
                text="",
                image=preview_photo
            )
            preview_label.image = preview_photo
            preview_label.pack(fill="both", expand=True)
        except Exception as e:
            print(f"미리보기 업데이트 오류: {e}")
            error_label = ctk.CTkLabel(
                self.preview_panel,
                text=f"미리보기 오류: {str(e)}",
                font=self.fonts["body"]
            )
            error_label.pack(fill="both", expand=True)

    def apply_filter(self, img, filter_id):
        """이미지에 필터 적용"""
        try:
            # 이미지가 경로인 경우 로드
            if isinstance(img, str):
                original_img = Image.open(img)
            else:
                # 항상 복사본을 사용하여 원본 이미지 보존
                original_img = img.copy()
            
            # 캐시 키 생성
            if hasattr(img, 'filename'):
                cache_key = f"{img.filename}_{filter_id}"
            else:
                cache_key = f"{id(original_img)}_{filter_id}"            
            # 캐시에 있으면 반환
            if cache_key in self.filter_cache:
                return self.filter_cache[cache_key].copy()  # 복사본 반환    
                
            # 필터 적용
            if filter_id == "none":
                filtered = original_img  # 원본
            elif filter_id == "grayscale":
                filtered = original_img.convert("L").convert("RGB")
            elif filter_id == "sepia":
                # 세피아 필터
                gray = original_img.convert("L")
                sepia = Image.new("RGB", img.size, (255, 240, 192))
                sepia.paste(gray, mask=gray)
                filtered = sepia
            elif filter_id == "warm":
                # 따뜻한 톤
                r, g, b = original_img.split()
                r = ImageEnhance.Brightness(r).enhance(1.1)
                g = ImageEnhance.Brightness(g).enhance(0.9)
                b = ImageEnhance.Brightness(b).enhance(0.8)
                filtered = Image.merge("RGB", (r, g, b))
            elif filter_id == "cool":
                # 차가운 톤
                r, g, b = original_img.split()
                r = ImageEnhance.Brightness(r).enhance(0.8)
                g = ImageEnhance.Brightness(g).enhance(0.9)
                b = ImageEnhance.Brightness(b).enhance(1.1)
                filtered = Image.merge("RGB", (r, g, b))
            elif filter_id == "vintage":
                # 빈티지 필터
                r, g, b = original_img.split()
                r = ImageEnhance.Brightness(r).enhance(1.2)
                g = ImageEnhance.Brightness(g).enhance(0.8)
                b = ImageEnhance.Brightness(b).enhance(0.8)
                contrast = ImageEnhance.Contrast(Image.merge("RGB", (r, g, b))).enhance(0.8)
                filtered = contrast
            elif filter_id == "boost":
                # 선명하게
                contrast = ImageEnhance.Contrast(original_img).enhance(1.2)
                filtered = ImageEnhance.Color(contrast).enhance(1.2)
            elif filter_id == "soft":
                # 부드럽게
                contrast = ImageEnhance.Contrast(original_img).enhance(0.9)
                filtered = ImageEnhance.Color(contrast).enhance(0.8)
            else:
                filtered = img  # 기본값
                
            # 캐시에 저장
            self.filter_cache[cache_key] = filtered.copy()
            
            return filtered
        except Exception as e:
            print(f"필터 적용 오류: {e}")
            return img.copy()  # 오류 시 원본 반환

    def show_printing_screen(self):
        """인쇄 진행 화면"""
        # 기존 위젯 정리
        for widget in self.main_frame.winfo_children():
            widget.destroy()
            
        # 배경 설정
        self.main_frame.configure(fg_color=self.colors["background"])
        
        # 중앙 패널
        center_panel = ctk.CTkFrame(self.main_frame, fg_color=self.colors["surface"], corner_radius=15)
        center_panel.pack(fill="both", expand=True, padx=40, pady=40)
        
        # 인쇄 중 메시지
        printing_label = ctk.CTkLabel(
            center_panel,
            text="이미지 처리 중...",
            font=self.fonts["title"],
            text_color=self.colors["text"]
        )
        printing_label.pack(pady=(50, 30))
        
        # 진행 상태 바
        progress_bar = ctk.CTkProgressBar(center_panel, width=400)
        progress_bar.pack(pady=20)
        progress_bar.set(0)
        
        # 처리 상태 레이블
        status_label = ctk.CTkLabel(
            center_panel,
            text="이미지를 생성하는 중...",
            font=self.fonts["body"],
            text_color=self.colors["text_secondary"]
        )
        status_label.pack(pady=10)
        
        # 최종 이미지 생성
        final_image = self.generate_final_image()
        
        # QR 코드 표시 프레임
        qr_frame = ctk.CTkFrame(center_panel, fg_color=self.colors["background"], corner_radius=10)
        qr_frame.pack(pady=20)
        
        # QR 코드 생성 및 표시
        status_label.configure(text="QR 코드 생성 중...")
        qr_code = self.generate_qr_code()
        if qr_code:
            # QR 코드 크기를 더 크게 설정 (300x300)
            qr_size = 300
            qr_code = ctk.CTkImage(
                light_image=qr_code._light_image,
                dark_image=qr_code._dark_image,
                size=(qr_size, qr_size)
            )
            
            # QR 코드 안내 텍스트
            qr_text = ctk.CTkLabel(
                qr_frame,
                text="QR 코드를 스캔하여 사진을 다운로드하세요",
                font=self.fonts["body"],
                text_color=self.colors["text"]
            )
            qr_text.pack(pady=(20, 10))
            
            # QR 코드 이미지
            qr_label = ctk.CTkLabel(qr_frame, text="", image=qr_code)
            qr_label.image = qr_code  # 이미지 참조 유지
            qr_label.pack(pady=10)
            
            # QR 코드 URL 표시
            qr_url = f"https://{self.ngrok_domain}/photo/{self.session_hash}"
            url_label = ctk.CTkLabel(
                qr_frame,
                text=qr_url,
                font=self.fonts["small"],
                text_color=self.colors["text_secondary"]
            )
            url_label.pack(pady=5)
        else:
            # QR 코드 생성 실패 시 메시지
            error_text = ctk.CTkLabel(
                qr_frame,
                text="QR 코드를 생성할 수 없습니다.",
                font=self.fonts["body"],
                text_color=self.colors["text"]
            )
            error_text.pack(pady=10)
        
        # 처리 완료 표시
        status_label.configure(text="모든 처리가 완료되었습니다!")
        
        # 처음으로 돌아가기 버튼
        home_button = ctk.CTkButton(
            center_panel,
            text="처음으로",
            font=self.fonts["button"],
            fg_color=self.colors["primary"],
            hover_color=self.colors["primary_dark"],
            text_color=self.colors["text"],
            corner_radius=15,
            width=200,
            height=60,
            command=self.restart_app  # 여기를 setup_start_screen에서 restart_app으로 변경
        )
        home_button.pack(pady=30)
        
        # 진행 상태 업데이트 (시뮬레이션)
        self.simulate_printing_progress(progress_bar)

    def simulate_printing_progress(self, progress_bar):
        """인쇄 진행 상태 시뮬레이션"""
        def update_progress(value):
            progress_bar.set(value)
            if value < 1.0:
                # 0.05초마다 5%씩 증가
                self.root.after(50, update_progress, value + 0.05)
            else:
                # 진행바가 100%에 도달하면 90초 후 자동으로 처음 화면으로 돌아감
                self.root.after(90000, self.restart_app)
                
        update_progress(0.0)

    def restart_app(self):
        """앱을 재시작하여 처음부터 다시 시작"""
        try:
            print("앱 재시작 시작...")
            
            # 카메라 리소스 정리
            if self.camera is not None:
                print("카메라 자원 해제 중...")
                self.camera.release()
                self.camera = None
            
            # 스레드 종료 확인
            self.running = False
            self.preview_running = False
            
            if hasattr(self, 'preview_thread') and self.preview_thread and self.preview_thread.is_alive():
                self.preview_thread.join(timeout=1)
                
            for thread in self.threads:
                if thread.is_alive():
                    thread.join(timeout=1)
            
            # 큐 비우기
            while not self.capture_queue.empty():
                try:
                    self.capture_queue.get_nowait()
                except:
                    pass
                    
            while not self.preview_queue.empty():
                try:
                    self.preview_queue.get_nowait()
                except:
                    pass
            
            # 기존 세션 정보 초기화
            self.photos = []
            self.selected_indices = []
            self.photos_taken = False
            self.current_photo_index = 0
            self.capture_in_progress = False
            self.timer_running = False
            self.current_filter = "none"
            self.camera_initialized = False  # 카메라 초기화 상태 재설정
            
            # 캐시 정리
            self.image_cache = {}
            self.filter_cache = {}
            
            # 프레임 버퍼 초기화
            self.frame_buffer = FrameBuffer(self.config.frame_buffer_size)
            
            # 메인 화면으로 돌아가기
            print("메인 화면으로 돌아갑니다...")
            self.setup_start_screen()
            
            print("앱이 성공적으로 재시작되었습니다.")
        except Exception as e:
            print(f"앱 재시작 중 오류 발생: {e}")
            self.show_error(f"오류: {e}")

    def generate_final_image(self):
        """최종 이미지 생성 및 저장"""
        try:
            # 프레임 이미지 로드
            frame_path = self.get_current_frame_path()
            if not frame_path or not os.path.exists(frame_path):
                raise Exception("프레임 이미지를 찾을 수 없습니다.")
            
            # PIL Image로 로드 및 크기 조정
            frame_img = Image.open(frame_path).convert("RGBA")
            frame_img = frame_img.resize((self.config.output_width, self.config.output_height), Image.LANCZOS)
            
            # 선택된 사진들 배치
            for i, idx in enumerate(self.selected_indices):
                if i >= self.config.selected_photos:
                    break
                    
                try:
                    # 사진 로드 및 크기 조정 (PIL Image 단계)
                    photo_img = Image.open(self.photos[idx])
                    photo_img = self.apply_filter(photo_img, self.current_filter)
                    
                    # 프레임 설정에 따라 위치 및 크기 조정
                    pos = self.config.frame_config["photo_positions"][i]
                    photo_width = pos["width"]
                    photo_height = pos["height"]
                    photo_x = pos["x"]
                    photo_y = pos["y"]
                    
                    # PIL Image 단계에서 리사이징
                    photo_img = photo_img.resize((photo_width, photo_height), Image.LANCZOS)
                    frame_img.paste(photo_img, (photo_x, photo_y))
                except Exception as e:
                    print(f"최종 이미지 사진 {i} 처리 오류: {e}")
                    raise
            
            # QR 코드 추가
            if hasattr(self, 'qr_image') and self.qr_image is not None:
                try:
                    # QR 코드 PIL 이미지 가져오기
                    qr_path = os.path.join(tempfile.gettempdir(), f"qr_{self.session_hash}.png")
                    if os.path.exists(qr_path):
                        qr_img = Image.open(qr_path)
                        qr_size = self.config.qr_size
                        qr_img = qr_img.resize((qr_size, qr_size), Image.LANCZOS)
                        qr_x = self.config.frame_config["qr_position"]["x"]
                        qr_y = self.config.frame_config["qr_position"]["y"]
                        frame_img.paste(qr_img, (qr_x, qr_y))
                except Exception as e:
                    print(f"QR 코드 추가 오류: {e}")
            
            # output 디렉토리 생성
            output_dir = "output"
            os.makedirs(output_dir, exist_ok=True)
            
            # 세션 ID 추출 (폴더명에서 숫자만 추출)
            session_id = ''.join(filter(str.isdigit, os.path.basename(self.session_folder)))
            
            # 최종 이미지 저장 (output 디렉토리에 저장)
            output_path = os.path.join(output_dir, f"session_{session_id}_final.png")
            frame_img.save(output_path, "PNG")
            print(f"최종 이미지 저장 완료: {output_path}")
            
            # 세션 해시 업데이트 (서버와 일치하도록)
            self.session_hash = hashlib.md5(session_id.encode()).hexdigest()[:12]
            
            return output_path
            
        except Exception as e:
            print(f"최종 이미지 생성 오류: {e}")
            self.show_error(f"최종 이미지 생성 중 오류가 발생했습니다: {str(e)}")
            return None

    def print_image(self, image_path):
        """이미지 인쇄"""
        try:
            printer = KodakPrinter(self.config.printer_name)
            success = printer.print_image(image_path)
            if success:
                print("인쇄 작업이 전송되었습니다.")
            else:
                print("인쇄 작업 전송 실패")
        except Exception as e:
            print(f"인쇄 오류: {e}")

    def show_printer_settings(self):
        """프린터 설정 화면"""
        # 기존 위젯 정리
        for widget in self.main_frame.winfo_children():
            widget.destroy()
            
        # 배경 설정
        self.main_frame.configure(fg_color=self.colors["background"])
        
        # 제목 패널
        header_panel = ctk.CTkFrame(self.main_frame, fg_color=self.colors["primary"], corner_radius=0, height=100)
        header_panel.pack(fill="x", side="top")
        title_label = ctk.CTkLabel(
            header_panel,
            text="프린터 설정",
            font=self.fonts["title"],
            text_color=self.colors["text"]
        )
        title_label.pack(pady=30)
        
        # 설정 패널
        settings_panel = ctk.CTkFrame(self.main_frame, fg_color=self.colors["surface"], corner_radius=15)
        settings_panel.pack(fill="both", expand=True, padx=40, pady=40)
        
        # 프린터 목록 가져오기
        printers = self.get_available_printers()
        
        # 프린터 선택 영역
        printer_label = ctk.CTkLabel(
            settings_panel,
            text="사용할 프린터 선택",
            font=self.fonts["subtitle"],
            text_color=self.colors["text"]
        )
        printer_label.pack(pady=(30, 20))
        
        # 프린터 목록
        for printer in printers:
            printer_button = ctk.CTkButton(
                settings_panel,
                text=printer,
                font=self.fonts["body"],
                fg_color=self.colors["primary"] if printer == self.config.printer_name else self.colors["secondary"],
                text_color=self.colors["text"],
                hover_color=self.colors["primary_dark"],
                corner_radius=15,
                width=400,
                height=50,
                command=lambda p=printer: self.select_printer(p)
            )
            printer_button.pack(pady=5)
        
        # 뒤로 가기 버튼
        back_button = ctk.CTkButton(
            settings_panel,
            text="뒤로 가기",
            font=self.fonts["button"],
            fg_color=self.colors["secondary"],
            text_color=self.colors["text"],
            hover_color="#333333",
            corner_radius=15,
            width=200,
            height=60,
            command=self.setup_start_screen
        )
        back_button.pack(pady=30)

    def get_available_printers(self):
        """사용 가능한 프린터 목록 가져오기"""
        try:
            if os.name == 'nt':  # Windows
                printer_info = subprocess.check_output(
                    'wmic printer get name', shell=True).decode('utf-8')
                printers = [p.strip() for p in printer_info.split('\n') if p.strip() and p.strip() != 'Name']
                return printers
            else:  # macOS/Linux
                return ["Default Printer"]
        except Exception as e:
            print(f"프린터 목록 가져오기 오류: {e}")
            return ["Microsoft Print to PDF"]

    def select_printer(self, printer_name):
        """프린터 선택"""
        self.config.printer_name = printer_name
        self.show_notification(f"프린터 '{printer_name}'이(가) 선택되었습니다.")
        self.show_printer_settings()  # 화면 갱신

    def show_notification(self, message):
        """알림 메시지 표시"""
        notification = ctk.CTkToplevel(self.root)
        notification.title("알림")
        notification.geometry("400x200")
        notification.resizable(False, False)
        notification.configure(fg_color=self.colors["surface"])
        notification.transient(self.root)
        notification.grab_set()
        
        # 중앙 정렬
        notification.update_idletasks()
        width = notification.winfo_width()
        height = notification.winfo_height()
        x = (notification.winfo_screenwidth() // 2) - (width // 2)
        y = (notification.winfo_screenheight() // 2) - (height // 2)
        notification.geometry(f"{width}x{height}+{x}+{y}")
        
        # 메시지 표시
        message_label = ctk.CTkLabel(
            notification,
            text=message,
            font=self.fonts["body"],
            text_color=self.colors["text"],
            wraplength=350
        )
        message_label.pack(pady=(50, 30))
        
        # 확인 버튼
        ok_button = ctk.CTkButton(
            notification,
            text="확인",
            font=self.fonts["button"],
            fg_color=self.colors["primary"],
            hover_color=self.colors["primary_dark"],
            text_color=self.colors["text"],
            corner_radius=15,
            width=100,
            height=40,
            command=notification.destroy
        )
        ok_button.pack(pady=10)
        
        # 3초 후 자동 닫기
        notification.after(3000, notification.destroy)

    def show_error(self, message):
        """오류 메시지 표시"""
        error_window = ctk.CTkToplevel(self.root)
        error_window.title("오류")
        error_window.geometry("400x200")
        error_window.resizable(False, False)
        error_window.configure(fg_color=self.colors["surface"])
        error_window.transient(self.root)
        error_window.grab_set()
        
        # 중앙 정렬
        error_window.update_idletasks()
        width = error_window.winfo_width()
        height = error_window.winfo_height()
        x = (error_window.winfo_screenwidth() // 2) - (width // 2)
        y = (error_window.winfo_screenheight() // 2) - (height // 2)
        error_window.geometry(f"{width}x{height}+{x}+{y}")
        
        # 오류 아이콘 (빨간색 원)
        canvas = ctk.CTkCanvas(error_window, width=50, height=50, bg=self.colors["surface"], highlightthickness=0)
        canvas.pack(pady=(20, 10))
        canvas.create_oval(5, 5, 45, 45, fill="#FF5252", outline="")
        canvas.create_text(25, 25, text="!", fill="white", font=("Arial", 24, "bold"))
        
        # 오류 메시지
        error_label = ctk.CTkLabel(
            error_window,
            text=message,
            font=self.fonts["body"],
            text_color=self.colors["text"],
            wraplength=350
        )
        error_label.pack(pady=10)
        
        # 확인 버튼
        ok_button = ctk.CTkButton(
            error_window,
            text="확인",
            font=self.fonts["button"],
            fg_color="#FF5252",
            hover_color="#FF3030",
            text_color=self.colors["text"],
            corner_radius=15,
            width=100,
            height=40,
            command=error_window.destroy
        )
        ok_button.pack(pady=20)

    def create_preview_image(self):
        """선택된 사진들로 미리보기 이미지 생성"""
        try:
            if not self.selected_indices:
                return None

            # 프레임 이미지 로드
            frame_path = self.get_current_frame_path()
            if not frame_path or not os.path.exists(frame_path):
                raise Exception("프레임 이미지를 찾을 수 없습니다.")
            
            frame_img = Image.open(frame_path).convert("RGBA")
            
            # 미리보기 크기 설정
            preview_width = 600
            preview_height = 900
            frame_img = frame_img.resize((preview_width, preview_height), Image.LANCZOS)
            
            # 선택된 사진들 배치
            for i, idx in enumerate(self.selected_indices):
                if i >= self.config.selected_photos:
                    break
                    
                try:
                    # 사진 로드
                    photo_img = Image.open(self.photos[idx])
                    
                    # 필터 적용
                    photo_img = self.apply_filter(photo_img, self.current_filter)
                    
                    # 프레임 설정에 따라 위치 및 크기 조정
                    pos = self.config.frame_config["photo_positions"][i]
                    scale_x = preview_width / self.config.output_width
                    scale_y = preview_height / self.config.output_height
                    photo_width = int(pos["width"] * scale_x)
                    photo_height = int(pos["height"] * scale_y)
                    photo_x = int(pos["x"] * scale_x)
                    photo_y = int(pos["y"] * scale_y)
                    
                    # 사진 리사이징 및 합성
                    photo_img = photo_img.resize((photo_width, photo_height), Image.LANCZOS)
                    frame_img.paste(photo_img, (photo_x, photo_y))
                except Exception as e:
                    print(f"미리보기 사진 {i} 처리 오류: {e}")
            
            # QR 코드 배치는 생략 (이미 생성된 QR 코드를 별도로 표시)
            
            # CTkImage로 변환하고 참조 유지
            preview_image = ctk.CTkImage(
                light_image=frame_img,
                dark_image=frame_img,
                size=(preview_width, preview_height)
            )
            
            # 클래스 인스턴스 변수로 저장하여 참조 유지
            self.current_preview_image = preview_image
            return preview_image
            
        except Exception as e:
            print(f"미리보기 이미지 생성 오류: {e}")
            return None

    def show_processing_screen(self):
        """이미지 처리 중 화면 표시"""
        try:
            # 기존 위젯 제거
            for widget in self.root.winfo_children():
                widget.destroy()
            
            # 메인 프레임
            main_frame = ctk.CTkFrame(self.root)
            main_frame.pack(expand=True, fill="both", padx=20, pady=20)
            
            # 로딩 메시지
            loading_label = ctk.CTkLabel(
                main_frame,
                text="이미지 처리 중입니다...",
                font=("Arial", 24, "bold")
            )
            loading_label.pack(pady=20)
            
            # 프로그레스 바
            progress = ctk.CTkProgressBar(main_frame)
            progress.pack(pady=20, padx=40, fill="x")
            progress.set(0)
            
            # QR 코드 생성
            qr_code = self.generate_qr_code()
            if qr_code:
                # QR 코드 크기를 더 크게 설정 (300x300)
                qr_size = 300
                qr_code = ctk.CTkImage(
                    light_image=qr_code._light_image,
                    dark_image=qr_code._dark_image,
                    size=(qr_size, qr_size)
                )
                
                # QR 코드 라벨
                qr_label = ctk.CTkLabel(
                    main_frame,
                    text="QR 코드를 스캔하여 사진을 확인하세요",
                    font=("Arial", 16)
                )
                qr_label.pack(pady=(20, 10))
                
                # QR 코드 이미지
                qr_image_label = ctk.CTkLabel(
                    main_frame,
                    image=qr_code,
                    text=""
                )
                qr_image_label.pack(pady=10)
            
            # 처음으로 돌아가기 버튼
            back_button = ctk.CTkButton(
                main_frame,
                text="처음으로 돌아가기",
                command=self.reset_app,
                font=("Arial", 16, "bold"),
                height=40
            )
            back_button.pack(pady=20)
            
            # 프로그레스 바 애니메이션
            def update_progress():
                current = progress.get()
                if current < 0.9:  # 90%까지만 진행
                    progress.set(current + 0.1)
                    self.root.after(500, update_progress)
            
            update_progress()
            
            # 이미지 처리 시작
            self.root.after(100, self.process_images)
            
        except Exception as e:
            print(f"처리 화면 표시 오류: {e}")
            self.show_error(f"처리 화면을 표시할 수 없습니다: {str(e)}")
            self.reset_app()

    def reset_app(self):
        """앱을 초기 상태로 리셋"""
        try:
            # 모든 위젯 제거
            for widget in self.root.winfo_children():
                widget.destroy()
            
            # 세션 초기화
            self.session_folder = None
            self.session_hash = None
            self.photos = []
            self.selected_indices = []
            self.current_filter = None
            self.current_frame = None
            self.camera_initialized = False  # 카메라 초기화 상태 초기화
            
            # 메인 화면 표시
            self.show_main_screen()
            
        except Exception as e:
            print(f"앱 리셋 오류: {e}")
            self.show_error(f"앱을 초기화할 수 없습니다: {str(e)}")
            # 강제 종료
            self.root.quit()

    def process_images(self):
        """선택된 사진들로 최종 이미지 생성"""
        try:
            # 처리 화면 표시
            self.show_processing_screen()
            
            # 최종 이미지 생성
            final_path = self.generate_final_image()
            if not final_path:
                raise Exception("최종 이미지 생성 실패")
            
            # 성공 메시지 표시
            self.show_success("이미지가 성공적으로 저장되었습니다!")
            
            # 잠시 대기 후 메인 화면으로
            self.root.after(2000, self.reset_app)
            
        except Exception as e:
            print(f"이미지 처리 오류: {e}")
            self.show_error(f"이미지 처리 중 오류가 발생했습니다: {str(e)}")
            self.reset_app()

    def generate_hash(self, folder_name):
        """세션 해시 생성 (server.js와 일치하도록)"""
        base = f"{folder_name}_{time.time()}_{random.randint(0,999999)}"
        return hashlib.md5(base.encode()).hexdigest()[:12]  # 12자리 해시 생성

    def initialize_camera_threads(self):
        """카메라 스레드 초기화"""
        self.running = True
        self.preview_running = True
        
        # 프리뷰 스레드 시작
        self.preview_thread = threading.Thread(target=self.preview_processing_thread)
        self.preview_thread.daemon = True
        self.preview_thread.start()
        
        # 기존 스레드들 시작
        self.threads = [
            threading.Thread(target=self.video_capture_thread),
            threading.Thread(target=self.video_processing_thread)
        ]
        for thread in self.threads:
            thread.daemon = True
            thread.start()

    def preview_processing_thread(self):
        """프리뷰 처리 스레드"""
        while self.preview_running:
            try:
                frame = self.preview_queue.get(timeout=1)
                if frame is None:
                    continue
                    
                # 16:9 비율로 크롭
                h, w = frame.shape[:2]
                target_ratio = 16/9
                current_ratio = w/h
                
                if current_ratio > target_ratio:
                    # 너무 넓은 경우
                    new_w = int(h * target_ratio)
                    start_x = (w - new_w) // 2
                    frame = frame[:, start_x:start_x+new_w]
                else:
                    # 너무 좁은 경우
                    new_h = int(w / target_ratio)
                    start_y = (h - new_h) // 2
                    frame = frame[start_y:start_y+new_h, :]
                
                # 90도 회전 및 상하반전
                frame = cv2.rotate(frame, cv2.ROTATE_90_CLOCKWISE)
                frame = cv2.flip(frame, 0)
                
                # UI 업데이트
                self.root.after(0, self.update_preview_ui, frame)
                
            except queue.Empty:
                continue
            except Exception as e:
                print(f"프리뷰 처리 중 오류: {e}")
                continue

    def update_preview_ui(self, frame=None):
        """프리뷰 UI 업데이트"""
        try:
            if frame is None:
                frame = self.frame_buffer.get_latest_frame()
                if frame is None:
                    return

            # OpenCV BGR -> RGB 변환
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            
            # PIL Image로 변환
            image = Image.fromarray(frame_rgb)
            
            # CTkImage로 변환
            photo = ctk.CTkImage(
                light_image=image,
                dark_image=image,
                size=(image.width, image.height)
            )
            
            # UI 업데이트
            if hasattr(self, 'preview_label'):
                self.preview_label.configure(image=photo)
                self.preview_label.image = photo
                
        except Exception as e:
            print(f"UI 업데이트 중 오류: {e}")

def get_local_ip():
    """내부 네트워크에서 사용 가능한 IP 주소 반환"""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(('8.8.8.8', 80))
        ip = s.getsockname()[0]
    except Exception:
        ip = '127.0.0.1'
    finally:
        s.close()
    return ip

if __name__ == "__main__":
    # 애플리케이션 시작
    root = ctk.CTk()
    app = PhotoBooth(root)
    root.mainloop()
                