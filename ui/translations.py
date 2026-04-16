from core.config_manager import ConfigManager

VI_TRANSLATIONS = {
    # App / Tabs
    "AI Subtitle Translator": "Trình dịch Phụ đề AI",
    "Translate": "Dịch",
    "Extract Subtitles": "Trích xuất Phụ đề",
    "Video Summary": "Tóm tắt Video",
    "Settings": "Cài đặt",
    "Restart Required": "Yêu cầu Khởi động lại",
    "Please restart the application to apply language changes.": "Vui lòng khởi động lại ứng dụng để áp dụng thay đổi ngôn ngữ.",
    
    # Settings Tab
    "Language:": "Ngôn ngữ:",
    "Built-in Providers": "Nhà cung cấp Tích hợp",
    "OpenAI Keys:": "Khóa OpenAI:",
    "Gemini Keys:": "Khóa Gemini:",
    "NVIDIA Keys:": "Khóa NVIDIA:",
    "💾 Save Built-in Keys": "💾 Lưu Khóa Tích hợp",
    "Custom OpenAI-Compatible Providers": "Nhà cung cấp Chuẩn OpenAI Tùy chỉnh",
    "Provider ID:": "ID Nhà cung cấp:",
    "Display Name:": "Tên Hiển thị:",
    "Base URL:": "URL Cơ sở:",
    "API Keys:": "Khóa API:",
    "Models:": "Mô hình:",
    "Headers (JSON):": "Headers (JSON):",
    "➕ Add / Update Custom Provider": "➕ Thêm / Cập nhật Nhà cung cấp Tùy chỉnh",
    "Success": "Thành công",
    "Default keys saved successfully.": "Lưu khóa mặc định thành công.",
    "Error": "Lỗi",
    "ID, Name, and Base URL are required.": "Cần có ID, Tên và URL Cơ sở.",
    "Invalid JSON format for headers.": "Định dạng JSON không hợp lệ cho headers.",
    "Custom provider '{name}' saved successfully.": "Lưu nhà cung cấp tùy chỉnh '{name}' thành công.",

    # Translate Tab
    "Provider:": "Nhà cung cấp:",
    "Model:": "Mô hình:",
    "Key Mode:": "Chế độ Khóa:",
    "Target Lang:": "Ngôn ngữ Đích:",
    "Chunk Size:": "Kích thước Đoạn:",
    "📂 Load Subtitle File": "📂 Tải File Phụ đề",
    "No file selected...": "Chưa chọn file nào...",
    "Context / Background Details:": "Văn cảnh / Chi tiết Nền:",
    "Quick Style:": "Kiểu Nhanh:",
    "Input Subtitles (VTT/SRT)": "Phụ đề Đầu vào (VTT/SRT)",
    "Translated Output": "Kết quả Dịch",
    "✕ Clear": "✕ Xóa",
    "▶ Start Translation": "▶ Bắt đầu Dịch",
    "⏹ Cancel": "⏹ Làm Hủy",
    "Ready": "Sẵn sàng",
    "💾 Save File": "💾 Lưu File",
    "Auto-Rotate": "Tự động Đảo Khóa",
    "Specific Key": "Khóa Cụ thể",
    "Loading models...": "Đang tải mô hình...",
    "Loading...": "Đang tải...",
    "No models found": "Không tìm thấy mô hình",
    "Please input text or load a file.": "Vui lòng nhập văn bản hoặc tải file.",
    "Chunk Size must be a valid integer.": "Kích thước Đoạn phải là một số nguyên hợp lệ.",
    "No API keys configured for openai.": "Chưa cấu hình khóa API cho openai.",
    "No API keys configured for gemini.": "Chưa cấu hình khóa API cho gemini.",
    "No API keys configured for nvidia.": "Chưa cấu hình khóa API cho nvidia.",
    "Custom provider not found.": "Không tìm thấy nhà cung cấp tùy chỉnh.",
    "Initializing translation engine...": "Đang khởi tạo trình dịch...",
    "Cancelling...": "Đang hủy...",
    "Translation cancelled.": "Đã hủy dịch.",
    "Translation completed successfully!": "Dịch thành công!",
    "Translation failed.": "Dịch thất bại.",
    "File saved successfully.": "Lưu file thành công.",
    "Saved": "Đã lưu",

    # Extract Tab
    "Whisper Model:": "Mô hình Whisper:",
    "Audio Lang:": "Ngôn ngữ Âm thanh:",
    "Output Format:": "Định dạng Đầu ra:",
    "🎬 Select Video/Audio": "🎬 Chọn Video/m thanh",
    "Extracted Subtitles": "Phụ đề Đã Trích xuất",
    "▶ Start Extraction": "▶ Bắt đầu Trích xuất",
    "↗ Send to Translate": "↗ Chuyển sang phần Dịch",
    "Please select a video/audio file first.": "Vui lòng chọn file video/âm thanh trước.",
    "Starting...": "Đang bắt đầu...",
    "Cancelling (waiting for Whisper to finish background task)...": "Đang hủy (chờ Whisper hoàn thành tác vụ nền)...",
    "Done! Detected Audio Language: {detected_lang}": "Hoàn tất! Ngôn ngữ m thanh phát hiện: {detected_lang}",
    "Error!": "Lỗi!",
    "Extraction cancelled by user.": "Người dùng đã hủy quá trình trích xuất.",
    "No subtitles to save.": "Không có phụ đề để lưu.",
    "Subtitles saved to {filename}": "Phụ đề đã lưu vào {filename}",
    "No subtitles to send.": "Không có phụ đề để chuyển.",
    "Translate tab not available.": "Tap dịch không khả dụng.",

    # Summary Tab
    "⚙️ Summary Settings": "⚙️ Cài đặt Tóm tắt",
    "Whisper:": "Whisper:",
    "Highlights:": "Số Đoạn Trích:",
    "Narration Lang:": "Ngôn ngữ Thuyết minh:",
    "🎬 Input Video": "🎬 Video Đầu vào",
    "Select Video": "Chọn Video",
    "🤖 AI Provider:": "🤖 Nhà cung cấp AI:",
    "Highlights Selected by AI": "Đoạn Trích Được AI Chọn",
    "SRT Output": "Đầu ra SRT",
    "▶ Start Auto Summary": "▶ Bắt đầu Tóm tắt Tự động",
    "▶ Continue Process": "▶ Tiếp tục Tiến trình",
    "💾 Setup Output & Run": "💾 Thiết lập Đầu ra và Chạy",
    "Please wait for AI models to load or check your API keys.": "Vui lòng chờ tải mô hình AI hoặc kiểm tra khóa API của bạn.",
    "Invalid number of highlights.": "Số lượng đoạn trích không hợp lệ.",
    "Analyzing subtitles with AI to find highlights...": "Đang phân tích phụ đề bằng AI để tìm đoạn trích...",
    "AI selected highlights. Please review and continue.": "AI đã chọn các đoạn trích. Vui lòng xem xét và tiếp tục.",
    "Reason: {reason}": "Lý do: {reason}",
    "Highlight #{i} : {start} -> {end}": "Đoạn trích #{i} : {start} -> {end}",
    "No highlights selected. Please select at least one.": "Không có đoạn trích nào được chọn. Vui lòng chọn ít nhất một.",
    "Generating narrations via AI...": "Đang tạo thuyết minh qua AI...",
    "Generating final SRT file...": "Đang tạo file SRT cuối cùng...",
    "Completed successfully!": "Hoàn tất thành công!",
    "Video Summary Processed!\n\nVideo: {output_video}\nSRT: {output_srt}": "Đã xử lý Tóm tắt Video!\n\nVideo: {output_video}\nSRT: {output_srt}",
}

def get_tr(config_manager: ConfigManager):
    def tr(text: str, **kwargs) -> str:
        lang = config_manager.get("language", "en")
        
        # Determine the translated template
        if lang == "vi":
            translated = VI_TRANSLATIONS.get(text, text)
        else:
            translated = text
            
        # Format if kwargs provided
        if kwargs:
            try:
                return translated.format(**kwargs)
            except KeyError:
                return translated
        return translated
    return tr
