document.addEventListener('DOMContentLoaded', function() {
    const settingsForm = document.getElementById('settingsForm');
    const cameraSelect = document.getElementById('cameraSelect');
    const countdownTime = document.getElementById('countdownTime');
    const filterSelect = document.getElementById('filterSelect');
    const frameColorBtns = document.querySelectorAll('.frame-color-btn');

    // 설정 불러오기
    async function loadSettings() {
        try {
            const response = await fetch('/get_settings');
            const settings = await response.json();

            // 카메라 설정
            cameraSelect.value = settings.camera;

            // 카운트다운 시간 설정
            countdownTime.value = settings.countdownTime;

            // 필터 설정
            filterSelect.value = settings.filter;

            // 프레임 색상 설정
            frameColorBtns.forEach(btn => {
                if (btn.dataset.color === settings.frameColor) {
                    btn.classList.add('selected');
                }
            });
        } catch (error) {
            console.error('설정을 불러오는 중 오류 발생:', error);
            showNotification('설정을 불러오는 중 오류가 발생했습니다.', 'error');
        }
    }

    // 프레임 색상 버튼 선택 처리
    frameColorBtns.forEach(btn => {
        btn.addEventListener('click', function() {
            // 이전 선택 제거
            frameColorBtns.forEach(b => b.classList.remove('selected'));
            // 현재 버튼 선택
            this.classList.add('selected');
        });
    });

    // 설정 저장 처리
    settingsForm.addEventListener('submit', async function(e) {
        e.preventDefault();

        const settings = {
            camera: cameraSelect.value,
            countdownTime: countdownTime.value,
            frameColor: document.querySelector('.frame-color-btn.selected')?.dataset.color || 'black',
            filter: filterSelect.value
        };

        try {
            const response = await fetch('/save_settings', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(settings)
            });

            if (response.ok) {
                // 성공 메시지 표시
                showNotification('설정이 저장되었습니다.');
                // 메인 페이지로 이동
                setTimeout(() => {
                    window.location.href = '/';
                }, 1500);
            } else {
                throw new Error('설정 저장 실패');
            }
        } catch (error) {
            console.error('설정 저장 중 오류 발생:', error);
            showNotification('설정 저장 중 오류가 발생했습니다.', 'error');
        }
    });

    // 알림 표시 함수
    function showNotification(message, type = 'success') {
        const notification = document.createElement('div');
        notification.className = `fixed top-4 right-4 p-4 rounded-lg shadow-lg ${
            type === 'success' ? 'bg-green-500' : 'bg-red-500'
        } text-white`;
        notification.textContent = message;

        document.body.appendChild(notification);

        // 3초 후 알림 제거
        setTimeout(() => {
            notification.remove();
        }, 3000);
    }

    // 페이지 로드 시 설정 불러오기
    loadSettings();
}); 