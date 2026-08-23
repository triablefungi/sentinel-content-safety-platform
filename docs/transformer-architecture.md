# Transformer Architecture Notes

## Why replace the lexical baseline?

TF-IDF treats text mainly as weighted word and phrase counts. It cannot represent meaning well
when wording changes, and it has limited ability to distinguish a direct attack from discussion,
quotation, sarcasm, or counterspeech. A transformer produces contextual token representations,
allowing the meaning of a token to depend on the surrounding sequence.

## DistilBERT used in Sentinel

Sentinel fine-tunes `distilbert-base-uncased`, a smaller student model distilled from BERT. The
encoder contains six transformer blocks. Each block combines multi-head self-attention with a
position-wise feed-forward network, residual connections, dropout, and layer normalization.

For each input, the tokenizer creates token IDs and an attention mask. Self-attention projects
the hidden state into queries, keys, and values. Scaled dot-product attention is computed as:

```text
Attention(Q, K, V) = softmax(QKᵀ / sqrt(d_k))V
```

Multiple attention heads learn different token relationships in parallel. The contextual
representation of the first token is passed to a classification head that produces two logits:
`NON_TOXIC` and `TOXIC`. Softmax converts those logits into normalized scores.

## Activations and training

DistilBERT's feed-forward layers use GELU activations. Unlike ReLU's hard zero boundary, GELU
smoothly weights negative and positive inputs. Fine-tuning updates the pretrained encoder and the
new classification head using class-weighted cross entropy. Class weights counter the roughly
7.75% positive-label rate in the current sample.

## Efficiency decisions

- Sequences are truncated to 256 tokens to bound memory and latency.
- Dynamic padding pads each batch only to its longest sequence.
- Mixed-precision FP16 training is enabled when a CUDA GPU is available.
- The best checkpoint is selected using toxic-class F1, not overall accuracy.
- Training runs in Colab; the saved model supports local CPU inference.
- ONNX export and quantization are planned as a separate deployment milestone.

## Limitations

Transformers improve contextual representation but do not solve content safety. The model can
still learn annotation bias, fail on new abuse strategies, behave inconsistently across identity
groups, and assign confident scores to unfamiliar inputs. It therefore remains one signal inside
a versioned policy system with heuristics, review queues, monitoring, and rollback controls.

