# Shopping Assistant V3

US Deal Assistant nói tiếng Việt cho demo DATN/CV.

Người dùng trò chuyện bằng tiếng Việt. Hệ thống tìm kiếm và định giá sản phẩm
từ Amazon và BestBuy, sau đó giải thích kết quả bằng tiếng Việt với product
cards dùng giá USD.

V3 cũng được định vị như một Vietnamese Shopping Sidekick: một specialist
sidekick cho shopping, giữ controlled Router + explicit tools thay vì
free-form autonomous browser agent.

V3 là source of truth tài liệu đã được đơn giản hóa cho lần triển khai tiếp
theo. Bắt đầu với:

- `gameplan.md`
- `guides/architecture.md`
- `guides/agent_architecture.md`
- guide của phase hiện tại trong `guides/`
- `reports/sidekick_patterns_brainstorm_report.md` nếu cần context về
  Sidekick-inspired progress/evidence direction đã được brainstorm.

`shopping_assistant_v2/` chỉ là tài liệu tham chiếu cho migration. `segment4/`
chỉ là prototype/reference và không được chỉnh sửa bởi implementation V3 trừ
khi được phê duyệt rõ ràng.
