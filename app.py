import os
import asyncio
import time
import pysrt
import streamlit as st
from pydub import AudioSegment
import edge_tts

# --- Cấu hình FFmpeg ---
# Streamlit sẽ cài đặt FFmpeg từ file packages.txt
# Chúng ta không cần chỉ định đường dẫn thủ công nữa.

# --- Các hàm xử lý cốt lõi (giữ nguyên từ file cũ) ---

async def convert_text_to_speech(text, voice, rate, volume, pitch):
    """Hàm chuyển đổi văn bản đơn giản."""
    communicate = edge_tts.Communicate(text, voice, rate=rate, volume=volume, pitch=pitch)
    # Lưu vào một file tạm thời
    temp_file = f"temp_output_{int(time.time())}.mp3"
    await communicate.save(temp_file)
    return temp_file

async def convert_srt_to_timed_speech(srt_content, voice, rate, volume, pitch):
    """Hàm chuyển đổi file SRT có đồng bộ hóa thời gian."""
    subs = pysrt.from_string(srt_content)
    final_audio = AudioSegment.silent(duration=0)
    last_end_time_ms = 0
    
    temp_files = [] # Để theo dõi các file tạm

    progress_bar = st.progress(0, text="Đang xử lý phụ đề...")

    for i, sub in enumerate(subs):
        start_time_ms = sub.start.ordinal
        end_time_ms = sub.end.ordinal

        silence_duration = start_time_ms - last_end_time_ms
        if silence_duration > 0:
            final_audio += AudioSegment.silent(duration=silence_duration)

        if not sub.text.strip():
            last_end_time_ms = end_time_ms
            continue

        temp_audio_path = f"temp_{sub.index}_{int(time.time())}.mp3"
        temp_files.append(temp_audio_path)
        try:
            communicate = edge_tts.Communicate(sub.text, voice, rate=rate, volume=volume, pitch=pitch)
            await communicate.save(temp_audio_path)
            
            segment = AudioSegment.from_mp3(temp_audio_path)
            final_audio += segment
            last_end_time_ms = start_time_ms + len(segment)
        except Exception as e:
            st.warning(f"Lỗi ở phụ đề {sub.index}: {e}. Bỏ qua...")
            last_end_time_ms = end_time_ms

        # Cập nhật thanh tiến trình
        progress_bar.progress((i + 1) / len(subs), text=f"Đang xử lý phụ đề {i+1}/{len(subs)}")

    # Xóa các file tạm
    for f in temp_files:
        if os.path.exists(f):
            os.remove(f)

    # Xuất file cuối cùng
    final_output_path = f"timed_output_{int(time.time())}.mp3"
    final_audio.export(final_output_path, format="mp3")
    progress_bar.empty() # Xóa thanh tiến trình
    return final_output_path

# --- Giao diện người dùng Streamlit ---

st.set_page_config(layout="wide")

st.markdown("<h1 style='text-align: center; color: #3498db;'>CÔNG CỤ TTS BY LÝ VĂN HIỆP</h1>", unsafe_allow_html=True)
st.markdown("---")

# Dữ liệu giọng đọc (từ file index.html của bạn)
all_voices = [
    { "ShortName": "vi-VN-HoaiMyNeural", "FriendlyName": "HoaiMy", "Locale": "Vietnamese", "Gender": "Female" },
    { "ShortName": "vi-VN-NamMinhNeural", "FriendlyName": "NamMinh", "Locale": "Vietnamese", "Gender": "Male" },
    { "ShortName": "ko-KR-BongJinNeural", "FriendlyName": "BongJin", "Locale": "Korean", "Gender": "Male" },
    { "ShortName": "ko-KR-GookMinNeural", "FriendlyName": "GookMin", "Locale": "Korean", "Gender": "Male" },
    { "ShortName": "ko-KR-InJoonNeural", "FriendlyName": "InJoon", "Locale": "Korean", "Gender": "Male" },
    { "ShortName": "ko-KR-JiMinNeural", "FriendlyName": "JiMin", "Locale": "Korean", "Gender": "Female" },
    { "ShortName": "ko-KR-SeoHyeonNeural", "FriendlyName": "SeoHyeon", "Locale": "Korean", "Gender": "Female" },
    { "ShortName": "ko-KR-SunHiNeural", "FriendlyName": "SunHi", "Locale": "Korean", "Gender": "Female" },
    { "ShortName": "ja-JP-AoiNeural", "FriendlyName": "Aoi", "Locale": "Japanese", "Gender": "Female" },
    { "ShortName": "ja-JP-DaichiNeural", "FriendlyName": "Daichi", "Locale": "Japanese", "Gender": "Male" },
    { "ShortName": "ja-JP-KeitaNeural", "FriendlyName": "Keita", "Locale": "Japanese", "Gender": "Male" },
    { "ShortName": "ja-JP-NanamiNeural", "FriendlyName": "Nanami", "Locale": "Japanese", "Gender": "Female" },
    { "ShortName": "en-US-BrandonNeural", "FriendlyName": "Brandon", "Locale": "English (US)", "Gender": "Male" },
    { "ShortName": "en-US-ChristopherNeural", "FriendlyName": "Christopher", "Locale": "English (US)", "Gender": "Male" },
    { "ShortName": "en-US-CoraNeural", "FriendlyName": "Cora", "Locale": "English (US)", "Gender": "Female" },
    # Thêm các giọng đọc khác nếu cần
]

# Chia layout thành 2 cột
col1, col2 = st.columns([1, 2])

with col1:
    st.header("Bảng điều khiển ⚙️")
    
    # Tìm kiếm và chọn giọng đọc
    search_term = st.text_input("Tìm kiếm giọng đọc (e.g., vi, en-US, female...)", "")
    
    filtered_voices = [
        v for v in all_voices if 
        search_term.lower() in v['FriendlyName'].lower() or 
        search_term.lower() in v['Locale'].lower() or
        search_term.lower() in v['Gender'].lower()
    ]
    
    voice_options = {f"{v['FriendlyName']} ({v['Locale']}, {v['Gender']})": v['ShortName'] for v in filtered_voices}
    
    selected_voice_display = st.selectbox(
        "Chọn giọng đọc", 
        options=list(voice_options.keys()),
        index=0 # Mặc định chọn giọng đầu tiên
    )
    voice_select = voice_options[selected_voice_display]
    st.info(f"Đã tìm thấy {len(filtered_voices)}/{len(all_voices)} giọng đọc.")

    # Các thanh trượt
    rate_val = st.slider("Tốc độ", -100, 100, 0)
    volume_val = st.slider("Âm lượng", -100, 100, 0)
    pitch_val = st.slider("Cao độ (Hz)", -50, 50, 0)
    
    # Định dạng lại giá trị cho edge-tts
    rate = f"{'+' if rate_val >= 0 else ''}{rate_val}%"
    volume = f"{'+' if volume_val >= 0 else ''}{volume_val}%"
    pitch = f"{'+' if pitch_val >= 0 else ''}{pitch_val}Hz"

with col2:
    st.header("Nội dung & Kết quả 📝")

    uploaded_file = st.file_uploader("Tải lên file .txt hoặc .srt", type=['txt', 'srt'])
    
    # Checkbox đồng bộ SRT chỉ hiển thị khi có file .srt được tải lên
    is_srt_timed = False
    if uploaded_file and uploaded_file.name.lower().endswith('.srt'):
        is_srt_timed = st.checkbox("Đồng bộ hóa thời gian file SRT", value=True)

    st.divider()

    text_input = st.text_area("Hoặc nhập văn bản vào đây...", height=250, 
        value=uploaded_file.read().decode('utf-8') if uploaded_file else ""
    )
    
    if st.button("Chuyển đổi thành giọng nói", use_container_width=True, type="primary"):
        if not text_input.strip() and not uploaded_file:
            st.error("Vui lòng nhập văn bản hoặc tải lên một file.")
        else:
            final_text = text_input
            
            with st.spinner('Đang xử lý, vui lòng chờ...'):
                try:
                    output_file = None
                    # Xử lý SRT có đồng bộ
                    if uploaded_file and uploaded_file.name.lower().endswith('.srt') and is_srt_timed:
                         srt_content = final_text
                         output_file = asyncio.run(convert_srt_to_timed_speech(srt_content, voice_select, rate, volume, pitch))
                    # Xử lý văn bản thường hoặc SRT không đồng bộ
                    else:
                        output_file = asyncio.run(convert_text_to_speech(final_text, voice_select, rate, volume, pitch))

                    st.success("Hoàn tất! ✅")
                    
                    # Hiển thị trình phát và nút tải xuống
                    audio_file = open(output_file, 'rb')
                    audio_bytes = audio_file.read()
                    st.audio(audio_bytes, format='audio/mpeg')
                    
                    st.download_button(
                        label="Tải xuống file MP3",
                        data=audio_bytes,
                        file_name=os.path.basename(output_file),
                        mime='audio/mpeg'
                    )
                    
                    # Dọn dẹp file đã tạo
                    if os.path.exists(output_file):
                        os.remove(output_file)

                except Exception as e:
                    st.error(f"Đã xảy ra lỗi: {e}")