# Yêu cầu: Đề xuất cơ chế khám phá thuật toán cho Alpha-Lab Framework

## Bối cảnh

Trong quá trình nghiên cứu và xây dựng chiến lược VTrend tại repo /var/www/trading-bots/btc-spot-dev, AI đã vô tình tạo ra thuật toán **VDO**. Việc tạo ra VDO là khi x38-full còn mới sơ khai — tôi đã viết một prompt và gửi vào AI, và nó vô tình tạo ra VDO. Vì lúc đó chưa backtest kỹ nên tôi cũng không quan tâm lắm và không lưu lại mẫu prompt đó. Sau khi trải qua rất nhiều thử nghiệm khác nhau, VDO đọng lại như một thuật toán hữu ích cho chiến lược VTrend đã được chứng minh.

Hiện tại, chúng ta đang phát triển X38 để nghiên cứu và tạo ra các spec để xây dựng **Alpha-Lab Framework**.

## Mục tiêu cốt lõi

Có hai tầng cần giải quyết:

1. **Tạo điều kiện cho "tai nạn tốt" xảy ra:** Trước khi nói đến hệ thống hóa, cần có cơ chế để AI liên tục thử nghiệm, tổ hợp, khám phá — tạo ra nhiều kết quả bất ngờ tiềm năng. Câu chuyện VDO xảy ra được là vì có một lần prompt đúng lúc, đúng cách — nhưng hiện tại không có quy trình nào chủ động tạo ra những lần "vô tình" như vậy.

2. **Nhận diện và hệ thống hóa:** Khi những kết quả bất ngờ xuất hiện, cần có cách nhận ra cái nào hữu ích, chứng minh giá trị của nó, và tích hợp vào framework một cách có hệ thống và tái lập được.

## Yêu cầu cụ thể

Dựa trên toàn bộ tài liệu, topic và spec hiện có trong X38, hãy thực hiện:

1. **Đề xuất cơ chế exploration (Tầng 1):** Thiết kế cơ chế để AI chủ động thử nghiệm, tổ hợp, và khám phá — tạo ra nhiều "tai nạn tốt" tiềm năng. Ví dụ: cách quét tổ hợp feature, cách tạo biến thể thuật toán, cách cho AI tự do thử nghiệm có kiểm soát... Mỗi đề xuất cần có: mục đích, input, output, và cách tích hợp vào framework hiện tại.

2. **Đề xuất cơ chế nhận diện & hệ thống hóa (Tầng 2):** Khi kết quả bất ngờ xuất hiện, làm sao nhận ra cái nào hữu ích? Quy trình sàng lọc, chứng minh, và tích hợp nên như thế nào?

3. **Xác định gap:** Những kỹ thuật phân tích dữ liệu hoặc phương pháp khám phá thuật toán nào còn thiếu hoặc chưa được tích hợp đầy đủ trong X38 để hỗ trợ hai tầng trên?

4. **Đề xuất bổ sung cho X38:** Nếu X38 cần thêm topic, spec hoặc kỹ thuật mới, hãy đề xuất cụ thể với lý do tại sao nó cần thiết và nó giải quyết vấn đề gì.
