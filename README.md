## Kiến trúc dự án
1. Pipelines
- Tạo và quản lý các queue, kết nối các filters với nhau
2. Filters
- Gồm 4 filter (như đã thảo luận)
3. Utils
- image_loader chịu trách nhiệm đọc/ ghi file hoặc xử lý định dạng file.

Về cấu trúc mỗi class có tối thiểu hàm khởi tạo và process với 2 tham số input_queue và output_queue.
## Cơ chế song song hoá
- Khi chương trình bắt đầu tạo 4 queue trên 4 core khác nhau cho mỗi filter.
- Ảnh cần được xử lý thì pipe đưa vào queue tương ứng với filter.

## hướng dẫn chạy
1. cài môi trường
python -m pip install -e .

