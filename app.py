import os
import asyncio
import time
import pysrt
import streamlit as st
import edge_tts
import subprocess # Thư viện để chạy lệnh hệ thống như FFmpeg

# --- Các hàm xử lý cốt lõi ---

async def convert_text_to_speech(text, voice, rate, volume, pitch):
    """Hàm chuyển đổi văn bản đơn giản (không thay đổi)."""
    communicate = edge_tts.Communicate(text, voice, rate=rate, volume=volume, pitch=pitch)
    temp_file = f"temp_output_{int(time.time())}.mp3"
    await communicate.save(temp_file)
    return temp_file

async def convert_srt_to_timed_speech_with_ffmpeg(srt_content, voice, rate, volume, pitch):
    """
    Hàm chuyển đổi SRT đã được nâng cấp với cơ chế xử lý lỗi và timeout
    để tránh bị treo khi gọi FFmpeg.
    """
    subs = pysrt.from_string(srt_content)
    
    temp_files = []
    concat_list_path = "filelist.txt"
    last_end_time_ms = 0
    
    progress_bar = st.progress(0, text="Bắt đầu xử lý phụ đề...")

    for i, sub in enumerate(subs):
        start_time_ms = sub.start.ordinal
        
        # 1. Tạo khoảng lặng bằng FFmpeg
        silence_duration_ms = start_time_ms - last_end_time_ms
        if silence_duration_ms > 50:
            silence_file = f"temp_silence_{i}.mp3"
            duration_sec = silence_duration_ms / 1000.0
            cmd = [
                'ffmpeg', '-f', 'lavfi', '-i', f'anullsrc=r=24000:cl=mono', 
                '-t', str(duration_sec), '-q:a', '5', '-y', silence_file
            ]
            try:
                # Nâng cấp: Thêm timeout và ghi log lỗi chi tiết
                result = subprocess.run(
                    cmd, check=True, capture_output=True, text=True, timeout=60
                )
            except subprocess.TimeoutExpired:
                st.error(f"Lỗi ở phụ đề {i}: Lệnh FFmpeg để tạo khoảng lặng mất quá nhiều thời gian (> 60s).")
                raise
            except subprocess.CalledProcessError as e:
                st.error(f"Lỗi ở phụ đề {i}: FFmpeg không thể tạo file im lặng. Chi tiết: {e.stderr}")
                raise
            temp_files.append(silence_file)

        # 2. Tạo file âm thanh cho câu thoại
        if sub.text.strip():
            speech_file = f"temp_speech_{i}.mp3"
            communicate = edge_tts.Communicate(sub.text, voice, rate=rate, volume=volume, pitch=pitch)
            await communicate.save(speech_file)
            temp_files.append(speech_file)
        
        last_end_time_ms = sub.end.ordinal
        progress_bar.progress((i + 1) / len(subs), text=f"Đã xử lý phụ đề {i+1}/{len(subs)}")

    # 3. Tạo file danh sách để FFmpeg nối các file lại
    with open(concat_list_path, "w", encoding='utf-8') as f:
        for filename in temp_files:
            # Sử dụng đường dẫn tương đối để an toàn hơn
            f.write(f"file '{filename}'\n")

    # 4. Chạy lệnh FFmpeg để nối tất cả các file
    final_output_path = f"timed_output_{int(time.time())}.mp3"
    concat_cmd = [
        'ffmpeg', '-f', 'concat', '-safe', '0', 
        '-i', concat_list_path, '-c', 'copy', '-y', final_output_path
    ]
    try:
        # Nâng cấp: Thêm timeout và ghi log lỗi chi tiết
        result = subprocess.run(
            concat_cmd, check=True, capture_output=True, text=True, timeout=180
        )
    except subprocess.TimeoutExpired:
        st.error("Lỗi: Lệnh FFmpeg để nối file mất quá nhiều thời gian (> 3 phút).")
        raise
    except subprocess.CalledProcessError as e:
        st.error(f"Lỗi: FFmpeg không thể nối các file âm thanh. Chi tiết: {e.stderr}")
        raise

    # 5. Dọn dẹp tất cả các file tạm
    for f in temp_files:
        if os.path.exists(f): os.remove(f)
    if os.path.exists(concat_list_path): os.remove(concat_list_path)
    
    progress_bar.empty()
    return final_output_path


# --- Giao diện người dùng Streamlit (Giữ nguyên) ---

st.set_page_config(layout="wide")
st.markdown("<h1 style='text-align: center; color: #3498db;'>CÔNG CỤ TTS BY LÝ VĂN HIỆP</h1>", unsafe_allow_html=True)
st.markdown("---")

all_voices = [
    # Vietnamese
    { "ShortName": "vi-VN-HoaiMyNeural", "FriendlyName": "HoaiMy", "Locale": "Vietnamese", "Gender": "Female" },
    { "ShortName": "vi-VN-NamMinhNeural", "FriendlyName": "NamMinh", "Locale": "Vietnamese", "Gender": "Male" },
    # Korean
    { "ShortName": "ko-KR-BongJinNeural", "FriendlyName": "BongJin", "Locale": "Korean", "Gender": "Male" },
    { "ShortName": "ko-KR-GookMinNeural", "FriendlyName": "GookMin", "Locale": "Korean", "Gender": "Male" },
    { "ShortName": "ko-KR-InJoonNeural", "FriendlyName": "InJoon", "Locale": "Korean", "Gender": "Male" },
    { "ShortName": "ko-KR-JiMinNeural", "FriendlyName": "JiMin", "Locale": "Korean", "Gender": "Female" },
    { "ShortName": "ko-KR-SeoHyeonNeural", "FriendlyName": "SeoHyeon", "Locale": "Korean", "Gender": "Female" },
    { "ShortName": "ko-KR-SunHiNeural", "FriendlyName": "SunHi", "Locale": "Korean", "Gender": "Female" },
    # Japanese
    { "ShortName": "ja-JP-AoiNeural", "FriendlyName": "Aoi", "Locale": "Japanese", "Gender": "Female" },
    { "ShortName": "ja-JP-DaichiNeural", "FriendlyName": "Daichi", "Locale": "Japanese", "Gender": "Male" },
    { "ShortName": "ja-JP-KeitaNeural", "FriendlyName": "Keita", "Locale": "Japanese", "Gender": "Male" },
    { "ShortName": "ja-JP-NanamiNeural", "FriendlyName": "Nanami", "Locale": "Japanese", "Gender": "Female" },
    # US English
    { "ShortName": "en-US-BrandonNeural", "FriendlyName": "Brandon", "Locale": "English (US)", "Gender": "Male" },
    { "ShortName": "en-US-ChristopherNeural", "FriendlyName": "Christopher", "Locale": "English (US)", "Gender": "Male" },
    { "ShortName": "en-US-CoraNeural", "FriendlyName": "Cora", "Locale": "English (US)", "Gender": "Female" },
    { "ShortName": "en-US-DavisNeural", "FriendlyName": "Davis", "Locale": "English (US)", "Gender": "Male" },
    { "ShortName": "en-US-ElizabethNeural", "FriendlyName": "Elizabeth", "Locale": "English (US)", "Gender": "Female" },
    { "ShortName": "en-US-EmmaNeural", "FriendlyName": "Emma", "Locale": "English (US)", "Gender": "Female" },
    { "ShortName": "en-US-EricNeural", "FriendlyName": "Eric", "Locale": "English (US)", "Gender": "Male" },
    { "ShortName": "en-US-GuyNeural", "FriendlyName": "Guy", "Locale": "English (US)", "Gender": "Male" },
    { "ShortName": "en-US-JacobNeural", "FriendlyName": "Jacob", "Locale": "English (US)", "Gender": "Male" },
    { "ShortName": "en-US-JaneNeural", "FriendlyName": "Jane", "Locale": "English (US)", "Gender": "Female" },
    { "ShortName": "en-US-JasonNeural", "FriendlyName": "Jason", "Locale": "English (US)", "Gender": "Male" },
    { "ShortName": "en-US-JennyNeural", "FriendlyName": "Jenny", "Locale": "English (US)", "Gender": "Female" },
    { "ShortName": "en-US-MichelleNeural", "FriendlyName": "Michelle", "Locale": "English (US)", "Gender": "Female" },
    { "ShortName": "en-US-MonicaNeural", "FriendlyName": "Monica", "Locale": "English (US)", "Gender": "Female" },
    { "ShortName": "en-US-NancyNeural", "FriendlyName": "Nancy", "Locale": "English (US)", "Gender": "Female" },
    { "ShortName": "en-US-RogerNeural", "FriendlyName": "Roger", "Locale": "English (US)", "Gender": "Male" },
    { "ShortName": "en-US-SaraNeural", "FriendlyName": "Sara", "Locale": "English (US)", "Gender": "Female" },
    { "ShortName": "en-US-SteffanNeural", "FriendlyName": "Steffan", "Locale": "English (US)", "Gender": "Male" },
    { "ShortName": "en-US-TonyNeural", "FriendlyName": "Tony", "Locale": "English (US)", "Gender": "Male" },
]

col1, col2 = st.columns([1, 2])
with col1:
    st.header("Bảng điều khiển ⚙️")
    search_term = st.text_input("Tìm kiếm giọng đọc (e.g., vi, en-US, female...)", "")
    filtered_voices = [v for v in all_voices if search_term.lower() in str(v).lower()]
    voice_options = {f"{v['FriendlyName']} ({v['Locale']}, {v['Gender']})": v['ShortName'] for v in filtered_voices}
    
    selectbox_options = list(voice_options.keys())
    selected_voice_display = st.selectbox("Chọn giọng đọc", options=selectbox_options, index=0 if selectbox_options else -1)
    
    voice_select = voice_options.get(selected_voice_display)
    
    rate_val = st.slider("Tốc độ", -100, 100, 0)
    volume_val = st.slider("Âm lượng", -100, 100, 0)
    pitch_val = st.slider("Cao độ (Hz)", -50, 50, 0)
    
    rate = f"{'+' if rate_val >= 0 else ''}{rate_val}%"
    volume = f"{'+' if volume_val >= 0 else ''}{volume_val}%"
    pitch = f"{'+' if pitch_val >= 0 else ''}{pitch_val}Hz"

with col2:
    st.header("Nội dung & Kết quả 📝")
    uploaded_file = st.file_uploader("Tải lên file .txt hoặc .srt", type=['txt', 'srt'])
    
    is_srt_timed = False
    if uploaded_file and uploaded_file.name.lower().endswith('.srt'):
        is_srt_timed = st.checkbox("Đồng bộ hóa thời gian file SRT", value=True)

    st.divider()
    text_input = st.text_area("Hoặc nhập văn bản vào đây...", height=250, value=uploaded_file.read().decode('utf-8') if uploaded_file else "")
    
    if st.button("Chuyển đổi thành giọng nói", use_container_width=True, type="primary"):
        if not text_input.strip() or not voice_select:
            if not text_input.strip(): st.error("Vui lòng nhập văn bản hoặc tải lên một file.")
            if not voice_select: st.error("Không có giọng đọc nào được chọn. Vui lòng xóa bộ lọc tìm kiếm.")
        else:
            with st.spinner('Đang xử lý, vui lòng chờ...'):
                try:
                    output_file = None
                    if uploaded_file and uploaded_file.name.lower().endswith('.srt') and is_srt_timed:
                         srt_content = text_input
                         output_file = asyncio.run(convert_srt_to_timed_speech_with_ffmpeg(srt_content, voice_select, rate, volume, pitch))
                    else:
                        output_file = asyncio.run(convert_text_to_speech(text_input, voice_select, rate, volume, pitch))

                    st.success("Hoàn tất! ✅")
                    with open(output_file, 'rb') as audio_file:
                        audio_bytes = audio_file.read()
                        st.audio(audio_bytes, format='audio/mpeg')
                        st.download_button(
                            label="Tải xuống file MP3",
                            data=audio_bytes,
                            file_name=os.path.basename(output_file),
                            mime='audio/mpeg'
                        )
                    
                    if os.path.exists(output_file): os.remove(output_file)
                except Exception as e:
                    # Hiển thị lỗi một cách thân thiện hơn
                    if "timed out" in str(e).lower():
                        st.error(f"Xử lý thất bại: {e}")
                    else:
                        st.error(f"Đã xảy ra một lỗi không mong muốn: {e}")