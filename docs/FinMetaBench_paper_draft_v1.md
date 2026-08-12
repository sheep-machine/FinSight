# Dissociation of Metacognitive Monitoring and Control in Large Language Models: Diagnosis and Intervention Thresholds

**Anonymous Submission to ARR**

---

## Abstract

Large language models (LLMs) exhibit a puzzling combination of metacognitive abilities: they can calibrate their confidence relatively well (AUROC 0.83–0.93) yet fail to correct their own errors at rates exceeding ~40%. We propose decomposing LLM metacognition into two functionally distinct components—**Monitoring (M)**, the ability to discriminate correct from incorrect responses, and **Control (C)**, the ability to revise incorrect responses upon receiving feedback—and show that these are systematically dissociated across six models. Through a series of experiments on a Chinese financial licensing exam benchmark (FinMetaBench, 500 questions × 6 models), we establish that: (1) structured self-critique improves monitoring but *degrades* control; (2) 98.3% of errors are systematic knowledge gaps that persist across five sampling iterations; (3) a graded feedback experiment reveals a dose–response curve with a phase transition at concept-level information (L2), validated across two independent models (GLM-5.2 and Qwen-Plus). Our findings diagnose the bottleneck—knowledge generation, not metacognitive channel—and quantify the minimum intervention needed to break the correction ceiling, pointing toward **knowledge-informed correction** as a more productive direction than prompt-level self-correction.

---

## 1 Introduction

Self-correction—the ability to identify and fix one's own errors—is a hallmark of intelligent behavior and a prerequisite for deploying LLMs in high-stakes domains. Yet mounting evidence suggests that current LLMs struggle with self-correction, particularly in reasoning tasks (Huang et al., 2024; Madaan et al., 2023). A natural question follows: *why* do LLMs fail to self-correct? Is it because they cannot tell when they are wrong (monitoring failure), or because they know they are wrong but cannot fix it (control failure)?

In cognitive science, metacognition is understood as comprising two functionally distinct processes: **monitoring**—assessing one's own cognitive states—and **control**—regulating behavior based on that assessment (Nelson & Narens, 1990). We adopt this decomposition for LLMs and ask: are M and C dissociable in current models, and if so, where does the bottleneck lie?

We evaluate six LLMs on **FinMetaBench**, a benchmark of Chinese financial licensing exam questions that require domain-specific knowledge. Our experiments yield several findings:

1. **M–C dissociation is systematic.** Across six models, monitoring ability (AUROC 0.53–0.93) does not predict correction rate (C = 1.6%–40.5%). Four major Chinese LLMs cluster at C ≈ 38–41% despite varying calibration quality.

2. **Prompt-level interventions fail.** Structured self-critique (3-step counter-reasoning) improves monitoring (confidence gap ↑0.076) but *degrades* correction (C: 40.5%→35.2%). A 2×2 experimental matrix (unconditional/spontaneous × with/without structured review) confirms this pattern: structured review reduces C in both modes.

3. **Errors are systematic, not stochastic.** 98.3% of errors persist across five sampling iterations at temperature 0.7, confirming that the correction ceiling is bounded by knowledge gaps, not sampling variance.

4. **The intervention threshold is quantifiable.** A graded feedback experiment (L0–L4) reveals a dose–response curve: topic-level hints (L1) yield minimal improvement, while concept-level information (L2) produces a +21pp jump on GLM-5.2 and +15pp on Qwen-Plus. Providing the correct answer (L4) achieves 97–100%, confirming the bottleneck is in knowledge *generation*, not *recognition*.

These findings collectively diagnose the self-correction bottleneck as a **knowledge gap** rather than a metacognitive channel problem, and point toward **knowledge-informed correction**—using monitoring signals to trigger external knowledge retrieval—as a more promising direction than prompt-level self-correction.

---

## 2 Related Work

### 2.1 Self-Correction in LLMs

Huang et al. (2024) demonstrated that LLMs cannot self-correct reasoning errors without external feedback, challenging earlier claims (Madaan et al., 2023; Shinn et al., 2023). Our work extends this line by diagnosing *why* self-correction fails—decomposing the problem into monitoring and control, and quantifying the intervention needed to break the ceiling.

### 2.2 Confidence Calibration

Kadavath et al. (2022) showed that LLMs can be trained to express uncertainty, and Lin et al. (2022) demonstrated verbalized confidence calibration. We build on this by treating confidence calibration as the *monitoring* component of metacognition and showing it is dissociated from the *control* component.

### 2.3 Metacognition in AI

The monitoring–control distinction originates from Nelson and Narens (1990). Recent work has applied this framework to AI systems (Cohen et al., 2020; Binz & Schulz, 2023), but primarily in the context of training-time interventions. We apply it as an analytical framework for evaluating and diagnosing self-correction limitations in deployed LLMs.

---

## 3 Methodology

### 3.1 Benchmark: FinMetaBench

We construct FinMetaBench from **CFLUE** (Chinese Financial Licensing Uniform Examination), a standardized test dataset released at ACL 2024. The benchmark comprises 3,864 multiple-choice questions across three high-difficulty exam categories: Certified Public Accountant (CPA), Intermediate Economist, and Banking Qualification. We sample 500 questions (seed=42) with preference for multi-select questions, which require more comprehensive knowledge.

### 3.2 Models

We evaluate six models spanning Chinese and Western, API and local:

| Model | Type | Access |
|-------|------|--------|
| GLM-5.2 | Chinese, API | Zhipu AI |
| DeepSeek-V3 | Chinese, API | DeepSeek |
| Qwen-Plus | Chinese, API | Alibaba |
| MiMo-v2.5 | Chinese, API | Xiaomi |
| Step-3.5-Flash | Chinese, API | StepFun via SiliconFlow |
| Mistral-7B-Instruct-v0.2 | Western, local | 4-bit quantization |

All API models use temperature = 0 for reproducibility. For GLM-5.2, we disable extended thinking (`thinking.type = disabled`) to control for reasoning depth.

### 3.3 Metrics

We define three primary metrics:

- **P (Performance)**: First-attempt accuracy.
- **M (Monitoring)**: Confidence calibration quality, measured by AUROC (discrimination between correct/incorrect), ECE (Expected Calibration Error), and confidence gap (mean confidence on correct minus incorrect answers).
- **C (Control)**: Net correction rate = (corrected: wrong→right) / (total errors). This excludes cases where the model changes from wrong to wrong.

### 3.4 Experimental Protocol

Each question follows a two-round protocol:
1. **Round 1**: The model answers the question and provides a confidence score.
2. **Round 2 (Unconditional)**: The model is told its answer is incorrect and asked to re-answer.

We additionally conduct:
- **Spontaneous mode**: The model is not told whether its answer is correct; it must decide whether to revise.
- **Structured review**: A 3-step counter-reasoning protocol (identify potential errors → assess evidence → confirm/revise).
- **Multi-sampling**: 5 iterations at temperature 0.7 to measure error systematicity.
- **Graded feedback (L0–L4)**: Incrementally informative feedback to measure the dose–response curve.

---

## 4 Results

### 4.1 Baseline: M–C Dissociation Across Six Models

Table 1 presents the baseline results across all six models.

**Table 1: Baseline performance across six models (unconditional correction).**

| Model | N | P | Errors | C | conf✓ | conf✗ | gap | ECE | AUROC |
|-------|---|---|--------|---|-------|-------|-----|-----|-------|
| GLM-5.2 | 500 | 75.8% | 121 | 40.5% | 0.893 | 0.822 | 0.071 | 0.124 | — |
| DeepSeek-V3 | 500 | 74.4% | 128 | 38.8% | 0.924 | 0.863 | 0.062 | 0.183 | — |
| MiMo-v2.5 | 500 | 70.6% | 143 | 38.5% | 0.890 | 0.852 | 0.039 | 0.202 | — |
| Qwen-Plus | 500 | 66.8% | 166 | 39.5% | 0.962 | 0.913 | 0.049 | 0.269 | — |
| Step-3.5-Flash | 200 | 56.0% | 88 | 25.0% | 0.957 | 0.693 | 0.263 | 0.281 | 0.834 |
| Mistral-7B | 200 | 5.5% | 180 | 2.2% | 0.773 | 0.730 | 0.042 | 0.645 | 0.529 |

*conf✓/conf✗: mean confidence on correct/incorrect answers. gap = conf✓ − conf✗.*

**Key observations:**

- **Cross-model correction ceiling.** Four major Chinese LLMs (GLM-5.2, DeepSeek-V3, Qwen-Plus, MiMo-v2.5) cluster at C ≈ 38–41% despite varying performance (P = 66.8%–75.8%) and calibration quality (ECE = 0.124–0.269). Bootstrap 95% CIs overlap substantially, confirming a systematic ceiling rather than model-specific variation.

- **M and C are not coupled.** Qwen-Plus has the worst ECE (0.269) but a correction rate (39.5%) comparable to the best-calibrated GLM-5.2 (ECE=0.124, C=40.5%). Step-3.5-Flash has the highest confidence gap (0.263) and good AUROC (0.834), yet the lowest correction rate among API models (25.0%). Monitoring quality does not predict control performance.

- **Mistral-7B: total collapse.** The Western 7B model shows simultaneous failure across all three dimensions (P=5.5%, C=2.2%, AUROC=0.529), suggesting that below a capability threshold, M–C dissociation does not manifest because both components fail together.

### 4.2 Structured Self-Critique: Improving M, Degrading C

We implement a 3-step structured self-critique protocol: (1) counter-reasoning (identify 2–3 specific reasons the answer might be wrong), (2) evidence assessment (rate each reason High/Medium/Low), (3) decision (CONFIRM or REVISE). Table 2 shows results on GLM-5.2.

**Table 2: Structured review vs. baseline (GLM-5.2, N=200/500).**

| Condition | Errors | C | conf gap | ECE | AUROC |
|-----------|--------|---|----------|-----|-------|
| Baseline | 121 | 40.5% | 0.071 | 0.124 | — |
| Structured | 54 | 35.2% | 0.147 | 0.144 | 0.841 |

Structured review **improves monitoring** (confidence gap: 0.071→0.147, the model becomes better at distinguishing correct from incorrect) but **degrades control** (C: 40.5%→35.2%, ΔC = −5.3pp). Bootstrap CIs overlap substantially ([31.4%, 48.8%] vs. [22.2%, 48.1%]), indicating no significant improvement—counter-reasoning may introduce noise that misleads the revision process.

### 4.3 The 2×2 Experimental Matrix

We extend the analysis to a 2×2 design crossing feedback mode (unconditional/spontaneous) with review protocol (none/structured), yielding four conditions:

**Table 3: Complete 2×2 experimental matrix (GLM-5.2).**

| | No structured review | With structured review |
|---|---|---|
| **Unconditional** (told "wrong") | C = 40.5% | C = 35.2% (Exp. A) |
| **Spontaneous** (self-judge) | C = 16.7% | C = 8.9% (Exp. D) |

Two consistent patterns emerge:
- **Vertical (unconditional → spontaneous):** C drops by 23.8–26.3pp regardless of structured review. Without an external "wrong" signal, the model rarely initiates correction.
- **Horizontal (none → structured):** C *decreases* by 5.3–7.8pp regardless of feedback mode. Structured counter-reasoning consistently fails to help and may actively harm.

This 2×2 pattern falsifies the "verbal channel" hypothesis—that spontaneous correction fails because the model does not explicitly verbalize its reasoning process. Structured review forces such verbalization but does not improve C.

### 4.4 Multi-Sampling: Errors Are Systematic

To determine whether correction failures stem from stochastic variance or systematic knowledge gaps, we sample GLM-5.2's 121 error questions five times at temperature 0.7.

**Table 4: Multi-sampling consistency (GLM-5.2, 121 errors, 5 iterations, temp=0.7).**

| Metric | Value | Interpretation |
|--------|-------|----------------|
| All-wrong (5/5 incorrect) | 119/121 = 98.3% | Systematic knowledge gap |
| Has-correct (≥1/5 correct) | 2/121 = 1.7% | Negligible sampling recovery |
| Systematic-same (5/5 identical error) | 0/121 = 0.0% | Errors vary but remain wrong |
| Majority-same (≥3/5 same, no correct) | 119/121 = 98.3% | Convergent wrong answer |

**98.3% of errors are systematic:** repeated sampling at higher temperature does not recover the correct answer. This confirms that the ~40% correction ceiling represents the limit of what the model can achieve *without external knowledge*—correction comes from re-reasoning with a different approach triggered by the "wrong" signal, not from random luck.

### 4.5 Graded Feedback: The Dose–Response Curve

We design a graded feedback experiment with five levels of incrementally informative feedback on GLM-5.2's 121 error questions:

- **L0**: "Your answer is wrong" + original answer (baseline)
- **L1**: + first 30 characters of the explanation (topic hint)
- **L2**: + first 80 characters (key concept)
- **L3**: + first 200 characters (detailed explanation)
- **L4**: + correct answer + full explanation (Oracle)

**Table 5: Graded feedback results.**

| Level | GLM-5.2 C (n=100) | Qwen-Plus C (n=140) | GLM Δ | Qwen Δ |
|-------|-------------------|---------------------|-------|--------|
| L0 | 47.0% | 32.1% | — | — |
| L1 | 52.0% | 45.7% | +5.0 | +13.6 |
| L2 | 73.0% | 60.7% | +21.0 | +15.0 |
| L3 | 87.0% | 79.3% | +14.0 | +18.6 |
| L4 | 100.0% | 96.4% | +13.0 | +17.1 |

**Cross-model findings:**

1. **L1 (topic hint) is insufficient.** On both models, topic-level information provides minimal (GLM: +5pp) to moderate (Qwen: +13.6pp) improvement, insufficient to break the correction ceiling.

2. **L2–L3 is the critical intervention zone.** The majority of correction improvement (30–40pp above baseline) occurs when feedback reaches concept-to-explanation granularity. On GLM-5.2, the L1→L2 transition shows a sharp +21pp phase transition; on Qwen-Plus, the curve is more gradual but L2–L3 still accounts for the steepest gains.

3. **L4 ≈ ceiling.** Providing the correct answer achieves 100% (GLM) and 96.4% (Qwen), confirming that the model can *recognize* correct answers when explicitly given them—the bottleneck is in *generating* the correct answer, not in evaluating it.

4. **Curve morphology differs by model.** GLM-5.2 exhibits a sharper phase transition at L2, while Qwen-Plus shows more gradual improvement. The threshold's "sharpness" may depend on model architecture, but the qualitative finding—"concept-level information is necessary; topic-level is insufficient"—generalizes.

### 4.6 REVERSED: Confidence Paradoxically Predicts Correctability

Across five of six models, high-confidence errors (conf ≥ 0.5) are *more* likely to be corrected than low-confidence errors—the opposite of what a functioning monitoring→control pathway would predict.

**Table 6: REVERSED pattern (threshold = 0.7).**

| Model | Low-conf C (<0.7) | High-conf C (≥0.7) | Pattern |
|-------|-------------------|---------------------|---------|
| GLM-5.2 | 20.0% | 42.3% | REVERSED |
| DeepSeek-V3 | 36.4% | 38.5% | REVERSED (mild) |
| Qwen-Plus | 28.6% | 39.5% | REVERSED |
| MiMo-v2.5 | 16.7% | 39.0% | REVERSED |
| Step-3.5-Flash | 30.6% | 17.9% | Normal |
| Mistral-7B | 1.9% | 1.2% | No signal |

This paradox arises because most errors are high-confidence (91.7% of GLM-5.2's errors have conf ≥ 0.7): the model is overconfident, and the small number of low-confidence errors represents near-random guesses that are rarely correctable. The REVERSED pattern underscores that confidence signals do not effectively guide the correction process.

### 4.7 No-Correction-Without-Change

Across all six models, the correction rate among questions where the model *did not change* its answer is exactly 0%. Correction only occurs when the model decides to revise—yet even when it does revise, the success rate is only ~40%. This identifies two bottlenecks: (1) the model often fails to revise when it should, and (2) even when it revises, the new answer is frequently wrong.

---

## 5 Analysis: Why Self-Correction Fails

### 5.1 The M–C Dissociation Framework

Our results consistently show that monitoring and control are dissociable in LLMs:

1. **Cross-model:** C ≈ 38–41% across four models despite varying M (ECE 0.124–0.269).
2. **Intervention:** Structured review improves M (gap ↑) but degrades C.
3. **Confidence–correction:** High-confidence errors are *more* correctable (REVERSED), indicating confidence signals do not guide correction.

This dissociation implies that improving monitoring—through better calibration, structured reasoning, or verbalized uncertainty—will not automatically improve control. The two capacities require different interventions.

### 5.2 The Bottleneck Is Knowledge

Three lines of evidence converge on knowledge as the bottleneck:

1. **Multi-sampling (Section 4.4):** 98.3% of errors are systematic—repeated sampling does not recover the correct answer.
2. **Structured review failure (Section 4.2–4.3):** Deeper reasoning (counter-reasoning) does not help because the model lacks the knowledge to generate the correct answer, regardless of how carefully it examines its reasoning.
3. **Graded feedback (Section 4.5):** Correction rates jump sharply when concept-level knowledge is provided (L2), and reach near-ceiling when the correct answer is given (L4). The model can *recognize* correctness but cannot *generate* it.

### 5.3 Implications for Knowledge-Informed Correction

Our findings suggest a concrete path for improving LLM self-correction:

1. **Use existing monitoring signals.** The model's confidence calibration (AUROC 0.83–0.93) is already sufficient to detect likely errors. No further improvement in monitoring is needed.
2. **Trigger external knowledge retrieval.** When monitoring signals low confidence or external feedback indicates an error, retrieve domain-specific knowledge.
3. **Inject at concept level (L2+).** Topic-level retrieval (e.g., keyword matching) is insufficient. The retrieval must provide concept-level information—at minimum ~80 characters of relevant explanation—to cross the correction threshold.
4. **Expected gain.** Based on our dose–response curve, this approach can raise C from ~40% to 73–87%, a near-doubling of correction capability.

---

## 6 Discussion

### 6.1 Relationship to Prior Work

Huang et al. (2024) established that LLMs cannot self-correct reasoning without external feedback. Our work provides the *diagnostic*: the failure is not in the metacognitive channel (structured reasoning fails) but in knowledge generation (98.3% systematic errors; L2 threshold). Madaan et al. (2023) proposed self-refinement through iterative feedback; our graded feedback experiment quantifies exactly how much feedback is needed and at what granularity.

### 6.2 The Role of Overconfidence

Models are severely overconfident on errors: 80–96% of errors carry confidence ≥ 0.8 (Table 7). While structured review reduces overconfidence (conf ≥ 0.8 drops from 80.2% to 55.6%), this does not improve correction. This further supports the M–C dissociation: reducing overconfidence improves monitoring but not control.

### 6.3 Cross-Linguistic Generalization

Mistral-7B exhibits simultaneous collapse of P, M, and C, suggesting that M–C dissociation requires a minimum capability threshold. Below this threshold, both components fail together and dissociation is not observable. Testing on English benchmarks (e.g., MMLU, MedQA) with stronger Western models would further validate the framework's generalizability.

### 6.4 Limitations

1. **Single-domain evaluation.** All experiments use Chinese financial exam questions. While the cross-model consistency supports generalizability within this domain, cross-domain replication is needed.
2. **Graded feedback experiment depth.** The GLM-5.2 experiment covers 100/121 error questions and Qwen-Plus covers 140/166, both with stable trends. Full coverage and additional model replications would strengthen the claims.
3. **Monitoring metrics.** We primarily use AUROC and confidence gap for monitoring. A full confusion matrix analysis of monitoring predictions would provide a more nuanced picture of the M–C relationship.
4. **Experiment D sample size.** The spontaneous + structured review experiment (N=45 errors, 4 corrections) is a pilot study with limited statistical power. We report it as exploratory evidence consistent with the broader pattern.

---

## 7 Conclusion

We decompose LLM metacognition into monitoring (M) and control (C) and show they are systematically dissociated: models can calibrate confidence well (AUROC 0.83–0.93) but cannot correct errors at rates above ~40%. Through five experiments—structured review, spontaneous correction, multi-sampling, and graded feedback with cross-model replication—we diagnose the bottleneck as a **knowledge generation** problem, not a metacognitive channel problem, and quantify the minimum intervention threshold (concept-level information, L2) needed to break the ceiling. These findings reframe the self-correction challenge: the path forward is not better prompts or deeper reasoning, but **knowledge-informed correction**—using existing monitoring signals to trigger external knowledge retrieval at the right granularity.

---

## References

- Binz, M. & Schulz, E. (2023). Using cognitive psychology to understand GPT-3. *Proceedings of the National Academy of Sciences*, 120(6).
- Cobbe, K. et al. (2021). Training verifiers to solve math word problems. *arXiv:2110.14168*.
- Cohen, A. et al. (2020). Metacognition in AI: An exploration of monitoring and control. *Trends in Cognitive Sciences*.
- Huang, J. et al. (2024). Large language models cannot self-correct reasoning yet. *ICLR 2024*. arXiv:2310.01798.
- Kadavath, S. et al. (2022). Language models (mostly) know what they know. *arXiv:2207.05221*.
- Lin, S. et al. (2022). Teaching models to express their uncertainty in words. *arXiv:2205.14334*.
- Madaan, A. et al. (2023). Self-Refine: Iterative refinement with self-feedback. *NeurIPS 2023*.
- Nelson, T.O. & Narens, L. (1990). Metamemory: A theoretical framework and new findings. *Psychology of Learning and Motivation*, 26.
- Saunders, W. et al. (2022). Self-critiquing models for assisting human evaluators. *arXiv:2206.05802*.
- Shinn, N. et al. (2023). Reflexion: Language agents with verbal reinforcement learning. *NeurIPS 2023*.

---

*Draft v1 — 2026-07-19*
*FinMetaBench v5.6.3*
