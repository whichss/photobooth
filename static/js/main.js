document.addEventListener('DOMContentLoaded', function() {
    const captureBtn = document.getElementById('captureBtn');
    const capturedPhotos = document.getElementById('capturedPhotos');
    let countdownInterval;
    let countdownValue = 5;

    // 설정 불러오기
    async function loadSettings() {
        try {
            const response = await fetch('/get_settings');
            const settings = await response.json();
            countdownValue = parseInt(settings.countdownTime);
        } catch (error) {
            console.error('설정을 불러오는 중 오류 발생:', error);
        }
    }

    // 카운트다운 표시 함수
    function showCountdown() {
        const countdownDiv = document.createElement('div');
        countdownDiv.className = 'countdown';
        countdownDiv.textContent = countdownValue;
        document.querySelector('.camera-preview').appendChild(countdownDiv);

        countdownInterval = setInterval(() => {
            countdownValue--;
            countdownDiv.textContent = countdownValue;

            if (countdownValue <= 0) {
                clearInterval(countdownInterval);
                countdownDiv.remove();
                capturePhoto();
                loadSettings(); // 카운트다운 초기화를 위해 설정 다시 불러오기
            }
        }, 1000);
    }

    // 사진 촬영 함수
    async function capturePhoto() {
        try {
            const response = await fetch('/capture', {
                method: 'POST'
            });
            const data = await response.json();

            if (data.success) {
                // 촬영된 사진 표시
                const photoDiv = document.createElement('div');
                photoDiv.className = 'captured-photo scale-in';
                
                const img = document.createElement('img');
                img.src = data.filename;
                img.alt = '촬영된 사진';
                
                photoDiv.appendChild(img);
                capturedPhotos.insertBefore(photoDiv, capturedPhotos.firstChild);

                // 최대 6장까지만 표시
                if (capturedPhotos.children.length > 6) {
                    capturedPhotos.removeChild(capturedPhotos.lastChild);
                }
            }
        } catch (error) {
            console.error('사진 촬영 중 오류 발생:', error);
        }
    }

    // 촬영 버튼 클릭 이벤트
    captureBtn.addEventListener('click', function() {
        if (!countdownInterval) {
            showCountdown();
        }
    });

    // 페이지 로드 시 설정 불러오기
    loadSettings();
}); 