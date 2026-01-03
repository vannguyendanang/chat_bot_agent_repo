import pandas as pd
from sklearn.model_selection import train_test_split
from datasets import load_dataset, DatasetDict, Dataset, ClassLabel, Features
from transformers import (
    AutoTokenizer,
    AutoConfig,
    AutoModelForSequenceClassification,
    DataCollatorWithPadding,
    TrainingArguments,
    Trainer
)

from peft import PeftModel, PeftConfig, get_peft_model, LoraConfig
import evaluate
import torch
import numpy as np

# train_hf = pd.read_json("./data/train_bank_intent.jsonl", lines=True)
# test_hf = pd.read_json("./data/test_bank_intent.jsonl", lines=True)

dataset = load_dataset(
    "json",
    data_files={"train": "./data/train_bank_intent.jsonl",
                "test": "./data/test_bank_intent.jsonl"}
)
train_hf = dataset["train"]
test_hf = dataset["test"]

# Data type of train_hf: 
print("Data type of train_hf ", type(train_hf))
print("Shape of trainning set:", train_hf.num_rows, train_hf.num_columns)
print("Shape of testing set:", test_hf.num_rows, test_hf.num_columns)
print("Sort label in train set ", np.sort(list(set(train_hf["label"]))))
print("Count total label in train set ", len(set(train_hf["label"])))

print("Sort label in test set ", np.sort(list(set(test_hf["label"]))))
print("Count total label in test set ", len(set(test_hf["label"])))

print("Count label text in train set ", len(set(train_hf["label_text"])))
print("Count label text in test set ", len(set(test_hf["label_text"])))


# inspect labels
print("Features in train set ",train_hf.features)
# print("First several label ",train_hf.unique("label")[:20])

# create a copy version of features of the training set
# new_features has type datasets.Features
new_features = train_hf.features.copy()

# redefine the type of the label column
label_uni_val = set(train_hf["label"])
# make sure the label column has continuous values
if label_uni_val != set(range(min(label_uni_val),max(label_uni_val) + 1)):
    raise ValueError(f"Values of label column are not continuous numbers. Dataset is invalid")

num_class = len(set(train_hf["label"]))
new_features["label"] = ClassLabel(num_classes=num_class)

# convert the data scheme of train_hf and still keep the values
train_hf = train_hf.cast(new_features)

# split validation set from the training set 
splits = train_hf.train_test_split(test_size=0.2, seed=42, stratify_by_column="label")
dataset = DatasetDict({
    "train": splits["train"],
    "validation": splits["test"],
    "test": dataset["test"]
})

# mapping from label id to label text and save in id2label dict
# mapping from label text to label id and save in label2id dict
def labelmapping(hf: Dataset, numUniqueLabel):
    id2label = {}
    label2id = {}
    # # for index, rec in df.iterrows():
    # for rec in df:
    #     lab = int(rec["label"])
    #     txt = rec["label_text"]
    #     # lab = int(getattr(rec, "label"))
    #     # txt = getattr(rec, "label_text")

    #     # throw error if one label is mapped to two different text
    #     if lab in id2label and id2label[lab] != txt:
    #         raise ValueError(f"Value {lab} is mapped to both {id2label[lab]} and {txt}")
        
    #     # throw error if one text is mapped to two different labels
    #     if txt in label2id and label2id[txt] != lab:
    #         raise ValueError(f"Value {txt} is mapped to both {label2id[txt]} and {lab}")
        
    #     id2label[lab] = txt
    #     label2id[txt] = lab

    # # check if there is any missing or redundant index in the id2label dict
    # expect = set(range(numUniqueLabel))
    # missing = expect - set(id2label.keys())
    # extra = set(id2label.keys()) - expect

    # # If there are items in set missing or extra then throw error
    # if missing or extra:
    #     raise ValueError(f"There are missing indices {missing} or extra indices {extra} in the mapping from index to text")

    # select a temp df that include 2 columns and remove all duplicate rows
    temp = hf.select_columns(["label", "label_text"]).to_pandas().drop_duplicates()

    # check if one label is mapped to two different label text
    # label_count is a pandas Series
    label_count = temp.groupby(["label"])["label_text"].nunique()
    if (label_count > 1).any():
        bad_rec = label_count[label_count > 1]
        raise ValueError(f"Label mapped to multiple label texts:\n {bad_rec}")

    # check if one label text is mapped to two different labels
    text_count = temp.groupby("label_text")["label"].nunique()
    if (text_count > 1).any():
        bad_rec = text_count[text_count > 1]
        raise ValueError(f"Label text mapped to multiple labels:\n{bad_rec}")
    
    # build mapping
    # dict(zip(...)): pair the 2 columns and then build a dict for these 2 columns
    id2label = dict(zip(temp["label"], temp["label_text"]))
    label2id = dict(zip(temp["label_text"], temp["label"]))

    # print("List of intents ", label2id.keys())
    return id2label, label2id

# get label mapping of training/test set
# numUniqueLabel = len(set(train_hf["label"]))
train_id2label, train_label2id = labelmapping(train_hf, num_class)
test_id2label, test_label2id = labelmapping(test_hf, num_class)

# make sure the test set also has the same number of labels as the training set
if not (train_id2label == test_id2label and train_label2id == test_label2id):
    missing_label = set(train_id2label.keys()) - set(test_id2label.keys())
    extra_label = set(test_id2label.keys()) - set(train_id2label.keys())
    missing_text = set(train_label2id.keys()) - set(test_label2id.keys())
    extra_text = set(test_label2id.keys()) - set(train_label2id.keys())

    if missing_label or extra_label:
        raise ValueError(f"Labels in train and text are different which is missing at test {missing_label} and extra at train {extra_label}")

    if missing_text or extra_text:
        raise ValueError(f"Label text in train and text are different which is missing at test {missing_text} and extra at train {extra_text}")

model_checkpoint = 'distilbert-base-uncased'

# generate classification model from model_checkpoint
# load a pretrained encoder (DistilBERT weights)
# Creates a new classification head with size num_labels
# - Classification head takes sentence vector (batch_size x hidden_size) and produce logits: logits = hW + b
# Attaches label metadata (id2label, label2id) for interpretation
model = AutoModelForSequenceClassification.from_pretrained(
    model_checkpoint, num_labels=len(train_id2label.keys()), id2label = train_id2label, label2id = train_label2id
)

# proprocess data
# create tokenizer
# AutoTokenizer.from_pretrained(): 
# - load correct tokenizer class associated with model_checkpoint
# - Download tokenizer vocab (base model's vocab which was learned during pretraining)
# and rules (splitting on whitespace, separating punctuation,...)
# add_prefix_space=True: Add a leading space at the begining of the input text before tokenization
# to separate between tokens
tokenizer = AutoTokenizer.from_pretrained(model_checkpoint, add_prefix_space=True)

# create token id representing tokens
def tokenizer_func(examples):
    # extract text, can be a string (a sentence) or a list of string (multiple sentences - batch)
    text = examples["text"]

    # if a text is longer than max_length, truncation will remove tokens from the right
    tokenizer.truncation_side = "right" # default is on right side
    
    # create integer IDs representing tokens
    tokenizer_inputs = tokenizer(
        text,
        # return_tensors = "np", # returns Numpy arrays instead of Python lists or PyTorch tensors
        truncation=True,
        max_length=128
    )

    # return a dict contains input_ids and attention_mask have size of batch_size x sequence_len
    # attention_mask 1: real tokens, 0: padding tokens
    # For ex: 
    # {
    #    "input_ids": array([[  101,  1045,  2572,  2145,  3401, 0], 
    #                        [2006,  2026,  4003,  1029,  102, 876 ]]),
    #    "attention_mask": array([[1, 1, 1, 1, 1, 0], 
    #                             [1, 1, 1, 1, 1, 1]])
    # }
    # --> batch_size = 2 (2 sentences), sequence_len = 6 (6 tokens)
    return tokenizer_inputs

# add pad token string (ID = 0) into tokenizer's vocab if non exists
if tokenizer.pad_token is None:
    tokenizer.add_special_tokens({'pad_token': '[PAD]'})
    # After adding pad token, the tokenizer vocab size increases
    # --> We need to add a new row to the embedding matrix (has size vocab_size x hidden size) created inside the pretrained model
    model.resize_token_embeddings(len(tokenizer))

# tokenize training and validation datasets
# tokenizer_func will be applied to many dataset rows
# batch=True: Hugging Face passes multiple examples at once to tokenizer_func to speed up processing time
# The result is a new dataset with additional columns from tokenizer_inputs
tokenized_dataset = dataset.map(tokenizer_func, batched=True)
print("tokenized_dataset ",tokenized_dataset)

cols = ["input_ids", "attention_mask", "label"]

# format columns as PyTorch tensors data type
tokenized_dataset["train"].set_format("torch", columns=cols)
tokenized_dataset["validation"].set_format("torch", columns=cols)
tokenized_dataset["test"].set_format("torch",columns=cols)
print("tokenized_dataset after formating",tokenized_dataset)

# create data collator to dynamically fill pad token at the short sequences at batch time
data_collator = DataCollatorWithPadding(tokenizer=tokenizer)

# import accuracy evaluation metric
accuracy = evaluate.load("accuracy")

# define an evaluation func to pass into trainer later
# def compute_metrics(p):
def compute_metrics(eval_pred):
    # logits is a matrix has shape batch_size x num_labels)
    logits = eval_pred.predictions
    # labels (shape batch_size)
    labels = eval_pred.label_ids
    # convert logit to prediction row-wise (axis=1) which is the index label that has max logit
    preds = np.argmax(logits, axis=1)
    # compute and return accuracy metric
    return accuracy.compute(predictions=preds, references=labels)

# task_type = "SEQ_CLS": The task LoRA is doing is sequence classification (intent classification, sentiment,...)
# Other task types can be "CAUSAL_LM" (text generation), "TOKEN_CLS" (token classification), "SEQ_2_SEQ_LM" (translation, summarization)
peft_config = LoraConfig(task_type="SEQ_CLS",
                         r=4, #LoRA rank
                        # Scales the LoRA update before adding it to the frozen weight
                        # Weff = W + (alpha/r).BA 
                         lora_alpha=32, 
                        # Dropout is applied to activation func during the forward pass in training
                        # It randomly sets a fraction (e.g., 1%) of activation values to zero to inject noise so that model does not rely on any singal feature too much
                         lora_dropout=0.01,
                        # Inject LoRA adapters to query projection layer in self-attention
                        # Because query vectors control what a token attends to --> a very effective layer for adaptation
                         target_modules=['q_lin']
                         )

# Frozen base model's weights, only LoRA params are trainable
model = get_peft_model(model, peft_config)
# print out information about which params are trainable
model.print_trainable_parameters()

# hyperparameters
lr = 1e-3 # size of optimization step
batch_size = 4 # number of examples processed per optimization step
num_epochs = 10 # number of times model runs through training data

# define training arguments
training_args = TrainingArguments(
    # directory where Trainer save trained model, training logs, optimizer states
    output_dir = model_checkpoint + "-lora-text-classification",
    # step size used by optimizer when updating parameters, apply to only LoRA params (A&B)
    learning_rate=lr,
    # num of samples processed per device (GPU/CPU) in one forward/backward pass
    # For 1 device: num of steps per epoch = num of samples/per_device_batch_size
    # For 2 device: num of steps per epoch = num of samples/2*per_device_batch_size
    per_device_train_batch_size=batch_size,
    # num of samples processed per device in one forward pass during evaluation process
    # For 2 device: num of samples processed in one forward pass = 2*4 = 8
    # Evaluation runs in num of samples/2*per_device_eval_batch_size steps
    per_device_eval_batch_size=batch_size,

    num_train_epochs=num_epochs,
    # L2 regularization, penalize large weights (discourages Δ𝑊=𝐵𝐴 from becoming too large) to prevent overfitting
    # because large weights --> model's output change a lot for a small change in inputs
    # --> model learns noise, not learn the general patterns --> overfitting issue
    weight_decay=0.01,

    # perform evaluation at the end of each epoch
    eval_strategy="epoch",
    # save one model check point at the end of each epoch
    save_strategy="epoch",
    # After training finishes, Trainer reloads the best checkpoint into trainer.model
    # Best checkpoint is identified based on lowest eval loss by default
    load_best_model_at_end=True,
)

# create Trainer object
# So we provide dataset (inputs + labels). 
# Trainer handles below tasks:
# for epoch:
#   for batch:
#   - Forward pass (compute logits using W+ΔW)
#   - Loss computation
#   - Backward pass (compute gradient for low rank matrices A and B)
#   - Update low rank matrices A & B
#   - zero_grad (remove gradient)
#   Evaluation (use lasted trained weights A,B to compute logits=h(x)(W + ΔW) + b of current epoch

# The Trainer object will produce the below output
# SequenceClassifierOutput(
#     loss=..., # this loss is a scalar, it's loss for each batch and it goes to backward pass during training
#     logits=Tensor[batch_size, num_labels] --> it's passed into compute_metrics during evaluation process
# )
trainer = Trainer(
    model=model,
    args=training_args,
    # set input to base model which is a matrix size batch_size x sequence_len/sentence_len
    # each item in these datasets looks like:
    # {
    # "input_ids": Tensor[seq_len],
    # "attention_mask": Tensor[seq_len],
    # "label": Tensor[] --> This is true index label
    # }
    train_dataset=tokenized_dataset["train"], 
    eval_dataset=tokenized_dataset["validation"],
    tokenizer=tokenizer,
    data_collator=data_collator, #this will dynamically pad examples
    # during evaluation, model passes logits (shape batch_size x num_labels) and labels (shape batch_size)
    # to compute_metrics where we finally can see the output(predictions) and accuracy
    compute_metrics=compute_metrics, #evaluate model using compute_metrics
)

# train model
trainer.train()

# save LoRA adapter/artifacts
output_dir = model_checkpoint + "-lora-text-classification"
trainer.model.save_pretrained(output_dir)
tokenizer.save_pretrained(output_dir)

trainer.evaluate()
trainer.predict(tokenized_dataset["test"])