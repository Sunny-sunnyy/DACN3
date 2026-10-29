import logging
from concurrent.futures import ThreadPoolExecutor
from typing import Dict, Optional

from price_agents.agent import Agent
from price_agents.specialist_agent import SpecialistAgent
from price_agents.frontier_agent import FrontierAgent
from price_agents.neural_network_agent import NeuralNetworkAgent
from price_agents.preprocessor import Preprocessor


class EnsembleAgent(Agent):
    name = "Ensemble Agent"
    color = Agent.YELLOW
    WEIGHTS = {"frontier": 0.8, "specialist": 0.1, "neural_network": 0.1}

    def __init__(self, collection):
        """
        Create an instance of Ensemble, by creating each of the models
        And loading the weights of the Ensemble
        """
        self.log("Initializing Ensemble Agent")
        self.specialist = SpecialistAgent()
        self.frontier = FrontierAgent(collection)
        self.neural_network = NeuralNetworkAgent()
        self.preprocessor = Preprocessor()
        self.log("Ensemble Agent is ready")

    def price(self, description: str) -> float:
        """
        Run this ensemble model
        Ask each of the models to price the product
        Then use the Linear Regression model to return the weighted price
        :param description: the description of a product
        :return: an estimate of its price
        """
        self.log("Running Ensemble Agent - preprocessing text")
        rewrite = self.preprocessor.preprocess(description)
        self.log(f"Pre-processed text using {self.preprocessor.model_name}")
        # 3 mô hình độc lập, cùng nhận `rewrite` => chạy song song (chờ mạng là chính: Modal, OpenAI)
        models = {
            "specialist": self.specialist.price,
            "frontier": self.frontier.price,
            "neural_network": self.neural_network.price,
        }
        with ThreadPoolExecutor(max_workers=len(models)) as executor:
            futures = {name: executor.submit(self._safe_price, name, fn, rewrite) for name, fn in models.items()}
            estimates = {name: f.result() for name, f in futures.items()}
        combined = self.combine(estimates)
        self.log(f"Ensemble Agent complete - returning ${combined:.2f}")
        return combined

    def _safe_price(self, name: str, price_fn, text: str) -> Optional[float]:
        """Một mô hình lỗi (mạng, Modal, parse) không làm hỏng cả ước lượng: ghi lỗi, trả None."""
        try:
            return price_fn(text)
        except Exception as e:
            logging.exception(f"[Ensemble] {name} failed: {type(e).__name__}: {e}")
            return None

    def combine(self, estimates: Dict[str, Optional[float]]) -> float:
        """Trung bình có trọng số 0.8 / 0.1 / 0.1 trên các mô hình trả giá hợp lệ (> 0).
        Frontier và Llama trả 0 khi không đọc được số => coi là lỗi, không đưa 0 vào trung bình
        (trước đây Frontier 0 kéo ước lượng xuống ~20% giá thật mà không ai biết).
        Thiếu mô hình thì chia lại trọng số cho các mô hình còn lại."""
        valid = {name: value for name, value in estimates.items() if value is not None and value > 0}
        missing = [name for name in estimates if name not in valid]
        if not valid:
            raise ValueError(f"No model returned a valid price: {estimates}")
        if missing:
            self.log(f"Ensemble Agent: missing {missing} - reweighting the others")
        total_weight = sum(self.WEIGHTS[name] for name in valid)
        return sum(self.WEIGHTS[name] * value for name, value in valid.items()) / total_weight
