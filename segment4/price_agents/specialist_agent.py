import threading
import time
from typing import Optional

import modal
import modal.exception
from price_agents.agent import Agent


MODAL_APP = "pricer-service"
MODAL_CLASS = "Pricer"


def wake_up_modal():
    """Gửi một lượt gọi không chờ kết quả để Modal bật máy sẵn (gọi ngay lúc mở app, trước khi nạp mô hình ~20 s)."""
    modal.Cls.from_name(MODAL_APP, MODAL_CLASS)().price.spawn(SpecialistAgent.PING_TEXT)


class SpecialistAgent(Agent):
    """
    An Agent that runs our fine-tuned LLM that's running remotely on Modal
    """

    name = "Specialist Agent"
    color = Agent.RED

    # Modal tắt máy sau 60 s rảnh (mặc định; app "pricer-service" không đặt khác) => khởi động lại 32-46 s.
    # Không deploy được app mới (Modal đòi gắn thẻ, 29/10) nên giữ ấm từ phía máy mình.
    COLD_SKIP_SECONDS = 45    # vừa quá giờ => máy đang khởi động (32-46 s), các deal kế tiếp không chờ nữa
    PING_SECONDS = 50         # < 60 s để máy không tắt
    KEEP_WARM_IDLE_STOP = 900 # 15 phút không ai tìm => ngừng ping (T4 ~$0,59 / giờ)
    PING_TEXT = "warm-up ping"

    def __init__(self, timeout_seconds: Optional[float] = None):
        """
        Set up this Agent by creating an instance of the modal class
        :param timeout_seconds: chờ Llama tối đa bao lâu; None = chờ tới khi có kết quả (như cũ — price_is_right
            không giữ ấm Modal nên không đặt giới hạn). search_key đặt 10 s vì có đánh thức + giữ ấm.
        """
        self.timeout_seconds = timeout_seconds
        self.log("Specialist Agent is initializing - connecting to modal")
        Pricer = modal.Cls.from_name(MODAL_APP, MODAL_CLASS)
        self.pricer = Pricer()
        # Xếp hàng các lời gọi: gọi song song có thể làm Modal bật thêm máy nguội (tốn tiền, không nhanh hơn)
        self._call_lock = threading.Lock()
        self._skip_until = 0.0
        self._last_used = time.time()
        self._keep_warm_thread = None
        self._keep_warm_lock = threading.Lock()  # 3 deal song song cùng thấy luồng đã dừng => chỉ bật lại một luồng
        self.log("Specialist Agent is ready")

    def price(self, description: str) -> float:
        """
        Make a remote call to return the estimate of the price of this item
        Raises TimeoutError when Modal is too slow (cold start) - the ensemble then drops this model.
        """
        self._last_used = time.time()
        with self._keep_warm_lock:
            if self._keep_warm_thread is not None and not self._keep_warm_thread.is_alive():
                self.start_keep_warm()  # đã ngừng vì rảnh lâu; có lượt tìm mới thì giữ ấm lại
        self.log("Specialist Agent is calling remote fine-tuned model")
        with self._call_lock:
            # Kiểm trong khoá: các deal song song đang chờ khoá phải thấy lượt trước vừa quá giờ (không chờ thêm 10 s mỗi deal)
            if time.time() < self._skip_until:
                raise TimeoutError("Modal is still starting up (previous call timed out) - skipping")
            call = self.pricer.price.spawn(description)
            try:
                result = call.get(timeout=self.timeout_seconds)
            except (TimeoutError, modal.exception.TimeoutError):
                # Lời gọi vẫn chạy tiếp trên Modal => máy được làm ấm cho các lượt sau
                self._skip_until = time.time() + self.COLD_SKIP_SECONDS
                raise TimeoutError(f"Modal did not answer within {self.timeout_seconds}s (cold start?)")
        self.log(f"Specialist Agent completed - predicting ${result:.2f}")
        return result

    def start_keep_warm(self):
        """Luồng nền ping Modal mỗi PING_SECONDS; tự dừng khi KEEP_WARM_IDLE_STOP giây không có lượt price() thật."""
        self._last_used = time.time()
        self._keep_warm_thread = threading.Thread(target=self._keep_warm_loop, daemon=True, name="modal-keep-warm")
        self._keep_warm_thread.start()

    def _keep_warm_loop(self):
        while time.time() - self._last_used < self.KEEP_WARM_IDLE_STOP:
            try:
                self.pricer.price.spawn(self.PING_TEXT)
            except Exception as e:
                self.log(f"Keep-warm ping failed: {type(e).__name__}: {e}")
            time.sleep(self.PING_SECONDS)
        self.log(f"Specialist Agent: no search for {self.KEEP_WARM_IDLE_STOP // 60} min - stop keeping Modal warm")
