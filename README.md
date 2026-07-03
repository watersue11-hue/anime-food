# AniMeal Studio (Streamlit MVP)

애니풍 음식 쇼츠를 간단하게 만드는 Streamlit 프로젝트입니다.

## 기능
- 음식 이름 입력
- 컷 수 / 컷당 길이 / 자막 위치 설정
- 기본 스토리보드 자동 생성
- 표에서 장면 제목 / 자막 / 장면 설명 직접 수정
- OpenAI 이미지 생성 또는 수동 이미지 업로드
- MP4 프리뷰 생성
- 다운로드 전에 `st.video()`로 결과 확인 가능
- 최종 mp4 다운로드

## 폴더 구조
```bash
anime_food_reel_streamlit/
├─ app.py
├─ requirements.txt
├─ README.md
├─ outputs/
└─ .streamlit/
   └─ secrets.toml.example
```

## 실행 방법
### 1) 패키지 설치
```bash
pip install -r requirements.txt
```

### 2) API 키 설정 (선택)
OpenAI로 장면 이미지를 자동 생성하려면 `.streamlit/secrets.toml` 파일을 만들고 아래처럼 입력하세요.

```toml
OPENAI_API_KEY = "sk-..."
```

API 키가 없으면 **직접 이미지 업로드 모드**만 사용하면 됩니다.

### 3) 실행
```bash
streamlit run app.py
```

## 사용 흐름
1. 음식 이름 입력
2. `기본 스토리보드 생성`
3. 필요하면 표에서 자막 / 장면 설명 수정
4. 이미지 준비 방식 선택
   - `AI로 자동 생성`
   - `내가 직접 업로드`
5. `프리뷰 영상 생성`
6. 미리보기 확인
7. `최종 mp4 다운로드`

## 주의
- AI 이미지 생성에는 비용이 들 수 있습니다.
- 처음 MVP라서 `이미지 → 영상`은 실제 비디오 생성 API가 아니라, 이미지에 줌 효과와 자막을 넣어 mp4로 합성하는 방식입니다.
- 나중에 원하면 `render_short_video()` 부분을 Runway/Luma/Kling 같은 영상 API 호출로 교체할 수 있습니다.
