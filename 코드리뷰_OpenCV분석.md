# 포토부스 시스템 코드 리뷰 - OpenCV 부분 상세 분석

## OpenCV 구현 상세 분석

### 1. 카메라 초기화 및 제어

```python
# 카메라 객체 초기화 및 해상도 설정
def initialize_camera(self):
    self.camera = cv2.VideoCapture(self.camera_port)
    self.camera.set(cv2.CAP_PROP_FRAME_WIDTH, self.camera_width)
    self.camera.set(cv2.CAP_PROP_FRAME_HEIGHT, self.camera_height)
    
    # 카메라 프레임 속도 설정 (30fps)
    self.camera.set(cv2.CAP_PROP_FPS, 30)
    
    # 자동 포커스 설정 (지원되는 카메라의 경우)
    self.camera.set(cv2.CAP_PROP_AUTOFOCUS, 1)
    
    # 카메라 초기화 확인
    if not self.camera.isOpened():
        raise Exception("카메라를 열 수 없습니다. 연결을 확인하세요.")
        
    # 처음 몇 프레임은 버림 (카메라 안정화)
    for i in range(10):
        ret, frame = self.camera.read()
```

OpenCV의 `VideoCapture` 클래스를 사용하여 카메라 장치를 초기화합니다. `CAP_PROP_*` 상수를 통해 해상도, 프레임 속도, 자동 포커스 등 다양한 카메라 속성을 제어할 수 있습니다. 카메라 안정화를 위해 처음 몇 프레임을 버리는 기법도 사용되었습니다.

### 2. 실시간 프레임 캡처 및 처리

```python
def update_preview(self):
    # 카메라에서 프레임 읽기
    ret, frame = self.camera.read()
    
    if ret:
        # 거울 모드 적용 (좌우 반전)
        if self.mirror_mode:
            frame = cv2.flip(frame, 1)
        
        # BGR에서 RGB로 색상 공간 변환 (Tkinter 호환)
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        
        # 현재 선택된 필터 적용
        if self.current_filter != "none":
            rgb_frame = self.apply_filter(rgb_frame, self.current_filter)
        
        # 현재 선택된 프레임 오버레이 적용
        if self.current_frame != "none":
            rgb_frame = self.overlay_frame(rgb_frame, self.current_frame)
        
        # 결과 이미지를 Tkinter에 표시 가능한 형식으로 변환
        img = Image.fromarray(rgb_frame)
        imgtk = ImageTk.PhotoImage(image=img)
        
        # UI 레이블 업데이트
        self.preview_label.imgtk = imgtk
        self.preview_label.config(image=imgtk)
    
    # 30ms 후 다시 호출 (약 30fps)
    self.preview_label.after(30, self.update_preview)
```

`camera.read()` 메서드로 프레임을 읽고, 다양한 OpenCV 함수를 사용하여 전처리합니다. `flip()` 함수로 거울 효과를 적용하고, `cvtColor()`로 색상 공간을 변환합니다. 최종 이미지는 PIL을 통해 Tkinter에 표시 가능한 형식으로 변환됩니다.

### 3. 필터 적용 기능 상세 분석

```python
def apply_filter(self, image, filter_type):
    # 그레이스케일 필터
    if filter_type == "grayscale":
        gray = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY)
        return cv2.cvtColor(gray, cv2.COLOR_GRAY2RGB)
    
    # 세피아 필터
    elif filter_type == "sepia":
        # 세피아 변환 행렬
        sepia_kernel = np.array([
            [0.393, 0.769, 0.189],
            [0.349, 0.686, 0.168],
            [0.272, 0.534, 0.131]
        ])
        # 행렬 변환 적용
        sepia_img = cv2.transform(np.array(image), sepia_kernel)
        # 값 범위 조정 (0-255 사이로)
        sepia_img = np.clip(sepia_img, 0, 255).astype(np.uint8)
        return sepia_img
    
    # 블러 필터
    elif filter_type == "blur":
        return cv2.GaussianBlur(image, (5, 5), 0)
    
    # 샤프닝 필터
    elif filter_type == "sharpen":
        kernel = np.array([[-1, -1, -1],
                           [-1,  9, -1],
                           [-1, -1, -1]])
        return cv2.filter2D(image, -1, kernel)
    
    # 엣지 감지 필터
    elif filter_type == "edge":
        gray = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY)
        edges = cv2.Canny(gray, 100, 200)
        return cv2.cvtColor(edges, cv2.COLOR_GRAY2RGB)
    
    # 밝기 증가 필터
    elif filter_type == "bright":
        hsv = cv2.cvtColor(image, cv2.COLOR_RGB2HSV)
        h, s, v = cv2.split(hsv)
        # 밝기 채널 증가 (최대 255까지)
        v = np.clip(v + 30, 0, 255).astype(np.uint8)
        hsv = cv2.merge((h, s, v))
        return cv2.cvtColor(hsv, cv2.COLOR_HSV2RGB)
    
    # 대비 증가 필터
    elif filter_type == "contrast":
        # CLAHE 알고리즘 적용
        lab = cv2.cvtColor(image, cv2.COLOR_RGB2LAB)
        l, a, b = cv2.split(lab)
        clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
        l = clahe.apply(l)
        lab = cv2.merge((l, a, b))
        return cv2.cvtColor(lab, cv2.COLOR_LAB2RGB)
    
    # 필터 없음
    else:
        return image
```

이 함수는 OpenCV의 다양한 이미지 처리 기능을 활용하여 여러 필터를 구현합니다:

1. **그레이스케일**: `cvtColor()` 함수로 색상 공간을 RGB→그레이→RGB로 변환
2. **세피아**: 3x3 변환 행렬을 사용하여 RGB 채널을 변환
3. **블러**: `GaussianBlur()` 함수로 가우시안 블러링 적용
4. **샤프닝**: `filter2D()` 함수와 3x3 샤프닝 커널로 이미지 선명도 증가
5. **엣지 감지**: `Canny()` 알고리즘으로 이미지의 엣지 검출
6. **밝기 증가**: HSV 색상 공간에서 V(밝기) 채널 조정
7. **대비 증가**: LAB 색상 공간과 CLAHE(Contrast Limited Adaptive Histogram Equalization) 알고리즘 적용

### 4. 프레임 오버레이 및 합성 기술

```python
def overlay_frame(self, image, frame_path):
    # 프레임 이미지 로드
    frame_img = cv2.imread(frame_path, cv2.IMREAD_UNCHANGED)
    
    if frame_img is None:
        print(f"프레임을 로드할 수 없습니다: {frame_path}")
        return image
    
    # 이미지 크기 맞추기
    frame_img = cv2.resize(frame_img, (image.shape[1], image.shape[0]))
    
    # 알파 채널이 있는 경우 (PNG 투명 배경)
    if frame_img.shape[2] == 4:
        # 알파 채널 분리
        alpha = frame_img[:, :, 3] / 255.0
        
        # 결과 이미지 생성
        result = image.copy()
        
        # 알파 블렌딩: result = (1-alpha)*image + alpha*frame
        for c in range(3):  # RGB 채널
            result[:, :, c] = (1 - alpha) * image[:, :, c] + alpha * frame_img[:, :, c]
        
        return result
    
    # 알파 채널이 없는 경우 (단순 오버레이)
    else:
        return cv2.addWeighted(image, 0.7, frame_img, 0.3, 0)
```

이 함수는 사진 위에 프레임 이미지를 합성합니다:

1. **투명 배경 처리**: PNG 이미지의 알파 채널을 활용하여 자연스러운 합성
2. **알파 블렌딩**: 각 픽셀을 알파 값에 따라 원본과 프레임 이미지 간 가중치 계산
3. **리사이징**: `resize()` 함수로 프레임 이미지를 원본 사진 크기에 맞게 조정
4. **가중치 합성**: 알파 채널이 없는 이미지는 `addWeighted()` 함수로 단순 중첩 