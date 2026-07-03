import base64
import os
import re
import time
from pathlib import Path

import imageio.v2 as imageio
import numpy as np
import streamlit as st
from PIL import Image, ImageDraw, ImageFont

try:
    from openai import OpenAI
except Exception:
    OpenAI = None

# -----------------------------
# App config
# -----------------------------
st.set_page_config(
    page_title="AniMeal Studio",
    page_icon="🍤",
    layout="wide"
)

WIDTH, HEIGHT = 1080, 1920
FPS = 24
APP_DIR = Path(__file__).parent
OUTPUT_DIR = APP_DIR / "outputs"
OUTPUT_DIR.mkdir(exist_ok=True)


# -----------------------------
# Helpers
# -----------------------------
def sanitize_filename(text: str) -> str:
    text = re.sub(r"[\\/:*?\"<>|]", "", text)
    text = re.sub(r"\s+", "_", text.strip())
    return text[:80] or "video"


@st.cache_resource
def get_client(api_key: str):
    if OpenAI is None:
        raise RuntimeError("openai 패키지가 설치되지 않았습니다.")
    return OpenAI(api_key=api_key)


def get_api_key() -> str:
    if st.session_state.get("manual_api_key"):
        return st.session_state["manual_api_key"]
    if "OPENAI_API_KEY" in st.secrets:
        return st.secrets["OPENAI_API_KEY"]
    return ""


def get_font(size=56):
    font_candidates = [
        "/System/Library/Fonts/AppleSDGothicNeo.ttc",
        "/System/Library/Fonts/AppleSDGothicNeoB.ttc",
        "C:/Windows/Fonts/malgun.ttf",
        "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc",
        "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
        "/usr/share/fonts/truetype/nanum/NanumGothic.ttf",
    ]
    for path in font_candidates:
        if os.path.exists(path):
            return ImageFont.truetype(path, size)
    return ImageFont.load_default()


def make_storyboard(food_name: str, scene_count: int):
    templates = [
        {
            "title": "재료 클로즈업",
            "subtitle": f"오늘의 메뉴, {food_name}",
            "action": f"fresh ingredients for {food_name} arranged on a wooden counter, cinematic close-up"
        },
        {
            "title": "손질 장면",
            "subtitle": "재료 손질부터 시작",
            "action": f"hands slicing and preparing ingredients for {food_name}, detailed food preparation shot"
        },
        {
            "title": "팬 예열",
            "subtitle": "달궈진 팬 위로 향이 오른다",
            "action": "oil spreading in a hot pan, warm kitchen lighting, anticipation shot"
        },
        {
            "title": "재료 투입",
            "subtitle": "지글거리는 순간 시작",
            "action": f"main ingredients for {food_name} going into the pan, sizzling action, close-up"
        },
        {
            "title": "소스 장면",
            "subtitle": "윤기가 돌기 시작한다",
            "action": f"glossy sauce coating the {food_name}, steam rising, rich highlights"
        },
        {
            "title": "조리 클로즈업",
            "subtitle": "가장 맛있어 보이는 타이밍",
            "action": f"extreme close-up of {food_name} cooking beautifully, glossy texture, appetizing detail"
        },
        {
            "title": "플레이팅",
            "subtitle": "그릇 위에 정성스럽게 담기",
            "action": f"{food_name} being plated neatly in a bowl or on a plate, elegant presentation"
        },
        {
            "title": "완성샷",
            "subtitle": "완성. 마지막 한 컷",
            "action": f"finished {food_name}, cinematic hero shot, steam, glossy texture, appetizing close-up"
        },
    ]
    return templates[:scene_count]


def make_image_prompt(scene: dict, food_name: str, style: str) -> str:
    return f"""
Create an original anime-inspired food illustration for a vertical short-form cooking video.
Food: {food_name}
Scene title: {scene['title']}
Scene description: {scene['action']}
Style: {style}
Composition: vertical 9:16, food-focused, warm kitchen light, cinematic close-up.
Visual requirements: appetizing glossy texture, steam, rich food detail, clean framing, polished composition.
Do not include any text, watermark, logo, UI, or copyrighted characters.
Keep it original and consistent with an anime-inspired food illustration style.
""".strip()


def save_uploaded_file(uploaded_file, save_path: Path):
    save_path.write_bytes(uploaded_file.getbuffer())
    return str(save_path)


def generate_image(prompt: str, save_path: Path, api_key: str):
    client = get_client(api_key)
    result = client.images.generate(
        model="gpt-image-1",
        prompt=prompt,
        size="1024x1536"
    )
    image_base64 = result.data[0].b64_json
    image_bytes = base64.b64decode(image_base64)
    save_path.write_bytes(image_bytes)
    return str(save_path)


def resize_cover(img, target_w=WIDTH, target_h=HEIGHT):
    img = img.convert("RGB")
    w, h = img.size
    scale = max(target_w / w, target_h / h)
    new_w = int(w * scale)
    new_h = int(h * scale)
    img = img.resize((new_w, new_h), Image.LANCZOS)
    left = (new_w - target_w) // 2
    top = (new_h - target_h) // 2
    return img.crop((left, top, left + target_w, top + target_h))


def wrap_text(draw, text, font, max_width):
    if not text:
        return []
    lines = []
    current = ""
    for ch in text:
        test = current + ch
        bbox = draw.textbbox((0, 0), test, font=font)
        if bbox[2] - bbox[0] <= max_width:
            current = test
        else:
            if current:
                lines.append(current)
            current = ch
    if current:
        lines.append(current)
    return lines


def add_subtitle(img: Image.Image, text: str, position: str = "bottom"):
    if not text:
        return img
    draw = ImageDraw.Draw(img, "RGBA")
    font = get_font(56)
    max_width = WIDTH - 180
    lines = wrap_text(draw, text, font, max_width)
    if not lines:
        return img

    line_height = 76
    box_height = line_height * len(lines) + 46
    if position == "top":
        box_y = 100
    elif position == "middle":
        box_y = (HEIGHT - box_height) // 2
    else:
        box_y = HEIGHT - box_height - 170

    draw.rounded_rectangle(
        (70, box_y, WIDTH - 70, box_y + box_height),
        radius=30,
        fill=(0, 0, 0, 145)
    )

    y = box_y + 22
    for line in lines:
        bbox = draw.textbbox((0, 0), line, font=font)
        text_w = bbox[2] - bbox[0]
        x = (WIDTH - text_w) // 2
        draw.text((x, y), line, font=font, fill=(255, 255, 255, 255))
        y += line_height
    return img


def render_short_video(image_paths, subtitles, output_path: Path, seconds_per_scene=3, subtitle_position="bottom"):
    writer = imageio.get_writer(
        str(output_path),
        fps=FPS,
        codec="libx264",
        quality=8,
        macro_block_size=1,
    )
    frames_per_scene = FPS * seconds_per_scene

    for idx, (image_path, subtitle) in enumerate(zip(image_paths, subtitles)):
        base = Image.open(image_path)
        base = resize_cover(base)

        for i in range(frames_per_scene):
            t = i / max(1, frames_per_scene - 1)
            zoom = 1.0 + 0.05 * t
            zw = int(WIDTH * zoom)
            zh = int(HEIGHT * zoom)

            frame = base.resize((zw, zh), Image.LANCZOS)
            left = (zw - WIDTH) // 2
            top = (zh - HEIGHT) // 2
            frame = frame.crop((left, top, left + WIDTH, top + HEIGHT))

            frame = add_subtitle(frame, subtitle, subtitle_position)
            writer.append_data(np.array(frame))

    writer.close()
    return str(output_path)


def reset_all():
    for key in [
        "storyboard_df",
        "generated_image_paths",
        "video_path",
        "last_food_name",
        "last_scene_count",
    ]:
        if key in st.session_state:
            del st.session_state[key]


# -----------------------------
# Header
# -----------------------------
st.title("🍤 AniMeal Studio")
st.caption("애니풍 음식 쇼츠를 간단하게 만드는 Streamlit MVP · 생성 후 미리보기 가능")


# -----------------------------
# Sidebar
# -----------------------------
with st.sidebar:
    st.header("설정")
    food_name = st.text_input("음식 이름", value="매콤 새우덮밥")
    scene_count = st.slider("컷 수", min_value=4, max_value=8, value=6)
    seconds_per_scene = st.slider("컷당 길이(초)", min_value=2, max_value=5, value=3)
    subtitle_position = st.selectbox("자막 위치", ["bottom", "middle", "top"], index=0)
    style = st.selectbox(
        "그림 분위기",
        [
            "cozy anime-inspired cooking scene",
            "glossy anime food close-up",
            "warm cinematic hand-drawn food illustration",
            "soft original Japanese animation inspired food art",
        ],
        index=1,
    )

    st.divider()
    st.subheader("OpenAI API 키")
    st.text_input(
        "없으면 이미지 업로드 모드만 사용 가능",
        type="password",
        key="manual_api_key",
        placeholder="sk-..."
    )
    if get_api_key():
        st.success("API 키 확인됨")
    else:
        st.info("API 키를 넣으면 AI 이미지 생성 가능")

    st.divider()
    if st.button("전체 초기화"):
        reset_all()
        st.rerun()


# -----------------------------
# Step 1: Storyboard
# -----------------------------
st.subheader("1) 스토리보드 만들기")
col_a, col_b = st.columns([1, 1])
with col_a:
    if st.button("기본 스토리보드 생성", type="primary"):
        storyboard = make_storyboard(food_name, scene_count)
        st.session_state["storyboard_df"] = storyboard
        st.session_state["generated_image_paths"] = []
        st.session_state["video_path"] = ""
        st.session_state["last_food_name"] = food_name
        st.session_state["last_scene_count"] = scene_count
with col_b:
    st.write("스토리보드 생성 후, 아래 표에서 제목/자막/장면 설명을 수정할 수 있습니다.")

if "storyboard_df" in st.session_state:
    edited = st.data_editor(
        st.session_state["storyboard_df"],
        num_rows="fixed",
        use_container_width=True,
        column_config={
            "title": st.column_config.TextColumn("장면 제목"),
            "subtitle": st.column_config.TextColumn("자막"),
            "action": st.column_config.TextColumn("장면 설명 (영문 추천)", width="large"),
        },
        key="storyboard_editor",
    )
    st.session_state["storyboard_df"] = edited

    with st.expander("장면별 이미지 프롬프트 보기"):
        for idx, scene in enumerate(edited, start=1):
            st.markdown(f"**Scene {idx}. {scene['title']}**")
            st.code(make_image_prompt(scene, food_name, style), language="text")
else:
    st.info("왼쪽 입력값을 정한 뒤 '기본 스토리보드 생성'을 눌러주세요.")


# -----------------------------
# Step 2: Prepare images
# -----------------------------
st.divider()
st.subheader("2) 장면 이미지 준비")
mode = st.radio("이미지 준비 방식", ["AI로 자동 생성", "내가 직접 업로드"], horizontal=True)

image_paths = st.session_state.get("generated_image_paths", [])

if "storyboard_df" in st.session_state:
    storyboard = st.session_state["storyboard_df"]

    if mode == "AI로 자동 생성":
        if st.button("장면 이미지 생성"):
            api_key = get_api_key()
            if not api_key:
                st.error("OpenAI API 키가 필요합니다. 사이드바에 넣어주세요.")
            else:
                generated_paths = []
                progress = st.progress(0, text="이미지 생성 시작...")
                timestamp = int(time.time())
                for idx, scene in enumerate(storyboard, start=1):
                    prompt = make_image_prompt(scene, food_name, style)
                    save_path = OUTPUT_DIR / f"scene_{timestamp}_{idx}.png"
                    try:
                        generate_image(prompt, save_path, api_key)
                        generated_paths.append(str(save_path))
                        progress.progress(int(idx / len(storyboard) * 100), text=f"{idx}/{len(storyboard)} 생성 중...")
                    except Exception as e:
                        st.error(f"{idx}번 컷 생성 실패: {e}")
                        break
                if len(generated_paths) == len(storyboard):
                    st.session_state["generated_image_paths"] = generated_paths
                    st.session_state["video_path"] = ""
                    st.success("이미지 생성 완료")
                    image_paths = generated_paths

    else:
        st.write("각 장면에 맞는 이미지를 직접 업로드하세요.")
        uploaded_paths = []
        for idx, scene in enumerate(storyboard, start=1):
            uploaded_file = st.file_uploader(
                f"{idx}. {scene['title']} 이미지 업로드",
                type=["png", "jpg", "jpeg", "webp"],
                key=f"uploader_{idx}"
            )
            if uploaded_file is not None:
                suffix = Path(uploaded_file.name).suffix.lower() or ".png"
                save_path = OUTPUT_DIR / f"upload_{int(time.time())}_{idx}{suffix}"
                uploaded_paths.append(save_uploaded_file(uploaded_file, save_path))
        if len(uploaded_paths) == len(storyboard):
            st.session_state["generated_image_paths"] = uploaded_paths
            st.session_state["video_path"] = ""
            image_paths = uploaded_paths
            st.success("모든 이미지 업로드 완료")
        else:
            st.info(f"현재 {len(uploaded_paths)}/{len(storyboard)}장 업로드됨")

    current_paths = st.session_state.get("generated_image_paths", [])
    if current_paths:
        st.markdown("**현재 준비된 이미지**")
        cols = st.columns(3)
        for i, img_path in enumerate(current_paths):
            with cols[i % 3]:
                st.image(img_path, caption=f"Scene {i+1}", use_container_width=True)
else:
    st.info("먼저 스토리보드를 생성하세요.")


# -----------------------------
# Step 3: Preview video
# -----------------------------
st.divider()
st.subheader("3) 영상 미리보기 만들기")
st.write("다운로드 전에 아래 미리보기로 결과를 먼저 확인할 수 있습니다.")

if "storyboard_df" in st.session_state:
    storyboard = st.session_state["storyboard_df"]
    current_paths = st.session_state.get("generated_image_paths", [])

    if st.button("프리뷰 영상 생성"):
        if len(current_paths) != len(storyboard):
            st.error("모든 장면 이미지가 준비되어야 영상을 만들 수 있습니다.")
        else:
            subtitles = [scene.get("subtitle", "") for scene in storyboard]
            safe_food_name = sanitize_filename(food_name)
            output_path = OUTPUT_DIR / f"{safe_food_name}_{int(time.time())}.mp4"
            progress = st.progress(0, text="영상 렌더링 중...")
            try:
                render_short_video(
                    image_paths=current_paths,
                    subtitles=subtitles,
                    output_path=output_path,
                    seconds_per_scene=seconds_per_scene,
                    subtitle_position=subtitle_position,
                )
                progress.progress(100, text="완료")
                st.session_state["video_path"] = str(output_path)
                st.success("프리뷰 영상 생성 완료")
            except Exception as e:
                st.error(f"영상 생성 실패: {e}")

    video_path = st.session_state.get("video_path", "")
    if video_path and os.path.exists(video_path):
        st.video(video_path)
        st.info("자막이나 장면이 마음에 안 들면 수정 후 다시 '프리뷰 영상 생성'을 누르세요.")
        with open(video_path, "rb") as f:
            st.download_button(
                label="최종 mp4 다운로드",
                data=f,
                file_name=Path(video_path).name,
                mime="video/mp4",
                type="primary"
            )
else:
    st.info("스토리보드와 이미지 준비가 먼저 필요합니다.")


# -----------------------------
# Footer
# -----------------------------
st.divider()
st.markdown(
    """
**추천 사용 흐름**  
1. 음식 이름 입력  
2. 스토리보드 생성 후 자막/장면 설명 수정  
3. AI 이미지 생성 또는 직접 이미지 업로드  
4. 프리뷰 영상 생성  
5. 확인 후 mp4 다운로드  
"""
)
