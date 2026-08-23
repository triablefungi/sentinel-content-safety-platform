# Baseline Toxicity Classifier Model Card

## Model overview

| Field         | Value                                        |
| ------------- | -------------------------------------------- |
| Model name    | Sentinel TF-IDF Logistic Regression Baseline |
| Model version | `tfidf-logreg-v1`                            |
| Model type    | Binary text classifier                       |
| Task          | Toxicity detection                           |
| Language      | English                                      |
| Training date | 23 August 2026                               |
| Framework     | Scikit-learn                                 |
| Status        | Experimental baseline; not production-ready  |

## Purpose

This model establishes a reproducible machine-learning baseline for the Sentinel Content Safety Platform. It estimates the probability that a piece of user-generated text is toxic.

The baseline provides a measurable reference against which later transformer-based classifiers can be evaluated. It is also integrated into Sentinel’s layered moderation pipeline alongside deterministic heuristics and a versioned policy engine.

## Intended uses

The model is intended for:

* Research and portfolio demonstration.
* Comparing classical NLP methods with transformer-based models.
* Testing model integration, versioning and policy orchestration.
* Prioritising potentially harmful content for review.
* Demonstrating safety-oriented model evaluation and monitoring.

## Out-of-scope uses

The model should not be used as:

* A standalone production moderation system.
* The sole basis for punitive action against a user.
* A classifier for languages other than English.
* A replacement for trained human moderators.
* A system for making legal, employment, educational or financial decisions.
* A reliable detector of threats, misinformation or policy violations requiring contextual understanding.

## Training data

The model was trained using a reproducible 20,000-row sample from the [Civil Comments dataset](https://huggingface.co/datasets/google/civil_comments).

Civil Comments contains public comments published on independent news sites between 2015 and 2017. The dataset includes toxicity scores produced through human annotation.

### Data split

| Split                          |   Rows |
| ------------------------------ | -----: |
| Complete sample                | 20,000 |
| Training set                   | 16,000 |
| Test set                       |  4,000 |
| Toxic examples in test set     |    310 |
| Non-toxic examples in test set |  3,690 |

A comment was assigned a positive toxicity label when its dataset toxicity score was greater than or equal to `0.5`.

The positive toxicity rate in the sampled dataset was approximately 7.75%, creating a significant class-imbalance problem.

## Model architecture

The model uses a Scikit-learn pipeline containing:

1. A TF-IDF vectorizer.
2. Unigram and bigram text features.
3. A maximum vocabulary of 50,000 features.
4. Sublinear term-frequency scaling.
5. Logistic regression with balanced class weights.

Balanced class weights were used to reduce the tendency to predict the majority non-toxic class.

## Evaluation results

The model was evaluated on a stratified 4,000-row holdout test set using a classification threshold of `0.5`.

| Metric              | Result |
| ------------------- | -----: |
| Accuracy            |  0.917 |
| ROC-AUC             |  0.843 |
| Average precision   |  0.474 |
| Toxic precision     |  0.464 |
| Toxic recall        |  0.461 |
| Toxic F1            |  0.463 |
| Non-toxic precision |  0.955 |
| Non-toxic recall    |  0.955 |
| Macro F1            |  0.709 |
| Weighted F1         |  0.917 |

### Confusion matrix

| Actual class | Predicted non-toxic | Predicted toxic |
| ------------ | ------------------: | --------------: |
| Non-toxic    |               3,525 |             165 |
| Toxic        |                 167 |             143 |

The model correctly identified 143 toxic comments but failed to detect 167. It also incorrectly classified 165 non-toxic comments as toxic.

This corresponds to:

* A toxic false-negative rate of approximately 53.9%.
* A non-toxic false-positive rate of approximately 4.5%.

## Interpretation

The 91.7% accuracy should not be interpreted as strong safety performance. Because approximately 92.25% of the sampled comments were non-toxic, a model can achieve high overall accuracy while still missing a large proportion of harmful content.

Toxic recall, false-negative rate, precision-recall performance and category-specific metrics are more meaningful for this use case.

The ROC-AUC of 0.843 indicates that the model has reasonable ranking ability. However, the toxic F1 score of 0.463 and false-negative rate of 53.9% show that the current decision threshold and model architecture are insufficient for production safety enforcement.

## Serving policy

The evaluation report uses a probability threshold of `0.5` to calculate binary classification metrics.

The Sentinel API applies a separate policy layer:

| Toxicity probability | Default policy action                         |
| -------------------- | --------------------------------------------- |
| Below 0.50           | Allow unless another safety signal is present |
| 0.50–0.84            | Send for review                               |
| 0.85 or above        | Block                                         |

These thresholds are initial engineering assumptions and have not yet been calibrated for production deployment.

Deterministic heuristic signals can override the ML result when explicit high-severity patterns are detected.

## Known limitations

### Limited contextual understanding

TF-IDF represents lexical patterns rather than the complete meaning of a sentence. It may struggle with:

* Sarcasm.
* Quoted harmful language.
* Counterspeech.
* Coded or indirect abuse.
* Long-range dependencies.
* Conversation history.
* Reclaimed identity language.
* Threats that require real-world context.

### Class imbalance

Only 7.75% of the sampled examples were labelled toxic. Accuracy and weighted metrics are therefore dominated by the non-toxic class.

### Historical and domain limitations

The data originated from news-site comments published between 2015 and 2017. Language, abuse strategies and online communities have changed since the data was collected.

### Annotation uncertainty

Toxicity is subjective and context-dependent. Human annotators may disagree, and the `0.5` labelling threshold simplifies continuous annotation scores into a binary label.

### Identity-related bias

Toxicity classifiers may incorrectly associate identity terms with harmful content. Subgroup false-positive and false-negative rates have not yet been measured for this model.

### Adversarial robustness

The baseline has not been systematically evaluated against homoglyphs, spacing attacks, deliberate misspellings or semantic paraphrasing. Sentinel’s normalization and heuristic layers provide limited additional protection, but they do not solve the underlying model weakness.

### Probability calibration

The logistic-regression probability has not yet been formally calibrated. A score of `0.80` should not be interpreted as proof that content has an 80% probability of being toxic.

## Ethical and safety considerations

* High-risk or uncertain decisions should be reviewed by a trained human moderator.
* Users should have access to understandable reason codes and an appeal mechanism.
* Model outputs should be logged with the model and policy versions used.
* Raw user content should be protected through appropriate retention and access controls.
* Performance should be monitored across relevant demographic and linguistic groups.
* Model updates should not be deployed when safety-critical metrics regress.
* Automated decisions should be reversible where practical.
* LLM or classifier output should not be treated as unquestionable ground truth.

## Monitoring recommendations

A production implementation should monitor:

* Toxic prediction rate.
* Per-category precision and recall.
* False-negative and false-positive rates.
* Score-distribution drift.
* Input-language distribution.
* Model inference latency.
* Model timeout and error rate.
* Human-review disagreement rate.
* Appeal and reversal rate.
* Performance across identity subgroups.
* Changes in adversarial evasion patterns.

## Planned improvements

1. Evaluate precision and recall across multiple decision thresholds.
2. Select thresholds based on explicit safety and review-capacity objectives.
3. Add probability calibration.
4. Measure subgroup performance and unintended identity bias.
5. Create an adversarial evaluation dataset.
6. Fine-tune a transformer-based classifier.
7. Compare the transformer against this baseline using the same test split.
8. Add model versioning and experiment tracking through MLflow.
9. Introduce human-review feedback and controlled retraining workflows.
10. Export the selected model to ONNX for efficient CPU inference.

## Reproducibility

The dataset download, preprocessing, training and evaluation steps are implemented as version-controlled scripts:

```text
scripts/download_data.py
scripts/train_baseline.py
```

Generated datasets and serialized model files are excluded from Git because of their size and content. Evaluation metrics are retained as a reproducible project artifact.
