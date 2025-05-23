# STT System Evaluation Summary Report

## TC-1: Multilingual Support

### Input:

Voice datasets for each language (English-US, English-UK, English-HK, Cantonese-HK, Mandarin), with length ranging from 2s to 10s.
Ground truth transcriptions for each clip.


### Output Requirement:

WER (Word Error Rate), WRR (Word Recognition Rate) for each language, and Accuracy for Numbers (Sequence).


### Results:

#### STT Method: google

| Language | Average WER (%) | Average WRR (%) | Average Sequence Accuracy (%) |
| --- | --- | --- | --- |
| Cantonese-HK | 50.81 | 49.19 | N/A |
| Cantonese-HK-Numbers | N/A | N/A | 59.38 |
| English-US | 29.72 | 70.28 | N/A |
| English-US-Numbers | N/A | N/A | 96.88 |
| Mandarin | 65.43 | 56.45 | N/A |
| Mandarin-Numbers | N/A | N/A | 65.62 |


## TC-2: Robustness Across Accents

### Input:

Voice datasets for each language (Cantonese-HK with Mandarin accent, Mandarin with Cantonese accent, English with Southeast Asian accent, English with Indian accent), with length ranging from 2s to 10s.
Ground truth transcriptions for each clip.


### Output Requirement:

WER (Word Error Rate), WRR (Word Recognition Rate) and for each language.


### Results:

#### STT Method: google

| Accent/Language | Average WER (%) | Average WRR (%) |
| --- | --- | --- |
| Cantonese_Mandarin_Accent | 100.00 | 0.00 |
| English_Indian_Accent | 38.99 | 61.90 |
| English_SouthEastAsian_Accent | 37.37 | 73.55 |
| Mandarin_Cantonese_Accent | 100.00 | 0.00 |


## TC-3: Domain Vocabulary Support

### Input:

Voice datasets for each language (English, Cantonese-HK), with length ranging from 2s to 10s, where HSBC specific terms are mentioned.
Ground truth transcriptions for each clip.


### Output Requirement:

WER (Word Error Rate), and (Accuracy) full vocab recognition for each language.


### Results:

#### STT Method: google

| Language | Average WER (%) | Average Vocabulary Accuracy (%) |
| --- | --- | --- |
| Cantonese | 59.34 | 45.38 |
| English | 25.91 | 93.33 |
| Mandarin | 56.40 | 66.67 |


## TC-4: Auto Punctuation Feature

### Input:

Voice datasets for each language (English-US, English-UK, English-HK, Cantonese-HK, Mandarin), with length ranging from 2s to 10s, and clear punctuation syntax (periods, commas, question marks).
Ground truth transcriptions for each clip.


### Output Requirement:

Proportion of correct punctuation (Sentence Sepreation) placements for each language.


### Results:

#### STT Method: google

| Language | Average Segmentation Accuracy (%) |
| --- | --- |
| Cantonese | 0.00 |
| Cantonese-HK | 3.07 |
| Cantonese-HK-Numbers | 0.00 |
| Cantonese-HK-Numbers\noisy_100 | 0.00 |
| Cantonese-HK-Numbers\noisy_25 | 0.00 |
| Cantonese-HK-Numbers\noisy_50 | 0.00 |
| Cantonese-HK-Numbers\noisy_75 | 18.75 |
| Cantonese-HK\noisy_100 | 6.25 |
| Cantonese-HK\noisy_25 | 0.00 |
| Cantonese-HK\noisy_50 | 15.62 |
| Cantonese-HK\noisy_75 | 9.26 |
| Cantonese_Mandarin_Accent | 0.00 |
| English-US | 100.00 |
| English-US-Numbers | 100.00 |
| English-US-Numbers\noisy_100 | 0.00 |
| English-US-Numbers\noisy_25 | 100.00 |
| English-US-Numbers\noisy_50 | 33.33 |
| English-US-Numbers\noisy_75 | 50.00 |
| English-US\noisy_100 | 0.00 |
| English-US\noisy_25 | 100.00 |
| English-US\noisy_50 | 50.00 |
| English-US\noisy_75 | 50.00 |
| English_SouthEastAsian_Accent | 60.94 |
| Mandarin | 30.00 |
| Mandarin-Numbers | 28.21 |
| Mandarin-Numbers\noisy_100 | 0.00 |
| Mandarin-Numbers\noisy_25 | 0.00 |
| Mandarin-Numbers\noisy_50 | 0.00 |
| Mandarin-Numbers\noisy_75 | 12.50 |
| Mandarin\noisy_100 | 5.56 |
| Mandarin\noisy_25 | 10.00 |
| Mandarin\noisy_50 | 0.00 |
| Mandarin\noisy_75 | 0.00 |
| Mandarin_Cantonese_Accent | 0.00 |


## TC-5: Profanity Filtering

### Input:

Voice datasets for each language (English-US, English-UK, English-HK, Cantonese-HK, Mandarin), with length ranging from 2s to 10s, containing profanity vocabulary.
Ground truth transcriptions for each clip.


### Output Requirement:

Rate of profanity vocabulary identified for each language.


### Results:

#### STT Method: google

No valid data to aggregate for this STT method after filtering.

## TC-6: Transcription Speed and Latency

### Input:

Audio clips of lengths: 5-10 seconds.


### Output Requirement:

Actual latency in seconds vs system-reported latency.


### Results:

#### STT Method: google

| Metric | Value |
| --- | --- |
| Average Actual Latency (s) | 1.930 |
| System-Reported Latency (s) | Data not available in source CSV |


## TC-7: Noise Robustness

### Input:

Voice datasets for each language (English-US, English-UK, English-HK, Cantonese-HK, Mandarin) with Numbers (Sequence), with length ranging from 2s to 10s, mixed with various environment noise at different SNR levels.


### Output Requirement:

WER (Word Error Rate), WRR (Word Recognition Rate), and Accuracy for Numbers (Sequence) for each language and noise level.


### Results:

#### STT Method: google

| Language/Condition | Noise Level (%) | Average WER (%) | Average WRR (%) | Average Sequence Accuracy (%) |
| --- | --- | --- | --- | --- |
| Cantonese-HK-Numbers\noisy_100 | 100% | 102.50 | 0.00 | N/A |
| Cantonese-HK-Numbers\noisy_25 | 25% | 86.07 | 13.93 | N/A |
| Cantonese-HK-Numbers\noisy_50 | 50% | 96.05 | 3.95 | N/A |
| Cantonese-HK-Numbers\noisy_75 | 75% | 106.25 | 0.00 | N/A |
| Cantonese-HK\noisy_100 | 100% | 98.26 | 1.74 | N/A |
| Cantonese-HK\noisy_25 | 25% | 82.18 | 17.82 | N/A |
| Cantonese-HK\noisy_50 | 50% | 100.07 | 3.50 | N/A |
| Cantonese-HK\noisy_75 | 75% | 95.60 | 4.40 | N/A |
| English-US-Numbers\noisy_100 | 100% | 74.46 | 25.54 | N/A |
| English-US-Numbers\noisy_25 | 25% | 56.29 | 43.71 | N/A |
| English-US-Numbers\noisy_50 | 50% | 79.10 | 20.90 | N/A |
| English-US-Numbers\noisy_75 | 75% | 78.68 | 21.32 | N/A |
| English-US\noisy_100 | 100% | 82.55 | 17.45 | N/A |
| English-US\noisy_25 | 25% | 70.37 | 29.63 | N/A |
| English-US\noisy_50 | 50% | 82.12 | 17.88 | N/A |
| English-US\noisy_75 | 75% | 75.06 | 24.93 | N/A |
| Mandarin-Numbers\noisy_100 | 100% | 97.83 | 2.17 | N/A |
| Mandarin-Numbers\noisy_25 | 25% | 58.59 | 42.61 | N/A |
| Mandarin-Numbers\noisy_50 | 50% | 74.86 | 25.14 | N/A |
| Mandarin-Numbers\noisy_75 | 75% | 95.10 | 4.90 | N/A |
| Mandarin\noisy_100 | 100% | 85.67 | 14.33 | N/A |
| Mandarin\noisy_25 | 25% | 53.20 | 46.80 | N/A |
| Mandarin\noisy_50 | 50% | 78.23 | 21.77 | N/A |
| Mandarin\noisy_75 | 75% | 84.11 | 15.89 | N/A |

