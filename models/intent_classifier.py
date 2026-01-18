import torch
import numpy as np
import json, os
from transformers import AutoTokenizer, AutoModelForSequenceClassification
from peft import PeftModel

class IntentClassifier:
    def __init__(self, base_checkpoint: str, adapter_dir: str, device: str | None = None):
        self.device = device or ("cuda" if torch.cuda.is_available() else "cpu")
        # load tokenizer from adapter folder
        self.tokenizer = AutoTokenizer.from_pretrained(adapter_dir, use_fast=True)

        # --- Determine num_labels from adapter config ---
        num_labels = None

        # --- Load label mapping from adapter_dir if available ---
        id2label_path = os.path.join(adapter_dir, "id2label.json")
        label2id_path = os.path.join(adapter_dir, "label2id.json")

        if os.path.exists(id2label_path):
            with open(id2label_path, "r", encoding="utf-8") as f:
                self.id2label = json.load(f)
        else:
            # fallback to config (will be LABEL_0..)
            self.id2label = self.model.config.id2label

        if os.path.exists(label2id_path):
            with open(label2id_path, "r", encoding="utf-8") as f:
                self.label2id = json.load(f)
                num_labels = len(self.label2id)
        else:
            self.label2id = self.model.config.label2id
            num_labels = 77

        # Optional: sanity check
        # print("Loaded id2label from:", id2label_path if os.path.exists(id2label_path) else "model.config")
        # print("Example id2label[\"22\"]:", self.id2label.get("22"))

        # load the base model from HuggingFace
        base = AutoModelForSequenceClassification.from_pretrained(
            base_checkpoint, 
            num_labels = num_labels
        )
        # Attach the LoRA adapter
        self.model = PeftModel.from_pretrained(base, adapter_dir)
        # move model weights to GPU or CPU device
        self.model.to(self.device)
        # switch model from training mode to evaluation mode (disable the dropout, all activations are used)
        self.model.eval()

    # do the prediction in inference mode (disable gradient tracking, reduce memory usage,...)
    @torch.inference_mode()
    def predict(self, text: str):
        # Converts text -> token IDs
        # Moves tensors to GPU/CPU, perform truncation, padding, cut long texts
        enc = self.tokenizer(text, truncation=True, padding=True, return_tensors="pt").to(self.device)
        # run forward pass to get logits = h(x)(W+ΔW) + b
        out = self.model(**enc)
        # out.logits is a PyTorch tensor and by default, PyTorch tracks operations on tensors so it could compute gradients later
        # [0]: Select first item in the batch (actually, we have 1 item in the batch bc we input only 1 text)
        # .detach(): remove this tensor from computation graph
        # move tensor to CPU memory and convert to Numpy array
        logits = out.logits[0].detach().cpu().numpy()
        # get the predict label id
        pred_id = int(np.argmax(logits))
        # get the predict label text from label id, if no value returned, assign that pred_id to label
        label = self.id2label.get(str(pred_id), str(pred_id))
        print("label text in intent classifier ", label)
        # Take the model’s raw scores → convert them into probabilities 
        # → pick the probability of the predicted intent → [0, pred_id]: pick prob at row 0 and col pred_id (at this time we have only 1 row or 1 sample).
        # detach(): Removes this tensor from PyTorch’s computation graph, Prevents gradient tracking
        # logits has shape batch_size x num_labels; dim=-1 means compute softmax across the last axis (the num_label axis)
        confidence = float(torch.softmax(out.logits, dim=-1)[0, pred_id].detach().cpu().item())
        return {"intent_id": pred_id, "intent": label, "confidence": confidence}
