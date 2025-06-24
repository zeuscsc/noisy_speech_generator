# STT System Evaluation Summary Report

## TC-1: Multilingual Support

### Input:

Voice datasets for each language (English-US, English-UK, English-HK, Cantonese-HK, Mandarin), with length ranging from 2s to 10s.
Ground truth transcriptions for each clip.


### Output Requirement:

WER (Word Error Rate), WRR (Word Recognition Rate) for each language, and Accuracy for Numbers (Sequence).


### Results:

#### STT Method: apple_note

| Language | Average WER (%) | Average WRR (%) | Average Sequence Accuracy (%) |
| --- | --- | --- | --- |
| Cantonese-HK | 43.44 | 56.56 | N/A |
| Cantonese-HK-Numbers | N/A | N/A | 68.75 |
| English-US | 25.76 | 74.24 | N/A |
| English-US-Numbers | N/A | N/A | 93.75 |
| Mandarin | 36.73 | 63.27 | N/A |
| Mandarin-Numbers | N/A | N/A | 91.67 |


#### STT Method: fano

| Language | Average WER (%) | Average WRR (%) | Average Sequence Accuracy (%) |
| --- | --- | --- | --- |
| Cantonese-HK | 41.87 | 58.96 | N/A |
| Cantonese-HK-Numbers | N/A | N/A | 71.88 |
| English-US | 31.76 | 68.24 | N/A |
| English-US-Numbers | N/A | N/A | 87.50 |
| Mandarin | 60.73 | 61.15 | N/A |
| Mandarin-Numbers | N/A | N/A | 95.83 |


#### STT Method: google

| Language | Average WER (%) | Average WRR (%) | Average Sequence Accuracy (%) |
| --- | --- | --- | --- |
| Cantonese-HK | 50.81 | 49.19 | N/A |
| Cantonese-HK-Numbers | N/A | N/A | 59.38 |
| English-US | 29.72 | 70.28 | N/A |
| English-US-Numbers | N/A | N/A | 96.88 |
| Mandarin | 65.43 | 56.45 | N/A |
| Mandarin-Numbers | N/A | N/A | 65.62 |


#### STT Method: iphone

| Language | Average WER (%) | Average WRR (%) | Average Sequence Accuracy (%) |
| --- | --- | --- | --- |
| Cantonese-HK | 51.95 | 48.05 | N/A |
| Cantonese-HK-Numbers | N/A | N/A | 62.50 |
| English-US | 38.59 | 61.41 | N/A |
| English-US-Numbers | N/A | N/A | 87.50 |
| Mandarin | 35.17 | 64.83 | N/A |
| Mandarin-Numbers | N/A | N/A | 77.92 |


## TC-2: Robustness Across Accents

### Input:

Voice datasets for each language (Cantonese-HK with Mandarin accent, Mandarin with Cantonese accent, English with Southeast Asian accent, English with Indian accent), with length ranging from 2s to 10s.
Ground truth transcriptions for each clip.


### Output Requirement:

WER (Word Error Rate), WRR (Word Recognition Rate) and for each language.


### Results:

#### STT Method: apple_note

| Accent/Language | Average WER (%) | Average WRR (%) |
| --- | --- | --- |
| Cantonese_Mandarin_Accent | 113.33 | 0.00 |
| English_Indian_Accent | 37.12 | 62.88 |
| English_SouthEastAsian_Accent | 23.56 | 76.44 |
| Mandarin_Cantonese_Accent | 100.00 | 0.00 |


#### STT Method: fano

| Accent/Language | Average WER (%) | Average WRR (%) |
| --- | --- | --- |
| Cantonese_Mandarin_Accent | 96.67 | 3.33 |
| English_Indian_Accent | 40.62 | 60.27 |
| English_SouthEastAsian_Accent | 29.58 | 70.42 |
| Mandarin_Cantonese_Accent | 112.50 | 0.00 |


#### STT Method: google

| Accent/Language | Average WER (%) | Average WRR (%) |
| --- | --- | --- |
| Cantonese_Mandarin_Accent | 100.00 | 0.00 |
| English_Indian_Accent | 38.99 | 61.90 |
| English_SouthEastAsian_Accent | 37.37 | 73.55 |
| Mandarin_Cantonese_Accent | 100.00 | 0.00 |


#### STT Method: iphone

| Accent/Language | Average WER (%) | Average WRR (%) |
| --- | --- | --- |
| Cantonese_Mandarin_Accent | 97.78 | 2.22 |
| English_Indian_Accent | 43.00 | 57.00 |
| English_SouthEastAsian_Accent | 33.71 | 66.29 |
| Mandarin_Cantonese_Accent | 100.00 | 0.00 |


## TC-3: Domain Vocabulary Support

### Input:

Voice datasets for each language (English, Cantonese-HK), with length ranging from 2s to 10s, where HSBC specific terms are mentioned.
Ground truth transcriptions for each clip.


### Output Requirement:

WER (Word Error Rate), and (Accuracy) full vocab recognition for each language.


### Results:

#### STT Method: apple_note

| Language | Average WER (%) | Average Vocabulary Accuracy (%) |
| --- | --- | --- |
| Cantonese | 48.89 | 47.33 |
| English | 24.34 | 86.67 |
| Mandarin | 50.00 | 100.00 |


#### STT Method: fano

| Language | Average WER (%) | Average Vocabulary Accuracy (%) |
| --- | --- | --- |
| Cantonese | 45.54 | 73.38 |
| English | 24.45 | 93.33 |
| Mandarin | 61.90 | 33.33 |


#### STT Method: google

| Language | Average WER (%) | Average Vocabulary Accuracy (%) |
| --- | --- | --- |
| Cantonese | 59.34 | 45.38 |
| English | 25.91 | 93.33 |
| Mandarin | 56.40 | 66.67 |


#### STT Method: iphone

| Language | Average WER (%) | Average Vocabulary Accuracy (%) |
| --- | --- | --- |
| Cantonese | 51.18 | 44.19 |
| English | 30.67 | 80.00 |
| Mandarin | 46.50 | 66.67 |


## TC-4: Auto Punctuation Feature

### Input:

Voice datasets for each language (English-US, English-UK, English-HK, Cantonese-HK, Mandarin), with length ranging from 2s to 10s, and clear punctuation syntax (periods, commas, question marks).
Ground truth transcriptions for each clip.


### Output Requirement:

Proportion of correct punctuation (Sentence Sepreation) placements for each language.


### Results:

#### STT Method: apple_note

| Language | Average Segmentation Accuracy (%) |
| --- | --- |
| Cantonese | 12.38 |
| Cantonese-HK | 3.68 |
| Cantonese-HK-Numbers | 10.26 |
| Cantonese-HK-Numbers\noisy_100 | 0.00 |
| Cantonese-HK-Numbers\noisy_25 | 4.76 |
| Cantonese-HK-Numbers\noisy_50 | 0.00 |
| Cantonese-HK-Numbers\noisy_75 | 0.00 |
| Cantonese-HK\noisy_100 | 0.00 |
| Cantonese-HK\noisy_25 | 0.00 |
| Cantonese-HK\noisy_50 | 0.00 |
| Cantonese-HK\noisy_75 | 0.00 |
| Cantonese_Mandarin_Accent | 13.64 |
| English-US | 100.00 |
| English-US-Numbers | 50.00 |
| English-US-Numbers\noisy_100 | 33.33 |
| English-US-Numbers\noisy_25 | 100.00 |
| English-US-Numbers\noisy_50 | 0.00 |
| English-US-Numbers\noisy_75 | 0.00 |
| English-US\noisy_100 | 0.00 |
| English-US\noisy_25 | 0.00 |
| English-US\noisy_50 | 25.00 |
| English-US\noisy_75 | 0.00 |
| English_SouthEastAsian_Accent | 45.31 |
| Mandarin | 33.33 |
| Mandarin-Numbers | 39.74 |
| Mandarin-Numbers\noisy_100 | 0.00 |
| Mandarin-Numbers\noisy_50 | 0.00 |
| Mandarin-Numbers\noisy_75 | 0.00 |
| Mandarin\noisy_100 | 0.00 |
| Mandarin\noisy_25 | 0.00 |
| Mandarin\noisy_50 | 0.00 |
| Mandarin\noisy_75 | 16.67 |
| Mandarin_Cantonese_Accent | 0.00 |


#### STT Method: fano

| Language | Average Segmentation Accuracy (%) |
| --- | --- |
| Cantonese | 4.52 |
| Cantonese-HK | 3.51 |
| Cantonese-HK-Numbers | 0.00 |
| Cantonese-HK-Numbers\noisy_100 | 9.52 |
| Cantonese-HK-Numbers\noisy_25 | 0.00 |
| Cantonese-HK-Numbers\noisy_50 | 0.00 |
| Cantonese-HK-Numbers\noisy_75 | 0.00 |
| Cantonese-HK\noisy_100 | 12.50 |
| Cantonese-HK\noisy_25 | 2.78 |
| Cantonese-HK\noisy_50 | 0.00 |
| Cantonese-HK\noisy_75 | 0.00 |
| Cantonese_Mandarin_Accent | 18.18 |
| English-US | 0.00 |
| English-US-Numbers | 50.00 |
| English-US-Numbers\noisy_100 | 0.00 |
| English-US-Numbers\noisy_25 | 0.00 |
| English-US-Numbers\noisy_50 | 0.00 |
| English-US-Numbers\noisy_75 | 0.00 |
| English-US\noisy_100 | 100.00 |
| English-US\noisy_25 | 0.00 |
| English-US\noisy_50 | 0.00 |
| English-US\noisy_75 | 0.00 |
| English_SouthEastAsian_Accent | 34.38 |
| Mandarin | 28.33 |
| Mandarin-Numbers | 0.00 |
| Mandarin-Numbers\noisy_100 | 0.00 |
| Mandarin-Numbers\noisy_25 | 16.67 |
| Mandarin-Numbers\noisy_50 | 7.14 |
| Mandarin-Numbers\noisy_75 | 25.00 |
| Mandarin\noisy_100 | 16.67 |
| Mandarin\noisy_25 | 0.00 |
| Mandarin\noisy_50 | 10.00 |
| Mandarin\noisy_75 | 0.00 |
| Mandarin_Cantonese_Accent | 40.00 |


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


#### STT Method: iphone

| Language | Average Segmentation Accuracy (%) |
| --- | --- |
| Cantonese | 12.38 |
| Cantonese-HK | 0.00 |
| Cantonese-HK-Numbers | 11.54 |
| Cantonese-HK-Numbers\noisy_100 | 0.00 |
| Cantonese-HK-Numbers\noisy_25 | 4.76 |
| Cantonese-HK-Numbers\noisy_50 | 0.00 |
| Cantonese-HK-Numbers\noisy_75 | 0.00 |
| Cantonese-HK\noisy_100 | 3.12 |
| Cantonese-HK\noisy_25 | 0.00 |
| Cantonese-HK\noisy_50 | 0.00 |
| Cantonese-HK\noisy_75 | 0.00 |
| Cantonese_Mandarin_Accent | 22.73 |
| English-US | 0.00 |
| English-US-Numbers | 50.00 |
| English-US-Numbers\noisy_100 | 0.00 |
| English-US-Numbers\noisy_25 | 100.00 |
| English-US-Numbers\noisy_50 | 33.33 |
| English-US-Numbers\noisy_75 | 0.00 |
| English-US\noisy_100 | 0.00 |
| English-US\noisy_25 | 0.00 |
| English-US\noisy_50 | 25.00 |
| English-US\noisy_75 | 0.00 |
| English_SouthEastAsian_Accent | 43.75 |
| Mandarin | 50.00 |
| Mandarin-Numbers | 35.90 |
| Mandarin-Numbers\noisy_100 | 0.00 |
| Mandarin-Numbers\noisy_25 | 0.00 |
| Mandarin-Numbers\noisy_50 | 0.00 |
| Mandarin-Numbers\noisy_75 | 0.00 |
| Mandarin\noisy_100 | 0.00 |
| Mandarin\noisy_25 | 10.00 |
| Mandarin\noisy_50 | 0.00 |
| Mandarin\noisy_75 | 0.00 |
| Mandarin_Cantonese_Accent | 30.00 |


#### STT Method: iphone.

| Language | Average Segmentation Accuracy (%) |
| --- | --- |
| Mandarin\noisy_100 | 0.00 |


#### STT Method: iphonet

No valid data to aggregate for this STT method after filtering.

## TC-5: Profanity Filtering

### Input:

Voice datasets for each language (English-US, English-UK, English-HK, Cantonese-HK, Mandarin), with length ranging from 2s to 10s, containing profanity vocabulary.
Ground truth transcriptions for each clip.


### Output Requirement:

Rate of profanity vocabulary identified for each language.


### Results:

#### STT Method: apple_note

No valid data to aggregate for this STT method after filtering.

#### STT Method: fano

No valid data to aggregate for this STT method after filtering.

#### STT Method: google

No valid data to aggregate for this STT method after filtering.

#### STT Method: iphone

No valid data to aggregate for this STT method after filtering.

## TC-6: Transcription Speed and Latency

### Input:

Audio clips of lengths: 5-10 seconds.


### Output Requirement:

Actual latency in seconds vs system-reported latency.


### Results:

#### STT Method: fano

| Metric | Value |
| --- | --- |
| Average Actual Latency (s) | 3.382 |
| System-Reported Latency (s) | Data not available in source CSV |


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

#### STT Method: apple_note

| Language/Condition | Noise Level (%) | Average WER (%) | Average WRR (%) | Average Sequence Accuracy (%) |
| --- | --- | --- | --- | --- |
| Cantonese-HK-Numbers\noisy_100 | 100% | 80.31 | 19.69 | N/A |
| Cantonese-HK-Numbers\noisy_25 | 25% | 66.98 | 33.02 | N/A |
| Cantonese-HK-Numbers\noisy_50 | 50% | 82.75 | 17.25 | N/A |
| Cantonese-HK-Numbers\noisy_75 | 75% | 98.94 | 1.06 | N/A |
| Cantonese-HK\noisy_100 | 100% | 89.92 | 10.08 | N/A |
| Cantonese-HK\noisy_25 | 25% | 57.00 | 43.00 | N/A |
| Cantonese-HK\noisy_50 | 50% | 71.47 | 28.53 | N/A |
| Cantonese-HK\noisy_75 | 75% | 90.78 | 9.22 | N/A |
| English-US-Numbers\noisy_100 | 100% | 83.58 | 16.42 | N/A |
| English-US-Numbers\noisy_25 | 25% | 54.05 | 45.95 | N/A |
| English-US-Numbers\noisy_50 | 50% | 80.50 | 19.50 | N/A |
| English-US-Numbers\noisy_75 | 75% | 70.88 | 29.12 | N/A |
| English-US\noisy_100 | 100% | 81.50 | 18.50 | N/A |
| English-US\noisy_25 | 25% | 68.88 | 31.12 | N/A |
| English-US\noisy_50 | 50% | 82.00 | 18.00 | N/A |
| English-US\noisy_75 | 75% | 77.29 | 22.71 | N/A |
| Mandarin-Numbers\noisy_100 | 100% | 92.58 | 7.42 | N/A |
| Mandarin-Numbers\noisy_50 | 50% | 61.11 | 38.89 | N/A |
| Mandarin-Numbers\noisy_75 | 75% | 73.00 | 27.00 | N/A |
| Mandarin\noisy_100 | 100% | 83.62 | 16.38 | N/A |
| Mandarin\noisy_25 | 25% | 37.49 | 62.51 | N/A |
| Mandarin\noisy_50 | 50% | 57.84 | 42.16 | N/A |
| Mandarin\noisy_75 | 75% | 69.53 | 30.47 | N/A |


#### STT Method: fano

| Language/Condition | Noise Level (%) | Average WER (%) | Average WRR (%) | Average Sequence Accuracy (%) |
| --- | --- | --- | --- | --- |
| Cantonese-HK-Numbers\noisy_100 | 100% | 85.10 | 14.90 | N/A |
| Cantonese-HK-Numbers\noisy_25 | 25% | 65.24 | 34.76 | N/A |
| Cantonese-HK-Numbers\noisy_50 | 50% | 82.31 | 17.69 | N/A |
| Cantonese-HK-Numbers\noisy_75 | 75% | 92.98 | 7.02 | N/A |
| Cantonese-HK\noisy_100 | 100% | 86.46 | 13.54 | N/A |
| Cantonese-HK\noisy_25 | 25% | 66.03 | 33.97 | N/A |
| Cantonese-HK\noisy_50 | 50% | 75.21 | 26.18 | N/A |
| Cantonese-HK\noisy_75 | 75% | 90.66 | 9.34 | N/A |
| English-US-Numbers\noisy_100 | 100% | 92.45 | 7.55 | N/A |
| English-US-Numbers\noisy_25 | 25% | 63.07 | 36.93 | N/A |
| English-US-Numbers\noisy_50 | 50% | 81.72 | 18.28 | N/A |
| English-US-Numbers\noisy_75 | 75% | 89.40 | 10.60 | N/A |
| English-US\noisy_100 | 100% | 84.09 | 15.90 | N/A |
| English-US\noisy_25 | 25% | 69.74 | 30.26 | N/A |
| English-US\noisy_50 | 50% | 87.54 | 12.46 | N/A |
| English-US\noisy_75 | 75% | 101.50 | 6.19 | N/A |
| Mandarin-Numbers\noisy_100 | 100% | 114.91 | 1.76 | N/A |
| Mandarin-Numbers\noisy_25 | 25% | 68.91 | 35.59 | N/A |
| Mandarin-Numbers\noisy_50 | 50% | 85.12 | 17.78 | N/A |
| Mandarin-Numbers\noisy_75 | 75% | 85.99 | 14.01 | N/A |
| Mandarin\noisy_100 | 100% | 95.76 | 6.18 | N/A |
| Mandarin\noisy_25 | 25% | 38.13 | 61.87 | N/A |
| Mandarin\noisy_50 | 50% | 91.82 | 18.13 | N/A |
| Mandarin\noisy_75 | 75% | 81.41 | 18.59 | N/A |


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


#### STT Method: iphone

| Language/Condition | Noise Level (%) | Average WER (%) | Average WRR (%) | Average Sequence Accuracy (%) |
| --- | --- | --- | --- | --- |
| Cantonese-HK-Numbers\noisy_100 | 100% | 92.17 | 7.83 | N/A |
| Cantonese-HK-Numbers\noisy_25 | 25% | 67.14 | 32.86 | N/A |
| Cantonese-HK-Numbers\noisy_50 | 50% | 96.21 | 3.79 | N/A |
| Cantonese-HK-Numbers\noisy_75 | 75% | 98.81 | 1.19 | N/A |
| Cantonese-HK\noisy_100 | 100% | 89.06 | 10.94 | N/A |
| Cantonese-HK\noisy_25 | 25% | 64.29 | 35.71 | N/A |
| Cantonese-HK\noisy_50 | 50% | 82.03 | 17.97 | N/A |
| Cantonese-HK\noisy_75 | 75% | 94.05 | 5.95 | N/A |
| English-US-Numbers\noisy_100 | 100% | 97.08 | 2.92 | N/A |
| English-US-Numbers\noisy_25 | 25% | 65.25 | 34.75 | N/A |
| English-US-Numbers\noisy_50 | 50% | 82.43 | 17.57 | N/A |
| English-US-Numbers\noisy_75 | 75% | 89.73 | 10.27 | N/A |
| English-US\noisy_100 | 100% | 99.34 | 0.66 | N/A |
| English-US\noisy_25 | 25% | 77.51 | 22.49 | N/A |
| English-US\noisy_50 | 50% | 95.54 | 4.46 | N/A |
| English-US\noisy_75 | 75% | 83.86 | 16.14 | N/A |
| Mandarin-Numbers\noisy_100 | 100% | 99.04 | 0.96 | N/A |
| Mandarin-Numbers\noisy_25 | 25% | 51.41 | 48.59 | N/A |
| Mandarin-Numbers\noisy_50 | 50% | 82.91 | 17.09 | N/A |
| Mandarin-Numbers\noisy_75 | 75% | 94.92 | 5.08 | N/A |
| Mandarin\noisy_100 | 100% | 93.87 | 6.13 | N/A |
| Mandarin\noisy_25 | 25% | 43.42 | 56.58 | N/A |
| Mandarin\noisy_50 | 50% | 80.07 | 19.93 | N/A |
| Mandarin\noisy_75 | 75% | 87.11 | 12.89 | N/A |


#### STT Method: iphone.

| Language/Condition | Noise Level (%) | Average WER (%) | Average WRR (%) | Average Sequence Accuracy (%) |
| --- | --- | --- | --- | --- |
| Mandarin\noisy_100 | 100% | 55.00 | 45.00 | N/A |


#### STT Method: iphonet

| Language/Condition | Noise Level (%) | Average WER (%) | Average WRR (%) | Average Sequence Accuracy (%) |
| --- | --- | --- | --- | --- |
| Mandarin\noisy_75 | 75% | 100.00 | 0.00 | N/A |

