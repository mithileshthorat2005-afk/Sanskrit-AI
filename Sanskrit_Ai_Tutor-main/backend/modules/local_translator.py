
import logging
import threading
from pathlib import Path

import torch
from transformers import AutoTokenizer, AutoModelForSeq2SeqLM
from peft import PeftModel

logger = logging.getLogger(__name__)

BASE_MODEL = "facebook/nllb-200-distilled-600M"

MODEL_DIR = Path(__file__).resolve().parents[1] / "models"

EN_TO_SA_ADAPTER = MODEL_DIR / "English_To_Sanskrit"
SA_TO_EN_ADAPTER = (
    MODEL_DIR / "Sanskrit_To_English" / "checkpoint-5985"
)


class LocalSanskritTranslator:
    def __init__(self):
        self._model = None
        self._tokenizer = None
        self._active_adapter = None
        self._lock = threading.Lock()

    def _load_model(self):
        if self._model is not None:
            return

        if not EN_TO_SA_ADAPTER.exists():
            raise FileNotFoundError(
                f"English-to-Sanskrit adapter not found: "
                f"{EN_TO_SA_ADAPTER}"
            )

        if not SA_TO_EN_ADAPTER.exists():
            raise FileNotFoundError(
                f"Sanskrit-to-English adapter not found: "
                f"{SA_TO_EN_ADAPTER}"
            )

        logger.info("Loading NLLB tokenizer and base model...")

        tokenizer = AutoTokenizer.from_pretrained(BASE_MODEL)

        base_model = AutoModelForSeq2SeqLM.from_pretrained(
            BASE_MODEL,
            torch_dtype=torch.float32,
        )

        model = PeftModel.from_pretrained(
            base_model,
            str(EN_TO_SA_ADAPTER),
            adapter_name="en_to_sa",
        )

        model.load_adapter(
            str(SA_TO_EN_ADAPTER),
            adapter_name="sa_to_en",
        )

        model.eval()

        self._tokenizer = tokenizer
        self._model = model

        logger.info("Local translation models loaded.")

    def translate(self, text: str, direction: str) -> str | None:
        text = text.strip()

        if not text:
            return None

        if direction not in ("en_to_sa", "sa_to_en"):
            raise ValueError(f"Unsupported translation direction: {direction}")

        with self._lock:
            try:
                self._load_model()

                if self._active_adapter != direction:
                    self._model.set_adapter(direction)
                    self._active_adapter = direction

                if direction == "en_to_sa":
                    self._tokenizer.src_lang = "eng_Latn"
                    target_lang = "san_Deva"
                else:
                    self._tokenizer.src_lang = "san_Deva"
                    target_lang = "eng_Latn"

                inputs = self._tokenizer(
                    text,
                    return_tensors="pt",
                    truncation=True,
                    max_length=256,
                )

                target_token_id = self._tokenizer.convert_tokens_to_ids(
                    target_lang
                )

                with torch.inference_mode():
                    generated = self._model.generate(
                        **inputs,
                        forced_bos_token_id=target_token_id,
                        max_new_tokens=128,
                        num_beams=4,
                    )

                result = self._tokenizer.batch_decode(
                    generated,
                    skip_special_tokens=True,
                )[0].strip()

                return result or None

            except Exception:
                logger.exception("Local translation failed.")
                return None


local_translator = LocalSanskritTranslator()
